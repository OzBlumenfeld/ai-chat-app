
from abc import ABC, abstractmethod
from pydantic import BaseModel, EmailStr


class ContactDetails(BaseModel):
    email: EmailStr


class NotificationInput(BaseModel):
    sender_email: str
    recipient_email: str
    subject: str
    body: str


class NotificationSender(ABC):

    @abstractmethod
    async def notify(self, notification_input: NotificationInput) -> bool:
        pass



