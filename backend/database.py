import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

os.makedirs("data", exist_ok=True)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/rivallens.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String)
    plan_tier = Column(String, default="starter") # starter, growth, enterprise
    company_name = Column(String, nullable=True) # for baseline comparison

class Scrape(Base):
    __tablename__ = "scrapes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, default=1)
    competitor_name = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String, index=True)
    payload = Column(JSON)  # Will store the intent signals and battlecard JSON

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
