import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime

# By default, creates a local SQLite file. On Railway, we'll give it a Postgres URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pipelineom_global.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class GlobalLead(Base):
    __tablename__ = "global_leads"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True) # Used to link the email later
    owner_email = Column(String, index=True, nullable=True) # Who uploaded this?
    
    # LinkedIn Data
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    url = Column(String, nullable=True)
    company = Column(String, nullable=True)
    position = Column(String, nullable=True)
    connected_on = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SiteEmail(Base):
    """Emails captured on the site (subscribe form, report unlock, etc.)."""
    __tablename__ = "site_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    source = Column(String, nullable=True, index=True)  # e.g. "subscribe", "report_unlock"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# Create the tables
Base.metadata.create_all(bind=engine)