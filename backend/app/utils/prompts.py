from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class PromptBuilder:
    """Utility class for building various types of prompts for the RAG system"""

    def __init__(self):
        self.system_prompt = """You are a helpful AI assistant that answers questions based ONLY on the provided context.

Your role is to:
1. Carefully analyze the provided context documents
2. Answer the user's question using only information from the context
3. Always cite your sources using the format [Source: filename]
4. If the answer cannot be found in the context, say "I don't have enough information to answer this question"
5. Be concise but thorough in your responses
6. Do not make up information or hallucinate facts

IMPORTANT:
- Use ONLY the provided context for your answer
- If multiple sources are relevant, cite all of them
- Maintain accuracy over completeness
- Indicate when information is missing from the context"""

    async def build_rag_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build a complete RAG prompt with system instructions, context, and query"""
        try:
            prompt_parts = [self.system_prompt]

            # Add conversation history if provided
            if conversation_history:
                prompt_parts.append("\n\nCONVERSATION HISTORY:")
                for i, message in enumerate(conversation_history[-5:]):  # Limit to last 5 messages
                    role = message.get("role", "user").upper()
                    content = message.get("content", "")
                    prompt_parts.append(f"{role}: {content}")

            # Add context
            if context and context.strip():
                prompt_parts.append(f"\n\nCONTEXT DOCUMENTS:\n{context}")
            else:
                prompt_parts.append("\n\nCONTEXT DOCUMENTS:\nNo relevant context documents were found.")

            # Add current query
            prompt_parts.append(f"\n\nUSER QUESTION:\n{query}")

            # Add final instruction
            prompt_parts.append("\n\nPlease provide a comprehensive answer based on the context above.")

            return "\n".join(prompt_parts)

        except Exception as e:
            logger.error("rag_prompt_building_failed", error=str(e))
            # Fallback to simple prompt
            return f"Based on the following context, answer this question: {query}\n\nContext: {context}"

    async def build_context_with_sources(
        self,
        context_chunks: List[Dict[str, Any]],
        query: str
    ) -> str:
        """Build formatted context with source citations"""
        try:
            if not context_chunks:
                return "No relevant context found."

            context_parts = []
            context_parts.append("Here are the relevant documents to answer the question:")

            for i, chunk in enumerate(context_chunks, 1):
                source = chunk.get("source", {})
                text = chunk.get("text", "")
                relevance = chunk.get("relevance_score", 0)

                source_info = f"Document {i}:"
                if source.get("filename"):
                    source_info += f" {source['filename']}"
                if source.get("page_number"):
                    source_info += f" (Page {source['page_number']})"

                context_parts.append(f"\n{source_info}")
                context_parts.append(f"Relevance: {relevance:.2f}")
                context_parts.append(f"Content: {text}")
                context_parts.append("---")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error("context_formatting_failed", error=str(e))
            # Fallback
            return "\n".join(chunk.get("text", "") for chunk in context_chunks)

    async def build_follow_up_prompt(
        self,
        original_query: str,
        response: str,
        context: str
    ) -> str:
        """Build a prompt for generating follow-up questions"""
        prompt = f"""Based on the following conversation, generate 3-5 relevant follow-up questions that the user might want to ask.

Original Question: {original_query}

AI Response: {response}

Available Context: {context[:500]}...

Generate follow-up questions that:
1. Explore related topics mentioned in the response
2. Ask for more specific details about the subject
3. Help clarify any ambiguous information
4. Encourage deeper understanding of the topic

Format each question on a new line, starting with a number."""

        return prompt

    async def build_summarization_prompt(
        self,
        documents: List[str],
        max_length: int = 300
    ) -> str:
        """Build a prompt for document summarization"""
        combined_docs = "\n\n".join(documents)

        prompt = f"""Please summarize the following documents in a concise and informative way. Focus on the main points, key findings, and important details.

Documents to summarize:
{combined_docs}

Requirements:
1. Keep the summary under {max_length} words
2. Maintain accuracy to the original content
3. Include the most important information
4. Organize the summary logically
5. Highlight any critical findings or conclusions

Summary:"""

        return prompt

    async def build_clarification_prompt(
        self,
        ambiguous_query: str,
        possible_interpretations: List[str]
    ) -> str:
        """Build a prompt for clarifying ambiguous queries"""
        prompt = f"""The user asked an ambiguous question. Help clarify what they mean by identifying the most likely interpretation.

Ambiguous Question: {ambiguous_query}

Possible Interpretations:
{chr(10).join(f"{i+1}. {interpretation}" for i, interpretation in enumerate(possible_interpretations))}

