import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
import structlog
from openai import AsyncOpenAI
import tiktoken
import json

from app.config.settings import settings
from app.utils.exceptions import LLMError, ExternalServiceError
from app.utils.prompts import PromptBuilder

logger = structlog.get_logger()


class LLMClient:
    """Client for interacting with OpenAI LLM models"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self.prompt_builder = PromptBuilder()

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to a common tokenizer
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Model configurations
        self.max_tokens = 4096
        self.temperature = 0.1  # Lower temperature for more factual responses
        self.max_retries = 3
        self.retry_delay = 1.0

    async def generate_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response to a query with context"""
        try:
            # Build the prompt
            prompt = await self.prompt_builder.build_rag_prompt(
                query=query,
                context=context,
                conversation_history=conversation_history or []
            )

            # Estimate tokens
            prompt_tokens = self._count_tokens(prompt)
            max_completion_tokens = self.max_tokens - prompt_tokens - 100  # Leave buffer

            logger.info(
                "llm_generation_started",
                model=self.model,
                prompt_tokens=prompt_tokens,
                max_completion_tokens=max_completion_tokens,
                stream=stream
            )

            # Generate response
            if stream:
                return await self._generate_streaming_response(
                    prompt, max_completion_tokens, **kwargs
                )
            else:
                return await self._generate_regular_response(
                    prompt, max_completion_tokens, **kwargs
                )

        except Exception as e:
            logger.error("llm_generation_failed", error=str(e))
            raise LLMError(f"Failed to generate LLM response: {str(e)}")

    async def _generate_regular_response(
        self,
        prompt: str,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a regular (non-streaming) response"""
        try:
            start_time = time.time()

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=self.temperature,
                **kwargs
            )

            generation_time = time.time() - start_time
            message = response.choices[0].message
            content = message.content or ""

            # Count tokens in response
            completion_tokens = response.usage.completion_tokens if response.usage else self._count_tokens(content)
            prompt_tokens = response.usage.prompt_tokens if response.usage else self._count_tokens(prompt)
            total_tokens = response.usage.total_tokens if response.usage else prompt_tokens + completion_tokens

            # Estimate cost
            cost_estimate = self._estimate_cost(prompt_tokens, completion_tokens)

            result = {
                "content": content,
                "model": self.model,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "generation_time": generation_time,
                "cost_estimate": cost_estimate,
                "finish_reason": response.choices[0].finish_reason
            }

            logger.info(
                "llm_response_generated",
                total_tokens=total_tokens,
                generation_time=generation_time,
                cost_estimate=cost_estimate,
                finish_reason=response.choices[0].finish_reason
            )

            return result

        except Exception as e:
            logger.error("regular_llm_response_failed", error=str(e))
            raise

    async def _generate_streaming_response(
        self,
        prompt: str,
        max_tokens: int,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response"""
        try:
            start_time = time.time()
            total_tokens = 0
            content_buffer = ""

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=self.temperature,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    content_buffer += content
                    total_tokens += 1
                    yield content

            generation_time = time.time() - start_time
            prompt_tokens = self._count_tokens(prompt)
            completion_tokens = total_tokens
            cost_estimate = self._estimate_cost(prompt_tokens, completion_tokens)

            logger.info(
                "llm_streaming_response_completed",
                total_tokens=prompt_tokens + completion_tokens,
                generation_time=generation_time,
                cost_estimate=cost_estimate
            )

        except Exception as e:
            logger.error("streaming_llm_response_failed", error=str(e))
            raise

    async def generate_with_sources(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate response with source citations"""
        try:
            # Format context with sources
            context_with_sources = await self.prompt_builder.build_context_with_sources(
                context_chunks, query
            )

            # Generate response
            response = await self.generate_response(
                query=query,
                context=context_with_sources,
                conversation_history=conversation_history
            )

            # Extract sources from response if available
            answer = response["content"]
            cited_sources = await self._extract_citations(answer, context_chunks)

            result = {
                **response,
                "sources": cited_sources,
                "context_used": len(context_chunks)
            }

            return result

        except Exception as e:
            logger.error("llm_generation_with_sources_failed", error=str(e))
            raise

    async def _extract_citations(
        self,
        answer: str,
        context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract source citations from the answer"""
        try:
            citations = []

            # Simple citation extraction - look for patterns like [Source: filename]
            # In a more sophisticated implementation, you might use:
            # - Regular expressions to find citation patterns
            # - NLP techniques to identify referenced sources
            # - LLM-based citation extraction

            import re
            citation_pattern = r'\[([^\]]+)\]'

            matches = re.findall(citation_pattern, answer)
            for match in matches:
                if "Source:" in match:
                    filename = match.replace("Source:", "").strip()
                    citations.append({
                        "type": "filename",
                        "reference": filename,
                        "context": match
                    })

            # If no explicit citations found, include all context sources
            if not citations and context_chunks:
                for i, chunk in enumerate(context_chunks):
                    source = chunk.get("source", {})
                    citations.append({
                        "type": "context",
                        "reference": source.get("filename", f"Source {i+1}"),
                        "document_id": source.get("document_id"),
                        "page_number": source.get("page_number"),
                        "relevance_score": chunk.get("relevance_score", 0)
                    })

            return citations

        except Exception as e:
            logger.error("citation_extraction_failed", error=str(e))
            return []

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback estimation
            return len(text) // 4

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> str:
        """Estimate cost in USD"""
        try:
            # OpenAI pricing (as of 2024)
            # GPT-4 Turbo: $0.01 per 1K prompt tokens, $0.03 per 1K completion tokens
            pricing = {
                "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
                "gpt-4": {"prompt": 0.03, "completion": 0.06},
                "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002}
            }

            model_pricing = pricing.get(self.model, pricing["gpt-4-turbo-preview"])
            prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
            completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
            total_cost = prompt_cost + completion_cost

            return f"${total_cost:.6f}"

        except Exception:
            return "$0.000000"

    async def validate_response(self, response: str, context: str) -> Dict[str, Any]:
        """Validate response against context for factual accuracy"""
        try:
            # This is a simple validation - in production you might use:
            # - Another LLM call to check factual accuracy
            # - Semantic similarity between response and context
            # - Fact-checking against reliable sources

            validation_result = {
                "is_factual": True,
                "confidence": 0.8,
                "issues": [],
                "source_coverage": 0.7  # Estimate of how much response is based on sources
            }

            # Check for common hallucination indicators
            hallucination_indicators = [
                "I don't have information about",
                "I cannot find",
                "As an AI, I don't have access",
                "I'm not sure about"
            ]

            for indicator in hallucination_indicators:
                if indicator.lower() in response.lower():
                    validation_result["issues"].append(f"Contains uncertainty indicator: {indicator}")
                    validation_result["confidence"] -= 0.2

            # Ensure confidence doesn't go below 0
            validation_result["confidence"] = max(0, validation_result["confidence"])

            return validation_result

        except Exception as e:
            logger.error("response_validation_failed", error=str(e))
            return {
                "is_factual": True,
                "confidence": 0.5,
                "issues": [f"Validation failed: {str(e)}"],
                "source_coverage": 0.5
            }

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the LLM model"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "tokenizer": str(type(self.tokenizer).__name__),
            "pricing": {
                "prompt_tokens_per_million": 10,  # $0.01 per 1K = $10 per 1M
                "completion_tokens_per_million": 30  # $0.03 per 1K = $30 per 1M
            }
        }

    async def test_model_access(self) -> bool:
        """Test if we can access the LLM model"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.info("llm_model_access_validated", model=self.model)
            return True

        except Exception as e:
            logger.error("llm_model_access_failed", model=self.model, error=str(e))
            return False

    async def generate_follow_up_questions(
        self,
        query: str,
        response: str,
        context: str
    ) -> List[str]:
        """Generate follow-up questions based on the conversation"""
        try:
            prompt = await self.prompt_builder.build_follow_up_prompt(
                original_query=query,
                response=response,
                context=context
            )

            follow_up_response = await self.generate_response(
                query="",
                context=prompt,
                max_tokens=200
            )

            # Parse the response to extract questions
            questions_text = follow_up_response["content"]
            questions = []

            # Simple parsing - split by numbered items or bullet points
            lines = questions_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering/bullets and clean
                    question = re.sub(r'^[\d\-\.\•\s]+', '', line).strip()
                    if question and question.endswith('?'):
                        questions.append(question)

            # Limit to 3-5 questions
            return questions[:5]

        except Exception as e:
            logger.error("follow_up_generation_failed", error=str(e))
            return []

    async def analyze_response_quality(
        self,
        query: str,
        response: str,
        context: str,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze the quality of the generated response"""
        try:
            analysis = {
                "completeness": 0.8,  # How completely the query is answered
                "relevance": 0.8,     # How relevant the response is to the query
                "factual_accuracy": 0.8,  # How factually accurate the response is
                "source_usage": 0.7,  # How well sources are utilized
                "clarity": 0.8,       # How clear and understandable the response is
                "overall_score": 0.8   # Overall quality score
            }

            # Check response length
            response_length = len(response)
            if response_length < 50:
                analysis["completeness"] *= 0.5
                analysis["clarity"] *= 0.8
            elif response_length > 1000:
                analysis["clarity"] *= 0.9

            # Check if response actually answers the query
            query_words = set(query.lower().split())
            response_words = set(response.lower().split())
            word_overlap = len(query_words & response_words) / len(query_words) if query_words else 0
            analysis["relevance"] *= (0.5 + 0.5 * word_overlap)

            # Check source citations
            if sources:
                analysis["source_usage"] = min(1.0, len(sources) / 3)  # Cap at 3 sources
            else:
                analysis["source_usage"] *= 0.3

            # Calculate overall score
            analysis["overall_score"] = sum([
                analysis["completeness"],
                analysis["relevance"],
                analysis["factual_accuracy"],
                analysis["source_usage"],
                analysis["clarity"]
            ]) / 5

            return analysis

        except Exception as e:
            logger.error("response_quality_analysis_failed", error=str(e))
            return {
                "completeness": 0.5,
                "relevance": 0.5,
                "factual_accuracy": 0.5,
                "source_usage": 0.5,
                "clarity": 0.5,
                "overall_score": 0.5,
                "error": str(e)
            }