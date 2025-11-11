# RAG Chatbot Deployment Guide

This guide covers the deployment of the production-ready RAG chatbot system using Docker and Kubernetes.

## 🏗️ Architecture Overview

The system consists of:
- **Backend**: FastAPI + Python with RAG pipeline
- **Frontend**: React + Vite with TypeScript
- **Database**: PostgreSQL for metadata
- **Cache**: Redis for sessions and caching
- **Vector DB**: Pinecone for document embeddings
- **LLM**: OpenAI GPT-4 for responses

## 📋 Prerequisites

### Required Services
- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

### API Keys Required
- OpenAI API key (for embeddings and GPT-4)
- Pinecone API key (for vector storage)
- JWT secret key (for authentication)

## 🚀 Quick Start (Local Development)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rag-chatbot-production
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Required environment variables:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=rag-chatbot-index

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/ragchatbot

# Redis Configuration
REDIS_URL=redis://localhost:6379
```

### 3. Start Services with Docker Compose
```bash
# Start all services
docker-compose up -d

# Wait for services to be ready (approximately 30 seconds)
sleep 30

# Initialize database (first time only)
docker-compose exec backend python scripts/init_db.py

# Create Pinecone index (first time only)
docker-compose exec backend python scripts/init_pinecone.py
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 5. Default Login Credentials
- **Email**: demo@example.com
- **Password**: demo123456

## 🐳 Production Deployment

### Option 1: Docker Compose (Small Scale)

#### 1. Prepare Production Environment
```bash
# Create production environment file
cp .env.example .env.production

# Edit with production values
nano .env.production
```

#### 2. Deploy with Docker Compose
```bash
# Use production configuration
docker-compose --env-file .env.production up -d

# Scale services if needed
docker-compose up -d --scale backend=3 --scale frontend=2
```

#### 3. Configure Reverse Proxy (nginx)
```bash
# Create nginx configuration
mkdir -p nginx
cat > nginx/nginx.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Add nginx to docker-compose.yml
# ... add nginx service configuration ...
```

### Option 2: Kubernetes (Enterprise Scale)

#### 1. Prepare Kubernetes Manifests
```bash
# Namespace
kubectl create namespace rag-chatbot

# Apply secrets
kubectl apply -f deployment/kubernetes/secrets.yaml

# Apply configurations
kubectl apply -f deployment/kubernetes/configmaps.yaml
```

#### 2. Deploy Services
```bash
# Deploy database
kubectl apply -f deployment/kubernetes/postgres.yaml

# Deploy Redis
kubectl apply -f deployment/kubernetes/redis.yaml

# Deploy backend
kubectl apply -f deployment/kubernetes/backend-deployment.yaml

# Deploy frontend
kubectl apply -f deployment/kubernetes/frontend-deployment.yaml

# Apply ingress
kubectl apply -f deployment/kubernetes/ingress.yaml
```

#### 3. Setup Horizontal Pod Autoscaling
```yaml
# backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 🔧 Configuration

### Backend Configuration
Key settings in `backend/app/config/settings.py`:
- `embedding_model`: OpenAI embedding model
- `llm_model`: GPT model for responses
- `default_chunk_size`: Document chunking size
- `default_retrieval_k`: Default retrieval count
- `rerank_enabled`: Enable result reranking

### Frontend Configuration
Key settings in `frontend/vite.config.ts`:
- API proxy configuration
- Build optimization
- Bundle splitting

### Database Configuration
- PostgreSQL for user data, sessions, documents metadata
- Connection pooling configured
- Automatic migrations

## 🔒 Security Considerations

### Authentication
- JWT tokens with configurable expiration
- Secure password hashing with bcrypt
- Role-based access control (RBAC)
- Rate limiting per user

### Data Protection
- PII detection and redaction
- User data isolation (multi-tenancy)
- Encrypted storage options
- Audit logging

### Network Security
- HTTPS/TLS termination
- API rate limiting
- Input validation and sanitization
- CORS configuration

## 📊 Monitoring & Observability

### Application Monitoring
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# Metrics endpoints
curl http://localhost:8000/metrics
```

### Logging
- Structured JSON logging with correlation IDs
- Separate error and access logs
- Configurable log levels
- Log aggregation ready

### Performance Monitoring
- API response time tracking
- Database query monitoring
- Memory and CPU usage alerts
- Error rate monitoring

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm backend pytest
      - name: Run frontend tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm frontend npm test

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and deploy
        run: |
          docker-compose -f docker-compose.prod.yml up -d
```

### Infrastructure as Code
Terraform templates for cloud infrastructure:
- VPC and networking
- Kubernetes cluster
- Managed databases (PostgreSQL, Redis)
- Load balancers and ingress
- Monitoring and logging stack

## 🧪 Testing

### Backend Testing
```bash
# Unit tests
cd backend && python -m pytest tests/ -v