Analyze the question and:
1. Identify which interpretation is most likely based on common usage
2. Suggest clarifying questions to help disambiguate
3. Provide a brief explanation for your choice

Format your response as:
Most Likely Interpretation: [your choice]
Clarifying Questions: [2-3 questions]
Reasoning: [brief explanation]"""

        return prompt

    async def build_document_comparison_prompt(
        self,
        documents: List[Dict[str, str]],
        comparison_criteria: Optional[List[str]] = None
    ) -> str:
        """Build a prompt for comparing multiple documents"""
        criteria = comparison_criteria or ["content", "main points", "conclusions", "methodology"]

        prompt = "Compare and contrast the following documents:\n\n"

        for i, doc in enumerate(documents, 1):
            prompt += f"Document {i}: {doc.get('filename', f'Document {i}')}\n"
            prompt += f"Content: {doc.get('content', '')[:1000]}...\n\n"

        prompt += f"Focus your comparison on these aspects: {', '.join(criteria)}\n\n"
        prompt += "Provide a structured analysis highlighting similarities, differences, and key insights."

        return prompt

    async def build_fact_checking_prompt(
        self,
        claim: str,
        context: str
    ) -> str:
        """Build a prompt for fact-checking claims against context"""
        prompt = f"""Please fact-check the following claim against the provided context.

Claim to verify: {claim}

Context/Source documents:
{context}

Analyze the claim and determine:
1. Is the claim supported by the context? (True/False/Partially True/Not Mentioned)
2. What specific evidence in the context supports or contradicts the claim?
3. Are there any important nuances or limitations?
4. How confident are you in this assessment?

Provide your analysis in the following format:
Assessment: [True/False/Partially True/Not Mentioned]
Confidence: [High/Medium/Low]
Evidence: [specific evidence from context]
Notes: [any important additional information]"""

        return prompt

    async def build_error_correction_prompt(
        self,
        user_query: str,
        previous_response: str,
        error_feedback: str
    ) -> str:
        """Build a prompt for correcting previous responses"""
        prompt = f"""Please provide a corrected response based on the user's feedback.

Original User Query: {user_query}

Previous (Incorrect) Response: {previous_response}

User Feedback/Error: {error_feedback}

Instructions:
1. Acknowledge the error or issue
2. Provide a corrected, accurate response
3. Address the specific feedback points
4. Use only the available context information
5. Be more careful and thorough this time

Corrected Response:"""

        return prompt

    async def build_context_validation_prompt(
        self,
        query: str,
        answer: str,
        context: str
    ) -> str:
        """Build a prompt for validating if an answer is supported by context"""
        prompt = f"""Please validate if the following answer is properly supported by the given context.

Question: {query}

Answer: {answer}

Context: {context}

Evaluate the answer and determine:
1. Does the answer directly address the question?
2. Is the answer fully supported by the context?
3. Are there any claims in the answer that are not supported by the context?
4. Is the answer accurate based on the context?

Provide your assessment in this format:
Valid: [Yes/No/Partially]
Confidence: [High/Medium/Low]
Issues: [list any issues found]
Support: [how well the answer is supported by context]"""

        return prompt

    def get_system_prompt_for_role(self, role: str = "assistant") -> str:
        """Get system prompt based on different roles"""
        role_prompts = {
            "assistant": self.system_prompt,
            "researcher": """You are a research assistant specializing in analyzing academic and technical documents.
            Provide thorough, evidence-based responses with proper citations. Focus on accuracy and scholarly rigor.""",
            "tutor": """You are a helpful tutor. Explain concepts clearly and step-by-step.
            Use analogies and examples to make complex topics understandable. Encourage learning.""",
            "analyst": """You are a business analyst. Focus on practical insights, data-driven conclusions, and actionable recommendations.
            Be concise and focus on business relevance.""",
            "summarizer": """You are a document summarizer. Extract key information, main points, and important details
            while maintaining accuracy and reducing redundancy."""
        }

        return role_prompts.get(role, self.system_prompt)

    async def build_prompt_with_role(
        self,
        query: str,
        context: str,
        role: str = "assistant",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build a prompt with a specific role-based system prompt"""
        try:
            role_prompt = self.get_system_prompt_for_role(role)
            return await self.build_rag_prompt(query, context, conversation_history).replace(
                self.system_prompt, role_prompt
            )
        except Exception as e:
            logger.error("role_prompt_building_failed", role=role, error=str(e))
            return await self.build_rag_prompt(query, context, conversation_history)