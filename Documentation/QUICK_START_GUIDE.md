# AI Research Assistant - Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide helps you quickly set up and run the AI Research Assistant project.

---

## Step 1: Install Ollama (1 minute)

Ollama provides the LLM and embedding models required by the system.

### Download and Install
- Visit [ollama.ai](https://ollama.ai)
- Download for your OS (Mac, Linux, Windows)
- Install and run `ollama serve` in a terminal

### Pull Required Models
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull models
ollama pull phi3           # 7B LLM (~4GB)
ollama pull nomic-embed-text  # Embeddings (~300MB)

# Verify installation
curl http://localhost:11434/api/tags
```

---

## Step 2: Setup Backend (2 minutes)

```bash
# Navigate to backend folder
cd Backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# (Most defaults work for local development)

# Start the server
python -m uvicorn main:app --reload --port 8000

# ✓ Backend running at http://localhost:8000
```

---

## Step 3: Setup Frontend (2 minutes)

```bash
# In new terminal, navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Update API endpoint in .env.local
# VITE_API_URL=http://localhost:8000

# Start dev server
npm run dev

# ✓ Frontend running at http://localhost:5173
```

---

## Now You're Ready! 🎉

### Access the Application
1. Open browser: **http://localhost:5173**
2. Register a new account
3. Upload a PDF or text document
4. Ask questions about your document!

---

## Common Commands

### Backend Development
```bash
# Start server with auto-reload
python -m uvicorn main:app --reload

# Run tests
pytest tests/

# Database migration
python -m alembic upgrade head

# Create new migration
python -m alembic revision --autogenerate -m "Description"
```

### Frontend Development
```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Lint code
npm run lint
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" on localhost:11434 | Run `ollama serve` in separate terminal |
| Module not found error | Run `pip install -r requirements.txt` again |
| Port 8000 already in use | Kill existing process or use `--port 8001` |
| Frontend can't reach backend | Check `VITE_API_URL` in `.env.local` |
| Ollama models too slow | Ensure 8GB+ RAM available; close other apps |

---

## File Upload Examples

### Create a Test Document
```bash
# Create a simple text file
echo "The AI Research Assistant helps answer questions about uploaded documents using RAG technology." > sample.txt

# Or use your own PDF file
```

### Upload via UI
1. Click "Upload Document" button
2. Select your file
3. Wait for "Indexing..." status
4. Status changes to "Ready" ✓

---

## Example Queries

After uploading a document, try these questions:

- "What are the main topics covered?"
- "Summarize the key findings"
- "What methodology was used?"
- "Who are the authors?"
- "What conclusions are presented?"

---

## Next Steps

- 📖 Read [COMPREHENSIVE_PROJECT_DOCUMENTATION.md](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md)
- 🔌 Explore API endpoints at [http://localhost:8000/docs](http://localhost:8000/docs)
- 📚 Check API reference below

---

## API Quick Reference

### Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","full_name":"John"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

### Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

### Ask Question
```bash
curl -X POST http://localhost:8000/api/v1/query/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "document_ids": ["doc-id"],
    "stream": false
  }'
```

---

## Need Help?

- Check logs in `logs/` directory
- Review `.env` configuration
- Visit [Full Documentation](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md)
- Check backend error response at localhost:8000/docs

---

**Happy researching!** 🔍✨
