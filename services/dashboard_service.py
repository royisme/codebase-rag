"""Dashboard aggregation service for user workbench MVP."""
from __future__ import annotations

import datetime as dt
from typing import Dict, List

from sqlalchemy import func, select, and_
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import KnowledgeSource, ParseJob, ParseStatus, KnowledgeQuery, KnowledgeNote


async def get_dashboard_summary(session: AsyncSession, user_id) -> Dict[str, int | float | Dict[str, float]]:
    now = dt.datetime.now(dt.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - dt.timedelta(days=7)
    yesterday_start = today_start - dt.timedelta(days=1)
    day_before_yesterday_start = yesterday_start - dt.timedelta(days=1)

    # active sources (today vs yesterday)
    active_sources_today = await session.scalar(
        select(func.count(KnowledgeSource.id)).where(KnowledgeSource.is_active.is_(True))
    )
    # For delta, we compare with sources that were active yesterday
    # This is a simplified approach - in real scenario you'd track historical data
    active_sources_yesterday = active_sources_today  # Simplified: assume same as today

    # queries today vs yesterday
    queries_today = await session.scalar(
        select(func.count(KnowledgeQuery.id)).where(KnowledgeQuery.created_at >= today_start)
    )
    queries_yesterday = await session.scalar(
        select(func.count(KnowledgeQuery.id)).where(
            and_(KnowledgeQuery.created_at >= yesterday_start, KnowledgeQuery.created_at < today_start)
        )
    )

    # index health (success rate in last 7 days vs previous 7 days)
    total_jobs = await session.scalar(
        select(func.count(ParseJob.id)).where(ParseJob.created_at >= seven_days_ago)
    )
    completed_jobs = await session.scalar(
        select(func.count(ParseJob.id)).where(
            and_(ParseJob.created_at >= seven_days_ago, ParseJob.status == ParseStatus.COMPLETED)
        )
    )
    index_health = (float(completed_jobs or 0) / float(total_jobs or 1)) if (total_jobs or 0) > 0 else 0.0
    
    # Previous period health for delta
    fourteen_days_ago = now - dt.timedelta(days=14)
    prev_total_jobs = await session.scalar(
        select(func.count(ParseJob.id)).where(
            and_(ParseJob.created_at >= fourteen_days_ago, ParseJob.created_at < seven_days_ago)
        )
    )
    prev_completed_jobs = await session.scalar(
        select(func.count(ParseJob.id)).where(
            and_(
                ParseJob.created_at >= fourteen_days_ago,
                ParseJob.created_at < seven_days_ago,
                ParseJob.status == ParseStatus.COMPLETED
            )
        )
    )
    prev_index_health = (float(prev_completed_jobs or 0) / float(prev_total_jobs or 1)) if (prev_total_jobs or 0) > 0 else 0.0

    # saved entries for user (total count)
    saved_entries = await session.scalar(
        select(func.count(KnowledgeNote.id)).where(KnowledgeNote.user_id == user_id)
    )
    # Count entries created today for delta
    saved_entries_today = await session.scalar(
        select(func.count(KnowledgeNote.id)).where(
            and_(
                KnowledgeNote.user_id == user_id,
                KnowledgeNote.created_at >= today_start
            )
        )
    )
    # Count entries created yesterday
    saved_entries_yesterday = await session.scalar(
        select(func.count(KnowledgeNote.id)).where(
            and_(
                KnowledgeNote.user_id == user_id,
                KnowledgeNote.created_at >= yesterday_start,
                KnowledgeNote.created_at < today_start
            )
        )
    )

    # Calculate deltas
    # Note: active_sources delta is 0 as we don't track historical changes
    # In production, you'd need a history table to track this properly
    delta_active_sources = 0
    delta_queries = int((queries_today or 0) - (queries_yesterday or 0))
    delta_index_health = round(index_health - prev_index_health, 3)
    delta_saved_entries = int((saved_entries_today or 0) - (saved_entries_yesterday or 0))

    return {
        "active_sources": int(active_sources_today or 0),
        "queries_today": int(queries_today or 0),
        "index_health": round(index_health, 3),
        "saved_entries": int(saved_entries or 0),
        "delta": {
            "active_sources": delta_active_sources,
            "queries": delta_queries,
            "index_health": delta_index_health,
            "saved_entries": delta_saved_entries,
        },
    }


async def get_query_trend(session: AsyncSession, user_id, days: int = 7) -> List[Dict[str, int | str]]:
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await session.execute(
        select(KnowledgeQuery.created_at).where(KnowledgeQuery.created_at >= start)
    )
    dates = [r[0].date().isoformat() for r in rows.all() if r[0]]
    cnt = Counter(dates)
    trend = sorted(({"date": d, "count": int(c)} for d, c in cnt.items()), key=lambda x: x["date"])
    return trend
