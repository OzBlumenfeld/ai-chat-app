from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.uuid_mask import MaskedUUID



class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=16)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=16)


class AuthResponse(BaseModel):
    token: str
    email: str


class UserResponse(BaseModel):
    email: str


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    source: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: MaskedUUID
    original_filename: str
    file_size: int
    chunk_count: int | None
    status: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class UploadResponse(BaseModel):
    uploaded: list[DocumentResponse]
    errors: list[str]


class RequestHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: MaskedUUID
    question: str
    source: str
    created_at: datetime


class RequestHistoryDetailResponse(RequestHistoryResponse):
    response: str


class RequestHistoryListResponse(BaseModel):
    history: list[RequestHistoryResponse]


class MonthGroup(BaseModel):
    month: str
    entries: list[RequestHistoryResponse]


class RequestHistoryGroupedResponse(BaseModel):
    groups: list[MonthGroup]


class SendEmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str


class SendEmailResponse(BaseModel):
    success: bool
    message: str
