import enum
from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Index, String, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from weebit.database import Base

# The two analytics types for the link shortening service
class LinkEventType(str, enum.Enum):
    CREATE = 'CREATE'
    REDIRECT = 'REDIRECT'

class Link(Base):
    """A short code/link pair.

    Stores a shortened version of an HTTPS url.

    Attributes:
        id (int): Primary key.
        short_ref_code (str): 7-10 character short_code deterministically derived from the normalised_url.
        normalised_url (str): The "original" normalised URL for redirection.
        analytics (list[Analytic]): Collection of analytics events tied to this link.
    """
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_ref_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    normalised_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Virtual relationship property pointing to the analytics table.
    analytics: Mapped[list["Analytic"]] = relationship(
        back_populates="link",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_links_short_ref_code_hash", "short_ref_code", postgresql_using="hash"),
    )

class Analytic(Base):
    """Represents a discrete analytics event for a link's lifecycle.

    When the link is created or accessed, we store the event here for computing statistics.

    Attributes:
        id (int): Primary key.
        link_id (int): Foreign key existentially pointing to a short code/link pair.
        event_type (LinkEventType): Category of event (Create vs Redirect)
        timestamp (datetime): UTC timestamp for when the event occurred.
        browser_fingerprint (str | None): Optional hash of the browser fingerprint.
        link (Link): Virtual SQL property for lazy loading the relevant link property in a secondary query.
    """
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    link_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("links.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[LinkEventType] = mapped_column(
        SQLEnum(LinkEventType, name="link_event_type", native_enum=True),
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    browser_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Virtual relationship property pointing back to the links table.
    link: Mapped["Link"] = relationship(back_populates="analytics")

    __table_args__ = (
        Index("ix_analytics_src_timestamp", "link_id", "timestamp"),
    )