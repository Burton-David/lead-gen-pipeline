# lead_gen_pipeline/models.py
# Version: Gemini-2025-05-26 14:35 EDT
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base # UPDATED IMPORT
from sqlalchemy.sql import func
from typing import List, Dict, Optional

Base = declarative_base()

class Lead(Base): # type: ignore
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String, nullable=True, index=True)
    website = Column(String, nullable=True, index=True) # Derived primary website
    scraped_from_url = Column(String, nullable=False, index=True) # The exact URL page was scraped from
    canonical_url = Column(String, nullable=True) # Canonical URL of the scraped page, if available
    description = Column(Text, nullable=True)

    # Storing lists and dicts as JSON
    phone_numbers = Column(JSON, nullable=True) # Stores List[str]
    emails = Column(JSON, nullable=True) # Stores List[str]
    addresses = Column(JSON, nullable=True) # Stores List[str]
    social_media_links = Column(JSON, nullable=True) # Stores Dict[str, str]

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, company_name='{self.company_name}', website='{self.website}')>"

    @property
    def phone_numbers_list(self) -> Optional[List[str]]:
        return self.phone_numbers if isinstance(self.phone_numbers, list) else None # type: ignore

    @property
    def emails_list(self) -> Optional[List[str]]:
        return self.emails if isinstance(self.emails, list) else None # type: ignore

    @property
    def addresses_list(self) -> Optional[List[str]]:
        return self.addresses if isinstance(self.addresses, list) else None # type: ignore

    @property
    def social_media_dict(self) -> Optional[Dict[str, str]]:
        return self.social_media_links if isinstance(self.social_media_links, dict) else None # type: ignore
