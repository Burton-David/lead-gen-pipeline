"""SQLAlchemy models for extracted business leads (typed 2.0 style)."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Lead(Base):
    """A single business record scraped from a web page or chamber directory.

    List- and dict-valued fields are stored as JSON. Modern SQLite stores these as
    ``TEXT`` with JSON functions available; SQLAlchemy serialises and deserialises them.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    company_name: Mapped[str | None] = mapped_column(String, index=True)
    website: Mapped[str | None] = mapped_column(String, index=True)

    # The exact URL the data was scraped from (always recorded).
    scraped_from_url: Mapped[str] = mapped_column(String, index=True)
    canonical_url: Mapped[str | None] = mapped_column(String)

    description: Mapped[str | None] = mapped_column(Text)

    phone_numbers: Mapped[list[str] | None] = mapped_column(JSON)
    emails: Mapped[list[str] | None] = mapped_column(JSON)
    addresses: Mapped[list[str] | None] = mapped_column(JSON)
    social_media_links: Mapped[dict[str, str] | None] = mapped_column(JSON)
    industry_tags: Mapped[list[str] | None] = mapped_column(JSON)

    # Source chamber, when the lead came from a directory crawl.
    chamber_name: Mapped[str | None] = mapped_column(String, index=True)
    chamber_url: Mapped[str | None] = mapped_column(String, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
    )

    @property
    def phone_numbers_list(self) -> list[str] | None:
        return self.phone_numbers if isinstance(self.phone_numbers, list) else None

    @property
    def emails_list(self) -> list[str] | None:
        return self.emails if isinstance(self.emails, list) else None

    @property
    def addresses_list(self) -> list[str] | None:
        return self.addresses if isinstance(self.addresses, list) else None

    @property
    def social_media_dict(self) -> dict[str, str] | None:
        if isinstance(self.social_media_links, dict):
            return self.social_media_links
        return None

    def __repr__(self) -> str:
        return (
            f"<Lead(id={self.id}, company_name='{self.company_name}', "
            f"website='{self.website}')>"
        )


# Composite indexes for the queries the pipeline and CLI run most often.
Index("ix_company_website", Lead.company_name, Lead.website)
Index("ix_chamber_source", Lead.chamber_name, Lead.chamber_url)
