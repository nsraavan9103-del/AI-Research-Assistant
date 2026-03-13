import shutil, os
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from models import Base, User, Document, Chat
from auth import create_token, get_current_user, hash_password, verify_password
from rag import build_vector_store, ask_rag, UPLOAD_DIR

Base.metadata.create_all(engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    hashed = hash_password(password)
    db.add(User(email=email, password=hashed))
    db.commit()
    db.close()
    return {"message": "User created"}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": create_token({"id": user.id})}

@app.post("/upload")
def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    db = SessionLocal()
    db.add(Document(filename=file.filename))
    db.commit()
    db.close()

    build_vector_store()
    return {"message": "Uploaded & Indexed"}

"""@app.post("/ask")
def ask(question: str = Form(...), user=Depends(get_current_user)):
    result = ask_rag(question)

    db = SessionLocal()
    db.add(Chat(
        question=question,
        answer=result["answer"],
        context="RAG response",
        user_id=user.id
    ))
    db.commit()
    db.close()

    return {"answer": result["answer"]}"""

@app.get("/history")
def history(user=Depends(get_current_user)):
    db = SessionLocal()
    chats = db.query(Chat).filter(Chat.user_id == user.id).all()
    db.close()
    return chats
