"""认证与 RBAC 相关路由。"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_users.authentication import Strategy
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from database.models.user import User
from security.auth import (
    auth_backend,
    current_active_user,
    current_superuser,
    fastapi_users,
)
from security.casbin_enforcer import get_enforcer, reload_policies, require_permission
from security.constants import DEFAULT_ROLES
from security.schemas import (
    PolicyCreateRequest,
    PolicySchema,
    PolicyUpdateRequest,
    RoleSchema,
    UserCreate,
    UserRead,
    UserUpdate,
)
from services import rbac_service
from services.audit_logger import audit_logger, list_audit_events

router = APIRouter()

# 认证与用户管理路由
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["Auth"],
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/admin/users",
    tags=["RBAC"],
)


@router.post("/auth/refresh", tags=["Auth"])
async def refresh_token(
    user=Depends(current_active_user),
    strategy: Strategy = Depends(auth_backend.get_strategy),
):
    """基于现有登录状态刷新访问令牌。"""

    response = await auth_backend.login(strategy, user)
    await audit_logger.record_event(
        actor_id=user.id,
        actor_email=user.email,
        resource="auth",
        action="refresh_token",
        status="success",
        target="refresh",
    )
    return response


@router.get("/auth/me", response_model=UserRead, tags=["Auth"])
async def get_current_user_profile(
    user=Depends(current_active_user),
):
    """返回当前登录用户的基础资料。"""
    return UserRead.model_validate(user)


@router.get("/admin/users", tags=["RBAC"])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
    user=Depends(current_superuser),
) -> dict[str, Any]:
    """获取所有用户列表（仅限超级管理员）。"""

    offset = (page - 1) * limit

    # Get total count
    count_stmt = select(func.count()).select_from(User)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Get users with pagination
    stmt = select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
    result = await session.execute(stmt)
    users = result.scalars().all()

    return {
        "users": [UserRead.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/admin/roles", response_model=list[RoleSchema], tags=["RBAC"])
async def list_roles() -> list[RoleSchema]:
    return [RoleSchema(**role) for role in DEFAULT_ROLES]


@router.get(
    "/admin/policies",
    response_model=list[PolicySchema],
    tags=["RBAC"],
    dependencies=[Depends(require_permission("/admin/policies", "GET"))],
)
async def list_policies(
    session: AsyncSession = Depends(get_async_session),
) -> list[PolicySchema]:
    policies = await rbac_service.list_policies(session)
    return [
        PolicySchema(
            id=policy.id,
            subject=policy.v0 or "",
            domain=policy.v1 or "",
            resource=policy.v2 or "",
            action=policy.v3 or "",
        )
        for policy in policies
    ]


@router.post(
    "/admin/policies",
    response_model=PolicySchema,
    status_code=status.HTTP_201_CREATED,
    tags=["RBAC"],
)
async def create_policy(
    payload: PolicyCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_permission("/admin/policies", "POST")),
):
    enforcer = get_enforcer()
    added = enforcer.add_policy(
        payload.subject,
        payload.domain,
        payload.resource,
        payload.action,
    )
    if not added:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy already exists",
        )

    await session.commit()
    await reload_policies()

    await audit_logger.record_event(
        actor_id=user.id,
        actor_email=user.email,
        resource=payload.resource,
        action="create_policy",
        status="success",
        target=payload.subject,
        metadata=payload.model_dump(),
    )

    policies = await rbac_service.list_policies(session)
    policy = next(
        (
            p
            for p in policies
            if p.v0 == payload.subject
            and p.v1 == payload.domain
            and p.v2 == payload.resource
            and p.v3 == payload.action
        ),
        None,
    )
    if not policy:
        raise HTTPException(
            status_code=500, detail="Policy persisted but not retrievable"
        )
    return PolicySchema(
        id=policy.id,
        subject=policy.v0 or "",
        domain=policy.v1 or "",
        resource=policy.v2 or "",
        action=policy.v3 or "",
    )


@router.patch(
    "/admin/policies/{policy_id}",
    response_model=PolicySchema,
    tags=["RBAC"],
)
async def update_policy(
    policy_id: int,
    payload: PolicyUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_permission("/admin/policies", "PATCH")),
):
    policy = await rbac_service.get_policy(session, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found"
        )

    await rbac_service.apply_policy_update(
        policy,
        subject=payload.subject,
        domain=payload.domain,
        resource=payload.resource,
        action=payload.action,
    )
    await session.commit()
    await reload_policies()

    await audit_logger.record_event(
        actor_id=user.id,
        actor_email=user.email,
        resource=policy.v2 or "",
        action="update_policy",
        status="success",
        target=policy.v0 or "",
        metadata=payload.model_dump(exclude_none=True),
    )

    return PolicySchema(
        id=policy.id,
        subject=policy.v0 or "",
        domain=policy.v1 or "",
        resource=policy.v2 or "",
        action=policy.v3 or "",
    )


@router.delete(
    "/admin/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RBAC"],
)
async def delete_policy(
    policy_id: int,
    session: AsyncSession = Depends(get_async_session),
    user=Depends(require_permission("/admin/policies", "DELETE")),
):
    policy = await rbac_service.get_policy(session, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found"
        )

    await audit_logger.record_event(
        actor_id=user.id,
        actor_email=user.email,
        resource=policy.v2 or "",
        action="delete_policy",
        status="success",
        target=policy.v0 or "",
    )

    await rbac_service.delete_policy(session, policy)
    await session.commit()
    await reload_policies()
    return None


@router.get(
    "/admin/audit",
    tags=["RBAC"],
    dependencies=[Depends(require_permission("/admin/audit", "GET"))],
)
async def get_audit_logs(
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    offset = (page - 1) * limit

    def _parse_timestamp(value: Optional[str]) -> Optional[dt.datetime]:
        if not value:
            return None
        try:
            return dt.datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid timestamp format"
            ) from exc

    items, total = await list_audit_events(
        session,
        actor=actor,
        action=action,
        status=status_filter,
        start=_parse_timestamp(start),
        end=_parse_timestamp(end),
        limit=limit,
        offset=offset,
    )

    audits = [
        {
            "id": str(item.id),
            "actor": item.actor_email or "system",
            "action": item.action,
            "target": item.target or item.resource,
            "status": item.status,
            "timestamp": item.created_at.isoformat(),
            "details": item.details,
        }
        for item in items
    ]

    return {
        "audits": audits,
        "total": total,
        "page": page,
        "limit": limit,
    }
