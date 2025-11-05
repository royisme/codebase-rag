"""启动阶段的安全初始化逻辑。"""

from __future__ import annotations

import uuid

from fastapi_users.db import SQLAlchemyUserDatabase
from loguru import logger

from config import settings
from database.models import User
from database.session import async_session_factory
from security.casbin_enforcer import get_enforcer
from security.constants import DEFAULT_POLICIES
from security.manager import UserManager
from security.schemas import UserCreate


async def ensure_default_superuser() -> User | None:
    """在数据库中确保存在一个超级管理员账户。"""

    async with async_session_factory() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)

        existing = await user_db.get_by_email(settings.auth_superuser_email)
        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                await session.commit()
            return existing

        user_create = UserCreate(
            email=settings.auth_superuser_email,
            password=settings.auth_superuser_password,
            full_name="System Administrator",
            role="admin",
        )

        superuser = await manager.create_superuser(user_create, safe=True)
        logger.info("Default superuser created", extra={"user_id": str(superuser.id)})
        return superuser


async def ensure_default_policies(superuser_id: uuid.UUID | None = None) -> None:
    """写入基础策略，确保管理员具备访问能力。"""

    enforcer = get_enforcer()
    changed = False

    for policy in DEFAULT_POLICIES:
        subject, domain, resource, action = policy

        # 如果存在旧的策略但动作不匹配（如历史版本使用read/write等），则移除后写入最新规则
        existing = enforcer.get_filtered_policy(0, subject, domain, resource)
        if existing and not any(p[3] == action for p in existing if len(p) > 3):
            for old_policy in existing:
                enforcer.remove_policy(*old_policy)
            changed = True

        if not enforcer.has_policy(*policy):
            enforcer.add_policy(*policy)
            changed = True

    if superuser_id:
        grouping = (str(superuser_id), "admin", "global")
        if not enforcer.has_grouping_policy(*grouping):
            enforcer.add_grouping_policy(*grouping)
            changed = True

    if changed:
        enforcer.save_policy()
        logger.info("Default RBAC policies ensured")
