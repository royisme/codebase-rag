"""Casbin 权限判定与依赖。"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Callable, Optional

import casbin
from casbin import util
from casbin_sqlalchemy_adapter import Adapter
from fastapi import Depends, HTTPException, Request, status
from loguru import logger

from config import settings
from database.models import User
from database.session import sync_engine
from security.auth import current_active_user
from services.audit_logger import audit_logger

# Global variables for lazy initialization
_adapter: Optional[Adapter] = None
_enforcer: Optional[casbin.Enforcer] = None
_model_path = Path(__file__).with_name("casbin_model.conf")


def normalize_action_pattern(action: Optional[str]) -> str:
    """Normalize action string to a valid regex pattern."""
    if not action:
        return ""
    pattern = action.strip()
    if pattern == "*":
        return ".*"
    return pattern


def regex_match_safe(name1: str, name2: str) -> bool:
    """防御性处理，确保策略中的 action 作为正则表达式时不会抛异常。"""
    pattern = normalize_action_pattern(name2)
    try:
        return re.match(pattern, name1) is not None
    except re.error as exc:
        logger.warning(
            "Invalid regex in policy action '%s': %s. Falling back to literal match.",
            name2,
            exc,
        )
        safe_pattern = re.escape(pattern)
        return re.match(safe_pattern, name1) is not None


def _initialize_enforcer() -> casbin.Enforcer:
    """Initialize the Casbin enforcer with lazy loading."""
    global _adapter, _enforcer

    if _enforcer is None:
        logger.info("Initializing Casbin enforcer...")
        _adapter = Adapter(sync_engine, filtered=False)
        _enforcer = casbin.Enforcer(str(_model_path), _adapter, enable_log=False)
        _enforcer.add_function("key_match2", util.key_match2)
        _enforcer.add_function("regex_match", regex_match_safe)
        _enforcer.enable_auto_save(settings.casbin_auto_save)
        _enforcer.load_policy()
        logger.info("Casbin enforcer initialized successfully")

    return _enforcer


async def reload_policies() -> None:
    """重新加载策略，确保内存态与数据库同步。"""
    enforcer = _initialize_enforcer()
    await asyncio.to_thread(enforcer.load_policy)


def get_enforcer() -> casbin.Enforcer:
    """获取Casbin执行器（懒加载）。"""
    return _initialize_enforcer()


def user_or_role_enforce(user: User, domain: str, resource: str, action: str) -> bool:
    """同时检查用户 ID 与角色是否具备权限。"""
    enforcer = _initialize_enforcer()

    subject_candidates = [str(user.id)]
    if user.role:
        subject_candidates.append(user.role)

    for subject in subject_candidates:
        if enforcer.enforce(subject, domain, resource, action):
            return True
    return False


def require_permission(
    resource: str,
    action: str,
    domain_getter: Optional[Callable[..., str]] = None,
):
    """生成 FastAPI 依赖，用于在路由中附加权限判定。"""

    async def dependency(
        request: Request,
        user: User = Depends(current_active_user),
    ) -> User:
        domain = "global"
        if domain_getter is not None:
            domain = domain_getter()

        if user_or_role_enforce(user, domain, resource, action):
            await audit_logger.record_event(
                actor_id=user.id,
                actor_email=user.email,
                resource=resource,
                action=action,
                status="success",
                target=domain,
                details="permission granted",
                metadata={"domain": domain},
                ip_address=request.client.host if request.client else None,
                session_id=request.headers.get("X-Session-Id"),
            )
            return user

        logger.warning(
            "Permission denied",
            extra={
                "user_id": str(user.id),
                "role": user.role,
                "domain": domain,
                "resource": resource,
                "action": action,
            },
        )
        await audit_logger.record_event(
            actor_id=user.id,
            actor_email=user.email,
            resource=resource,
            action=action,
            status="failure",
            target=domain,
            details="permission denied",
            metadata={"domain": domain},
            ip_address=request.client.host if request.client else None,
            session_id=request.headers.get("X-Session-Id"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RBAC: insufficient permission",
        )

    return dependency
