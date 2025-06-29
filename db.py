from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class IngriaRequest(Base):
    __tablename__ = 'ingria_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    prompt = Column(Text)
    image_filename = Column(String, nullable=True)
    audio_filename = Column(String, nullable=True)
    video_filename = Column(String, nullable=True)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = 'memories'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('ingria_requests.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    memory_text = Column(Text, nullable=False)  # Текст воспоминания
    context = Column(Text, nullable=True)  # Контекст (что видели, слышали)
    emotions = Column(Text, nullable=True)  # Эмоции, которые испытала
    importance_score = Column(Integer, default=1)  # Важность воспоминания (1-10)
    memory_type = Column(String, nullable=True)  # Тип: visual, audio, conversation, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)  # Когда последний раз использовалось
    access_count = Column(Integer, default=0)  # Сколько раз использовалось
    hash = Column(String, nullable=True)  # Хеш для блокчейн-целостности
    previous_hash = Column(String, nullable=True)  # Хеш предыдущего блока

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    filetype = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    request_id = Column(Integer, ForeignKey('ingria_requests.id'), nullable=True)

class IngriaError(Base):
    __tablename__ = 'ingria_errors'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('ingria_requests.id'), nullable=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow) 