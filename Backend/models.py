from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)
    chats = relationship("Chat", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True)
    question = Column(Text)
    answer = Column(Text)
    context = Column(Text)
    time = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="chats")
