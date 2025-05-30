# lead_gen_pipeline/models.py
# Version: Production with Chamber Directory Support
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.orm import declarative_base 
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import DATETIME as SQLITE_DATETIME # For SQLite specific datetime
import datetime

# For other databases, you might use:
# from sqlalchemy.types import DateTime

Base = declarative_base()

class Lead(Base): # type: ignore
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    company_name = Column(String, nullable=True, index=True)
    website = Column(String, nullable=True, index=True) # Primary website of the company
    
    scraped_from_url = Column(String, nullable=False, index=True) # The exact URL the data was scraped from
    canonical_url = Column(String, nullable=True) # Canonical URL of the scraped page, if available
    
    description = Column(Text, nullable=True)

    # Storing lists and dicts as JSON.
    # For databases that don't natively support JSON well (older SQLite),
    # SQLAlchemy often maps this to TEXT. Modern SQLite supports JSON.
    phone_numbers = Column(JSON, nullable=True) # Stores List[str]
    emails = Column(JSON, nullable=True) # Stores List[str]
    addresses = Column(JSON, nullable=True) # Stores List[str]
    social_media_links = Column(JSON, nullable=True) # Stores Dict[str, str] like {"linkedin": "url", "twitter": "url"}
    
    # Industry/Category related fields (can be expanded later)
    industry_tags = Column(JSON, nullable=True) # List[str] of industry tags/keywords
    
    # Chamber directory specific fields (NEW)
    chamber_name = Column(String, nullable=True, index=True) # Name of the source chamber
    chamber_url = Column(String, nullable=True, index=True) # URL of the source chamber
    
    # Timestamps
    # For SQLite, ensure datetime objects are stored in a way that allows proper querying.
    # Using server_default=func.now() is generally good for SQL databases.
    # For SQLite, func.now() often translates to julianday('now') or similar.
    # Using Python's datetime.datetime.utcnow for default can be more portable if managed by Python.
    created_at = Column(SQLITE_DATETIME(timezone=True), server_default=func.now(), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(SQLITE_DATETIME(timezone=True), server_default=func.now(), onupdate=func.now(), default=datetime.datetime.now(datetime.timezone.utc))

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, company_name='{self.company_name}', website='{self.website}')>"

    # Optional: Add properties for easier access to JSON fields if needed,
    # though direct access is often fine. E.g.:
    # @property
    # def phone_numbers_list(self) -> Optional[List[str]]:
    #     return self.phone_numbers if isinstance(self.phone_numbers, list) else None

# Example of a composite index if we often query by company name and website together
Index('ix_company_website', Lead.company_name, Lead.website)

# Index for chamber-based queries
Index('ix_chamber_source', Lead.chamber_name, Lead.chamber_url)

# You could add other models here later, e.g., Company, Contact, Source, etc.
# class Company(Base):
#     __tablename__ = "companies"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, unique=True, index=True)
#     # ... other company-specific fields
