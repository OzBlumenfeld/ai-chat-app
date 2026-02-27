import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from uuid6 import uuid7
from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    collection_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="documents", lazy="selectin")
