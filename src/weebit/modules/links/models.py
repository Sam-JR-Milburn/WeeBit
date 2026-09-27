from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from weebit.database import Base

class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_ref_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    normalised_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    __table_args__ = (
        Index("ix_links_short_ref_code_hash", "short_ref_code", postgresql_using="hash"),
    )