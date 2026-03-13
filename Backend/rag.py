import os
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

UPLOAD_DIR = "uploads"
VECTOR_DIR = "vector_store"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = OllamaLLM(
    model="phi3:mini",      # Use the correct lightweight tag
    num_ctx=2048,           # Strictly limit to 2048 tokens to prevent OOM
    keep_alive="0m"         # Immediately offload from RAM after generation
)

def load_docs(path):
    if path.endswith(".pdf"):
        return PyPDFLoader(path).load()
    return TextLoader(path, encoding="utf-8").load()

def build_vector_store():
    docs = []
    for f in os.listdir(UPLOAD_DIR):
        docs.extend(load_docs(os.path.join(UPLOAD_DIR, f)))

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(VECTOR_DIR)

def ask_rag(question: str):
    db = FAISS.load_local(
        VECTOR_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )

    retriever = db.as_retriever()

    prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Answer ONLY from the context.

Context:
{context}

Question: {question}
""")

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
    )

    answer = chain.invoke(question)
    return {"answer": answer}
