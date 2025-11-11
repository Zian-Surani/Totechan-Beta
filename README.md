# 🤖 Production-Ready RAG Chatbot

A comprehensive, enterprise-grade Retrieval-Augmented Generation (RAG) chatbot system with document intelligence, built with modern technologies and production-ready architecture.

## ✨ Features

### 🧠 Core RAG Capabilities
- **Multi-format Document Support**: PDF, DOCX, HTML, TXT processing
- **Intelligent Chunking**: Semantic document segmentation with overlap
- **Advanced Retrieval**: Vector search with hybrid filtering and reranking
- **Real-time Responses**: Streaming LLM responses with WebSocket support
- **Source Citations**: Automatic source attribution with confidence scores

### 🔒 Security & Compliance
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: User, admin, and viewer roles
- **PII Detection**: Automatic sensitive data identification
- **Audit Logging**: Comprehensive activity tracking
- **Data Isolation**: Multi-tenant architecture with user separation

### 📊 Production Features
- **Scalable Architecture**: Microservices with Docker/Kubernetes support
- **Monitoring & Observability**: Structured logging, metrics, and health checks
- **Load Balancing**: Horizontal scaling support
- **Database Optimization**: Connection pooling and query optimization
- **CI/CD Ready**: GitHub Actions workflows for automated deployment

## 🏗️ Technology Stack

### Backend
- **FastAPI**: Modern, fast Python web framework
- **PostgreSQL**: Relational database for metadata
- **Redis**: Caching and session storage
- **Pinecone**: Vector database for embeddings
- **OpenAI**: GPT-4 for responses, embeddings for vectors
- **LangChain**: RAG pipeline components

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **React Query**: Server state management

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Orchestration
- **Nginx**: Reverse proxy
- **GitHub Actions**: CI/CD

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key
- Pinecone API key

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rag-chatbot-production
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
```bash
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-pinecone-env
JWT_SECRET_KEY=your-jwt-secret
```

### 3. Launch the System
```bash
# Start all services
docker-compose up -d

# Initialize database (first time only)
docker-compose exec backend python scripts/init_db.py

# Create Pinecone index (first time only)
docker-compose exec backend python scripts/init_pinecone.py
```

### 4. Access the Application
- 🌐 **Frontend**: http://localhost:3000
- 🔌 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

### 5. Login
- **Email**: demo@example.com
- **Password**: demo123456

## 📱 Usage Guide

### Document Upload
1. Navigate to the Documents page
2. Click "Upload Document" or drag and drop files
3. Supported formats: PDF, DOCX, HTML, TXT
4. Monitor processing status in real-time

### Chat Interface
1. Go to the Chat page
2. Ask questions about your uploaded documents
3. View AI responses with source citations
4. Use real-time streaming for faster responses

### Session Management
- Create multiple chat sessions for different topics
- View chat history and export conversations
- Rename or delete sessions as needed

## 📁 Project Structure

```
rag-chatbot-production/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── routers/             # API routes
│   │   ├── services/            # Business logic
│   │   ├── models/              # Data models
│   │   ├── utils/               # Utilities
│   │   └── config/              # Configuration
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Backend container
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/          # UI components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API client
│   │   ├── types/              # TypeScript types
│   │   └── contexts/           # React contexts
│   ├── package.json             # Node.js dependencies
│   ├── vite.config.ts           # Vite configuration
│   └── Dockerfile               # Frontend container
├── deployment/                   # Infrastructure
│   ├── kubernetes/             # K8s manifests
│   └── terraform/              # Infrastructure as code
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── tests/                       # Test suites
├── docker-compose.yml           # Development environment
├── .env.example                 # Environment template
├── DEPLOYMENT.md               # Detailed deployment guide
└── README.md                   # This file
```

## 🔧 Configuration

### Backend Settings (`backend/app/config/settings.py`)
```python
# RAG Configuration
DEFAULT_CHUNK_SIZE = 1000          # Document chunk size
CHUNK_OVERLAP = 200              # Chunk overlap percentage
DEFAULT_RETRIEVAL_K = 8          # Default retrieval count
RERANK_ENABLED = True            # Enable result reranking
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4-turbo-preview"
```

### Frontend Settings (`frontend/vite.config.ts`)
```typescript
// API proxy configuration
proxy: {
  '/api': 'http://localhost:8000',
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true,
  },
}
```

## 🚀 Deployment

### Local Development
```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production (Docker Compose)
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale backend=3 --scale frontend=2
```

### Kubernetes
```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods -n rag-chatbot
```

Detailed deployment instructions in [DEPLOYMENT.md](./DEPLOYMENT.md)

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm test
npm run test:coverage
```

### Integration Tests
```bash
# Load testing with k6
k6 run --vus 10 --duration 30s tests/load-test.js
```

## 📊 Monitoring

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready
```

### Metrics
- Application metrics: `/metrics`
- Database metrics: PostgreSQL metrics
- Cache metrics: Redis metrics

## 🔒 Security

### Authentication Flow
- JWT-based authentication
- Secure password hashing
- Token refresh mechanism
- Role-based authorization

### Data Protection
- PII detection and redaction
- User data isolation
- Audit logging
- Encrypted communications

## 📈 Scaling

### Horizontal Scaling
- Multiple backend replicas
- Database read replicas
- Redis clustering
- CDN for static assets

### Performance Optimization
- Connection pooling
- Query optimization
- Result caching
- Batch processing

## 🛠️ Development

### Adding New Document Types
1. Update `DocumentType` enum in `backend/app/models/document_schemas.py`
2. Add processor in `backend/app/services/document_processor.py`
3. Update frontend validation

### Customizing Prompts
1. Modify prompt templates in `backend/app/utils/prompts.py`
2. Add new prompt building methods
3. Test with different use cases

### Extending RAG Pipeline
1. Add new services in `backend/app/services/`
2. Update retrieval configuration
3. Integrate with API endpoints

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/token` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user

### Document Endpoints
- `POST /api/v1/ingest/upload` - Upload document
- `GET /api/v1/ingest/documents` - List documents
- `DELETE /api/v1/ingest/documents/{id}` - Delete document

### Chat Endpoints
- `POST /api/v1/chat/ask` - Ask question
- `GET /api/v1/chat/sessions` - List sessions
- `WebSocket /ws/chat/{session_id}` - Real-time chat

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python
- Use ESLint for JavaScript/TypeScript
- Write comprehensive tests
- Update documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📖 Documentation: [Wiki](https://github.com/your-repo/wiki)

## 🎉 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Pinecone](https://www.pinecone.io/) - Vector database
- [OpenAI](https://openai.com/) - AI services
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework

---

**🚀 Ready to build your intelligent document assistant?** Get started now with the Quick Start guide above!