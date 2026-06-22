from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Redirect(Base):
    __tablename__ = "redirects"
    name = Column(String, primary_key=True, index=True)
    target_url = Column(String)


Base.metadata.create_all(bind=engine)
