"""RBAC 策略相关服务函数。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CasbinRule
from security.casbin_enforcer import normalize_action_pattern


async def list_policies(session: AsyncSession) -> list[CasbinRule]:
    result = await session.execute(
        select(CasbinRule).where(CasbinRule.ptype == "p").order_by(CasbinRule.id)
    )
    return list(result.scalars().all())


async def get_policy(session: AsyncSession, policy_id: int) -> Optional[CasbinRule]:
    return await session.get(CasbinRule, policy_id)


async def delete_policy(session: AsyncSession, policy: CasbinRule) -> None:
    await session.delete(policy)


async def apply_policy_update(
    policy: CasbinRule,
    *,
    subject: Optional[str] = None,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
) -> CasbinRule:
    if subject is not None:
        policy.v0 = subject
    if domain is not None:
        policy.v1 = domain
    if resource is not None:
        policy.v2 = resource
    if action is not None:
        policy.v3 = normalize_action_pattern(action)
    return policy


async def ensure_policy(
    session: AsyncSession,
    *,
    subject: str,
    domain: str,
    resource: str,
    action: str,
) -> CasbinRule:
    stmt = select(CasbinRule).where(
        CasbinRule.ptype == "p",
        CasbinRule.v0 == subject,
        CasbinRule.v1 == domain,
        CasbinRule.v2 == resource,
    )
    result = await session.execute(stmt)
    policy = result.scalar_one_or_none()
    if policy:
        policy.v3 = normalize_action_pattern(action)
        return policy

    policy = CasbinRule(
        ptype="p",
        v0=subject,
        v1=domain,
        v2=resource,
        v3=normalize_action_pattern(action),
    )
    session.add(policy)
    await session.flush()
    return policy
