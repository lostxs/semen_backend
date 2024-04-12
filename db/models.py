import uuid

from sqlalchemy import (
    Column,
    UUID,
    String,
    Boolean,
    Integer,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    is_active = Column(Boolean(), default=False)

    account_activation_codes = relationship(
        "ActivationCode", back_populates="user", uselist=False
    )
    messages = relationship("Message", back_populates="user")
    connection_history = relationship("ConnectionHistory", back_populates="user")


class ActivationCode(Base):
    __tablename__ = "account_activation_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    code = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="account_activation_codes")


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

    user = relationship("User", back_populates="messages")
