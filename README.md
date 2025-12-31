# 🔮 Future Me - AI-Powered GitHub Career Simulator

> **Chat with your future self based on your GitHub journey using Groq AI, LangChain, and Redis Vector Search**

Hey there! 👋 I'm **Aziz Zoaib**, and I built this Kubernetes-native app that analyzes your GitHub commit history, creates a vector database of your coding journey, and lets you chat with an AI about your future career trajectory.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-yellow.svg)](https://langchain.com/)
[![Groq](https://img.shields.io/badge/Groq-AI-orange.svg)](https://groq.com/)
[![Redis](https://img.shields.io/badge/Redis-Vector%20DB-DC382D.svg)](https://redis.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Native-326CE5.svg)](https://kubernetes.io/)

## 🎯 **What Does It Do?**

An intelligent conversational AI that:

- 🔍 Analyzes ALL your GitHub repositories and commit history
- 🧠 Builds a semantic vector database using Redis Stack + HuggingFace embeddings
- 💬 Enables RAG-powered conversations with LangChain for context-aware responses
- 🤖 Uses Groq's ultra-fast Llama 3 for AI-powered career predictions
- 🔮 Predicts your future development trajectory based on actual coding patterns
- ⚡ Delivers lightning-fast responses with session-based chat history

## ✨ **Key Features**

- 🎨 **Modern dark-themed chat UI** with real-time messaging and typing indicators
- 🧠 **RAG Architecture** - Redis Stack HNSW + HuggingFace embeddings (local, no API costs)
- 🚀 **Sub-second responses** with Groq's optimized Llama 3 inference
- 📊 **Smart retrieval** - Top-K semantic search across your commit history

## 🏗️ **Architecture**

```
┌──────────────────┐
│   GitHub API     │
│   (All Repos +   │
│   Commit History)│
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│  Data Ingestion Layer    │
│  • Fetch all repos       │
│  • Collect commits       │
│  • Create documents      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  HuggingFace Embeddings  │
│  (sentence-transformers) │
│  • Local processing      │
│  • No external API       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Redis Stack            │
│   • Vector storage       │
│   • HNSW indexing        │
│   • Semantic search      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   LangChain RAG          │
│   • Context retrieval    │
│   • Prompt engineering   │
│   • Chat history mgmt    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Groq AI (Llama 3)      │
│   • Ultra-fast inference │
│   • Career predictions   │
│   • Contextual responses │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   FastAPI Backend        │
│   • REST API             │
│   • Session management   │
│   • Static file serving  │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Chat UI (HTML/JS)      │
│   • Modern dark theme    │
│   • Real-time messaging  │
│   • Responsive design    │
└──────────────────────────┘
```

## 🛠️ **Tech Stack**

**Frontend:** HTML5/CSS3/JavaScript • **Backend:** FastAPI • **AI:** Groq (Llama 3 70B) + LangChain  
**Vector DB:** Redis Stack • **Embeddings:** HuggingFace Transformers • **Orchestration:** Kubernetes

## 📋 **Prerequisites**

- Kubernetes cluster (Kind, minikube, GKE, EKS, AKS)
- Docker 20.10+ and kubectl configured
- 8GB+ RAM recommended
- [Groq API Key](https://console.groq.com/keys) (14,400 free requests/day)
- [GitHub Personal Access Token](https://github.com/settings/tokens) (scopes: `repo`, `read:user`)

## ⚡ **Quick Start**

### **Step 1: Clone Repository**
```bash
git clone https://github.com/azizzoaib786/future-me.git
cd future-me
```

> **Note**: Feel free to fork this repo and customize it for your own GitHub analysis!

### **Step 2: Create Kind Cluster (Optional)**

If you don't have a Kubernetes cluster, create one with Kind:

```bash
# Install Kind (if not already installed)
# macOS
brew install kind

# Linux
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create cluster using provided config
kind create cluster --config cluster/future-me-cluster.yaml --name future-me

# Verify cluster is running
kubectl cluster-info --context kind-future-me
kubectl get nodes
```

> **Skip this step** if you're using an existing cluster (minikube, GKE, EKS, AKS, etc.)

### **Step 3: Build Application Image**
```bash
# Build Docker image
cd app
docker build -t future-me/app:latest .

# For Kind cluster - load image locally (skip for cloud clusters)
kind load docker-image future-me/app:latest --name future-me

# For cloud clusters - push to your registry
# docker tag future-me/app:latest your-registry/future-me:latest
# docker push your-registry/future-me:latest
```

### **Step 4: Configure Secrets**

Edit `k8s/future-me-secrets.yaml` with your API keys:

```yaml
stringData:
  groq-api-key: "your_groq_api_key_here"
  github-token: "your_github_token_here"
```

**⚠️ Security Warning**: Never commit real secrets to Git! Use this for local development only.

Alternatively, create secrets via kubectl:

```bash
kubectl create secret generic future-me-secrets \
  --from-literal=groq-api-key="your_groq_api_key" \
  --from-literal=github-token="your_github_token" \
  --namespace=future-me
```

### **Step 5: Deploy to Kubernetes**
```bash
# Deploy Redis Stack (vector database)
kubectl apply -f k8s/redis-stack.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis-stack -n future-me --timeout=60s

# Deploy secrets
kubectl apply -f k8s/future-me-secrets.yaml

# Deploy main application
kubectl apply -f k8s/future-me-deployment.yaml

# Wait for application to be ready (this may take 2-3 minutes on first run)
kubectl wait --for=condition=ready pod -l app=future-me-app -n future-me --timeout=300s
```

### **Step 6: Access the Application**
```bash
# Port forward to local machine
kubectl port-forward service/future-me-app 8000:8000 -n future-me

# Open in your browser:
# http://localhost:8000
```

### **Step 7: Start Chatting!**

Ask questions like:
- "Based on my GitHub activity, what will I be working on in 1 year?"
- "What programming languages should I learn next?"
- "What are my strongest technical skills?"

## 🔧 **Configuration**

Edit [`k8s/future-me-deployment.yaml`](k8s/future-me-deployment.yaml) to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *Required* | Groq API key (from secrets) |
| `GITHUB_TOKEN` | *Required* | GitHub PAT (from secrets) |
| `GITHUB_MAX_COMMITS` | `100` | Max commits to analyze across all repos |
| `FUTURE_ME_NAME` | `"Aziz"` | Your name (change this!) |
| `FUTURE_ME_YEARS_AHEAD` | `1` | Years to project into future |

**Example customization:**
```yaml
env:
  - name: GITHUB_MAX_COMMITS
    value: "500"
  - name: FUTURE_ME_NAME
    value: "YourName"
```

## 🏗️ **Project Structure**

```
future-me/
├── 📁 app/                           # Application source code
│   ├── 📄 app.py                     # FastAPI app (GitHub API, LangChain RAG, Redis, Groq AI, Chat endpoints)
│   ├── 📄 requirements.txt           # Python dependencies (fastapi, langchain, sentence-transformers, redis, pygithub)
│   ├── 📄 Dockerfile                 # Container build (python:3.11-slim, downloads embedding model)
│   └── 📁 static/
│       └── 📄 index.html             # Chat UI (dark theme, real-time messaging, responsive)
│
├── 📁 k8s/                           # Kubernetes manifests
│   ├── 📄 redis-stack.yaml           # Redis deployment (vector storage, HNSW indexing)
│   ├── 📄 future-me-deployment.yaml  # App deployment (service, environment config, resource limits)
│   └── 📄 future-me-secrets.yaml     # API credentials (Groq, GitHub)
│
├── 📁 cluster/
│   └── 📄 future-me-cluster.yaml     # Kind cluster config
│
└── 📄 README.md                      # This file
```

## 📖 **How It Works**

### **1. Data Ingestion Phase** (Startup)

1. Fetches ALL repositories from your GitHub account
2. Collects commits across all repos (up to `GITHUB_MAX_COMMITS`)
3. Creates LangChain documents with commit metadata (message, author, date, repo, files)
4. Generates embeddings using local HuggingFace model
5. Indexes in Redis with HNSW algorithm for fast vector search

**Note**: This process runs on every startup. Expect 1-3 minutes depending on your commit count.

### **2. Query Phase** (Chat Interaction)

1. **Vector Search** → Your message is embedded and matched against commit history
2. **Context Retrieval** → Top-K most relevant commits are retrieved (K=8)
3. **Prompt Construction** → LangChain builds prompt with message + context + history
4. **LLM Inference** → Groq's Llama 3 generates contextual response
5. **History Update** → Conversation saved to session
6. **Response Delivery** → Answer streamed back to UI

**RAG Benefits**: Responses are grounded in your actual commit history, contextually aware of your projects, personalized to your journey, and accurate rather than generic.

## 🎨 **Chat UI Features**

- 🌑 **Dark theme** with gradient accents • 📱 **Fully responsive** mobile design
- 💬 **Typing indicators** and real-time updates • 📜 **Scrollable chat history**
- ✨ **Message bubbles** with timestamps and avatars • ⌨️ **Keyboard shortcuts** (Enter to send)
- 🔐 **Session persistence** maintains conversation context

## 🚀 **API Reference**

### **POST /api/chat**

Chat endpoint for conversational interactions.

**Request:**
```json
{
  "message": "What will I be working on in 1 year?",
  "session_id": "optional-uuid-v4-string"
}
```

**Response:**
```json
{
  "reply": "Based on your GitHub activity showing strong Python and Kubernetes work...",
  "session_id": "uuid-v4-string"
}
```

**Features:**
- Session management (returns new `session_id` if not provided)
- Conversation history maintained per session
- RAG-powered responses with commit context

### **GET /**

Serves the chat UI (static HTML).

## 🌐 **Access Options**

### **Port Forwarding**

#### **Option 1: Simple Port Forward**
```bash
# Forward to localhost (most common for development)
kubectl port-forward service/future-me-app 8000:8000 -n future-me

# Access at: http://localhost:8000
```

#### **Option 2: Port Forward with Specific Address**
```bash
# Allow access from any network interface (useful for local network access)
kubectl port-forward --address 0.0.0.0 service/future-me-app 8000:8000 -n future-me

# Access from other devices on your network at: http://YOUR_IP:8000
```

#### **Option 3: Background Port Forward**
```bash
# Run port forward in background
kubectl port-forward service/future-me-app 8000:8000 -n future-me > /dev/null 2>&1 &

# Save the process ID
echo $! > /tmp/future-me-port-forward.pid

# Later, to stop it:
kill $(cat /tmp/future-me-port-forward.pid)
```

#### **Option 4: Persistent Port Forward with Auto-Restart**
```bash
# Create a script for persistent port forwarding
cat > port-forward.sh << 'EOF'
#!/bin/bash
while true; do
  echo "Starting port forward..."
  kubectl port-forward service/future-me-app 8000:8000 -n future-me
  echo "Port forward stopped. Restarting in 5 seconds..."
  sleep 5
done
EOF

chmod +x port-forward.sh

# Run in background
./port-forward.sh &
```

#### **Troubleshooting Port Forward**

**If port 8000 is already in use:**
```bash
# Use a different local port
kubectl port-forward service/future-me-app 8080:8000 -n future-me
# Access at: http://localhost:8080
```

**If port forward disconnects frequently:**
```bash
# Use the persistent script (Option 4) above, or
# Check if pod is stable
kubectl get pods -n future-me -w
```

**To find what's using port 8000:**
```bash
# On macOS/Linux
lsof -i :8000

# Kill the process if needed
kill -9 <PID>
```

### **Viewing Logs**

```bash
# View application logs
kubectl logs -f deployment/future-me-app -n future-me

# Check Redis logs
kubectl logs -f deployment/redis-stack -n future-me

# Check pod status
kubectl get pods -n future-me
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Pod CrashLoopBackOff**

**Check logs:**
```bash
kubectl logs deployment/future-me-app -n future-me --previous
```

**Common causes:**
- ❌ Invalid Groq API key
- ❌ Invalid GitHub token
- ❌ Redis not ready
- ❌ Out of memory (increase limits)

**Fix:**
```bash
# Verify secrets
kubectl get secret future-me-secrets -n future-me -o jsonpath='{.data.groq-api-key}' | base64 -d

# Check Redis connection
kubectl exec -it deployment/future-me-app -n future-me -- \
  python -c "import redis; print(redis.Redis(host='redis').ping())"
```

#### **2. Slow Startup / OOMKilled**

**Problem**: Pod crashes during embedding model download

**Solution**: Increase memory limits
```yaml
resources:
  limits:
    memory: "2Gi"  # Increase from 1Gi
```

#### **3. "No commits found" Error**

**Problem**: Application can't access GitHub repos

**Causes:**
- Token doesn't have `repo` scope
- Repositories are all empty
- API rate limit exceeded

**Fix:**
```bash
# Check GitHub token permissions
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user/repos

# Check rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

#### **4. Redis Connection Refused**

**Problem**: Application can't connect to Redis

**Solution:**
```bash
# Check Redis pod status
kubectl get pods -n future-me -l app=redis-stack

# Check Redis service
kubectl get svc redis -n future-me

# Test connectivity
kubectl run redis-test --rm -it --image=redis:alpine -n future-me -- \
  redis-cli -h redis ping
```

#### **5. Chat UI Not Loading**

**Problem**: Blank page or 404 errors

**Causes:**
- Static files not mounted correctly
- Port forward not working
- Pod not ready

**Fix:**
```bash
# Check if pod is running
kubectl get pods -n future-me

# Restart port forward
kubectl port-forward service/future-me-app 8000:8000 -n future-me

# Check if static files exist in pod
kubectl exec deployment/future-me-app -n future-me -- ls -la /app/static
```

### **Debug Mode**

Enable verbose logging by updating the deployment:

```yaml
env:
  - name: LOG_LEVEL
    value: "DEBUG"
```

## 🎯 **Use Cases**

- **Career Planning** - "What senior roles am I qualified for?" • "Which technologies should I learn next?"
- **Skill Assessment** - "What are my strongest programming languages?" • "How has my code quality improved?"
- **Project Discovery** - "What interesting side projects have I worked on?" • "Show me my contribution patterns"
- **Learning Guidance** - "Based on my GitHub, what should I study next?" • "Which frameworks align with my experience?"
- **Resume Building** - "Summarize my most significant contributions" • "How can I describe my GitHub work on my resume?"



## 🤝 **Contributing**

I'd love contributions from the community! Here's how:

**Quick Setup:**
```bash
git clone https://github.com/azizzoaib786/future-me.git && cd future-me/app
python -m venv venv && source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export GROQ_API_KEY="your-key" GITHUB_TOKEN="your-token" REDIS_URL="redis://localhost:6379/0"
docker run -d -p 6379:6379 redis/redis-stack:latest
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Workflow:** Fork → Branch (`feature/amazing-feature`) → Code (PEP 8, type hints, docstrings) → Test → Commit (`feat: add feature`) → PR

**Ideas:** Bug fixes • New chat features • Analytics • UI/UX • Tests • Docs • Multi-language • Performance • Security

## 🔐 **Security Notes**

**⚠️ This is a hobby project for personal use. Security features:**
- Kubernetes Secrets for API keys (don't commit secrets to Git!)
- Local embedding processing (data stays in your cluster)
- No permanent storage of commit data

**For personal use:** Keep your API keys safe and use a read-only GitHub token

## 📜 **License**

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

Huge thanks to the open-source community and these amazing technologies: **[Groq](https://groq.com)** (blazingly fast LLM inference) • **[LangChain](https://langchain.com)** (Swiss Army knife for RAG) • **[Redis Stack](https://redis.io/docs/stack/)** (vector search that scales) • **[HuggingFace](https://huggingface.co)** (democratizing AI) • **[FastAPI](https://fastapi.tiangolo.com)** (best Python web framework) • **[PyGithub](https://pygithub.readthedocs.io)** (painless GitHub API) • **[Kubernetes](https://kubernetes.io)** (cloud-native orchestration)

## 📚 **Resources**

[Groq API Docs](https://console.groq.com/docs) • [LangChain RAG Tutorial](https://python.langchain.com/docs/tutorials/rag/) • [Redis Vector Search](https://redis.io/docs/stack/search/reference/vectors/) • [FastAPI Guide](https://fastapi.tiangolo.com/tutorial/)

---

**🔮 Built with passion by [Aziz Zoaib](https://github.com/azizzoaib786) for developers who want to visualize their coding journey and discover their future potential!**

Found this helpful? ⭐ Star the repo • 🐛 Report issues • 💡 Suggest features

**Connect with me:**
- GitHub: [@azizzoaib786](https://github.com/azizzoaib786)
- Email: azizzoaib786@gmail.com

---