import uuid
from sqlalchemy import Column, Enum
from sqlalchemy import UUID
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    activation_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean(), default=False)

    messages = relationship(argument="Message", back_populates="user")
    connection_history = relationship(argument="ConnectionHistory", back_populates="user")


class ActivationStatus(str, Enum):
    PENDING = "pending"
    ACTIVATED = "activated"
    EXPIRED = "expired"


class ActivationCode(Base):
    __tablename__ = "account_activation_codes"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=True)
    username = Column(String, nullable=True)  
    hashed_password = Column(String, nullable=True)  
    code = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    status = Column(String, nullable=False, default='pending')


    @property
    def is_expired(self) -> bool:
        return ActivationStatus.EXPIRED in self.status

    @property
    def is_activated(self) -> bool:
        return ActivationStatus.ACTIVATED in self.status

    @property
    def is_pending(self) -> bool:
        return ActivationStatus.PENDING in self.status


class ConnectionHistory(Base):
    __tablename__ = "connection_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    connected_at = Column(DateTime(timezone=True), default=func.now())
    disconnected_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="connection_history")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship(argument="User", back_populates="messages")
