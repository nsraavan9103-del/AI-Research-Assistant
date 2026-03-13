PREREQUISITES:

curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3
ollama pull nomic-embed-text


BACKEND DEPENDENCIES:

pip install fastapi uvicorn python-multipart sqlalchemy langchain langchain-community faiss-cpu pypdf "python-jose[cryptography]" passlib[bcrypt]
pip install fastapi uvicorn python-multipart sqlalchemy passlib[bcrypt] python-jose
pip install --upgrade langchain langchain-community langchain-core langchain-text-splitters langchain-ollama faiss-cpu pypdf

pip uninstall langchain-classic -y
pip uninstall langchain -y
pip install langchain langchain-community langchain-core langchain-text-splitters langchain-ollama


Run inside venv:
pip install --upgrade \
langchain \
langchain-community \
langchain-core \
langchain-text-splitters

FRONTEND:

npx create-react-app frontend
cd frontend
npm start
