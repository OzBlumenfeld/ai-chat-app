import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from uuid6 import uuid7
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(String)
    answer: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String(3))  # "rag" or "llm"
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="requests", lazy="selectin")
