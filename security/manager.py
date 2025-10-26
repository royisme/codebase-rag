"""用户管理逻辑。"""

from __future__ import annotations

import uuid

from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.password import PasswordHelper
from loguru import logger

from config import settings
from database.models import User
from services.audit_logger import audit_logger


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_reset_token_secret
    verification_token_secret = settings.auth_verification_token_secret

    def __init__(self, user_db):
        super().__init__(user_db)
        self.password_helper = PasswordHelper()

    async def on_after_register(self, user: User, request=None):  # pragma: no cover - hook
        self.logger.info("User registered", extra={"user_id": str(user.id)})
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource="auth",
            action="register",
            status="success",
            target=user.email,
        )

    async def on_after_forgot_password(self, user: User, token: str, request=None):  # pragma: no cover - hook
        self.logger.info(
            "Password reset requested",
            extra={"user_id": str(user.id), "token": token},
        )
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource="auth",
            action="forgot_password",
            status="success",
            target=user.email,
            details="reset token issued",
        )

    async def on_after_request_verify(self, user: User, token: str, request=None):  # pragma: no cover
        self.logger.info(
            "User verification requested",
            extra={"user_id": str(user.id), "token": token},
        )
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource="auth",
            action="request_verify",
            status="success",
            target=user.email,
        )

    async def on_after_login(self, user: User, request=None, response=None):  # pragma: no cover
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource="auth",
            action="login_attempt",
            status="success",
            target="login",
        )

    async def on_after_logout(self, user: User, request=None, response=None):  # pragma: no cover
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource="auth",
            action="logout",
            status="success",
            target="logout",
        )

    async def create_superuser(self, user_create, safe: bool = False):
        """Create a superuser with admin role."""
        # Set role and verified status on the UserCreate object
        user_create.role = "admin"
        user_create.is_verified = True

        user = await self.create(user_create)
        return user
