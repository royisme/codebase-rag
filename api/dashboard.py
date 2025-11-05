"""User dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from datetime import datetime, timedelta, timezone
from services.dashboard_service import get_dashboard_summary, get_query_trend
from services.source_service import get_source_service
from database.models import ParseStatus, KnowledgeQuery
from security.casbin_enforcer import require_permission
from sqlalchemy import select, func
from security.auth import current_active_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        d = await get_dashboard_summary(session, getattr(user, "id", None))
        delta = d.get("delta", {})
        # map to camelCase
        return {
            "activeSources": d.get("active_sources", 0),
            "queriesToday": d.get("queries_today", 0),
            "indexHealth": d.get("index_health", 0.0),
            "savedEntries": d.get("saved_entries", 0),
            "delta": {
                "activeSources": delta.get("active_sources", 0),
                "queriesToday": delta.get("queries", 0),
                "indexHealth": delta.get("index_health", 0.0),
                "savedEntries": delta.get("saved_entries", 0),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query-trend")
async def dashboard_query_trend(
    days: int = 7,
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        data = await get_query_trend(session, getattr(user, "id", None), days=days)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-status")
async def dashboard_source_status(
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取知识源状态列表用于仪表盘展示。"""
    try:
        from database.models import KnowledgeSource, ParseJob
        from sqlalchemy.orm import selectinload
        
        # Query sources with eager-loaded parse_jobs to avoid lazy loading issues
        result_sources = await session.execute(
            select(KnowledgeSource)
            .where(KnowledgeSource.is_active.is_(True))
            .options(selectinload(KnowledgeSource.parse_jobs))
            .limit(100)
        )
        sources = result_sources.scalars().all()
        
        # Get query counts for last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        rows = await session.execute(
            select(KnowledgeQuery.source_id, func.count(KnowledgeQuery.id))
            .where(KnowledgeQuery.created_at >= seven_days_ago)
            .group_by(KnowledgeQuery.source_id)
        )
        query_counts = {str(k or ""): int(v) for k, v in rows.all()}
        
        result = []
        for source in sources:
            meta = getattr(source, "source_metadata", None) or {}
            
            # Determine status based on last_synced_at and parse job status
            status = "healthy"
            if not source.last_synced_at:
                status = "failed"
            else:
                days_since_sync = (datetime.now(timezone.utc) - source.last_synced_at).days
                if days_since_sync > 7:
                    status = "outdated"
            
            # Check if currently indexing (parse_jobs is now eagerly loaded)
            if source.parse_jobs:
                latest_job = max(source.parse_jobs, key=lambda j: j.created_at or datetime.min.replace(tzinfo=timezone.utc))
                if latest_job.status == ParseStatus.RUNNING:
                    status = "indexing"
                elif latest_job.status == ParseStatus.FAILED:
                    status = "failed"

            result.append(
                {
                    "id": str(source.id),
                    "name": source.name,
                    "alias": meta.get("alias") or source.name,
                    "branch": meta.get("branch") or "main",
                    "lastIndexed": source.last_synced_at.isoformat()
                    if source.last_synced_at
                    else None,
                    "status": status,
                    "queryCount7d": query_counts.get(str(source.id), 0),
                }
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