# Integration tests
cd backend && python -m pytest tests/integration/ -v

# Coverage report
cd backend && python -m pytest --cov=app tests/
```

### Frontend Testing
```bash
# Unit tests
cd frontend && npm test

# E2E tests
cd frontend && npm run test:e2e

# Coverage report
cd frontend && npm run test:coverage
```

### Load Testing
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz

# Run load test
./k6 run --vus 10 --duration 30s scripts/load-test.js
```

## 📈 Scaling Considerations

### Vertical Scaling
- Increase memory for large document processing
- CPU scaling for embedding generation
- Storage scaling for vector database

### Horizontal Scaling
- Multiple backend replicas behind load balancer
- Read replicas for database
- Redis clustering for session storage
- CDN for static assets

### Performance Optimization
- Batch embedding generation
- Result caching with TTL
- Connection pooling
- Query optimization

## 🔄 Maintenance

### Database Maintenance
```bash
# Database backups
docker-compose exec db pg_dump -U postgres ragchatbot > backup.sql

# Database cleanup
docker-compose exec backend python scripts/cleanup_old_data.py

# Vector database backups
docker-compose exec backend python scripts/backup_vectors.py
```

### Application Updates
```bash
# Zero-downtime updates
docker-compose up -d --no-deps backend
# Update one service at a time

# Rolling updates in Kubernetes
kubectl set image deployment/backend backend:latest
kubectl rollout status deployment/backend
```

### Health Monitoring
Set up alerts for:
- High error rates (>5%)
- Response time degradation (>2s)
- Database connection issues
- Memory usage (>80%)
- Disk space (>90%)

## 🚨 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check logs
docker-compose logs backend

# Check database connection
docker-compose exec backend python -c "from app.config.database import engine; engine.connect()"

# Check environment variables
docker-compose exec backend printenv
```

#### Frontend Not Loading
```bash
# Check API connectivity
curl http://localhost:8000/health

# Check nginx logs
docker-compose logs frontend

# Check file permissions
ls -la frontend/dist/
```

#### Vector Database Issues
```bash
# Test Pinecone connection
docker-compose exec backend python -c "
from app.services.vectordb import VectorDBService
service = VectorDBService()
print(service.test_connection())
"
```

#### High Memory Usage
```bash
# Monitor memory usage
docker stats

# Check for memory leaks
docker-compose exec backend python scripts/memory_profiler.py

# Optimize batch sizes
# Update settings.py configuration
```

### Performance Issues
```bash
# Profile slow queries
docker-compose exec backend python scripts/profiler.py

# Check embedding generation speed
docker-compose exec backend python scripts/benchmark_embeddings.py

# Monitor API response times
curl -w "@curl-format.txt" http://localhost:8000/health
```

## 📚 Additional Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)

### Best Practices
- [Python Testing Best Practices](https://docs.python.org/3/library/unittest.html)
- [React Performance](https://react.dev/learn/render-and-commit)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/cluster-administration/)

### Monitoring Tools
- [Prometheus](https://prometheus.io/) - Metrics collection
- [Grafana](https://grafana.com/) - Visualization
- [Jaeger](https://www.jaegertracing.io/) - Distributed tracing
- [ELK Stack](https://www.elastic.co/what-is/elk-stack) - Log aggregation

## 🎯 Production Checklist

Before going to production, ensure:

### Security
- [ ] All secrets are stored securely (not in code)
- [ ] HTTPS/TLS is configured
- [ ] Rate limiting is enabled
- [ ] Input validation is implemented
- [ ] CORS is properly configured
- [ ] Security headers are set
- [ ] Dependencies are scanned for vulnerabilities

### Performance
- [ ] Database connections are pooled
- [ ] Caching is implemented where appropriate
- [ ] Resource limits are set
- [ ] Load balancing is configured
- [ ] CDN is configured for static assets
- [ ] Images are optimized
- [ ] Bundle size is minimized

### Reliability
- [ ] Health checks are configured
- [ ] Auto-restart policies are set
- [ ] Database backups are scheduled
- [ ] Monitoring and alerting are configured
- [ ] Log aggregation is set up
- [ ] Error handling is comprehensive
- [ ] Circuit breakers are implemented

### Maintenance
- [ ] CI/CD pipeline is working
- [ ] Blue-green deployment strategy
- [ ] Rollback procedures are documented
- [ ] Documentation is complete
- [ ] Team is trained on operations
- [ ] Support procedures are established

---

**🎉 Congratulations! Your RAG chatbot is now production-ready!**