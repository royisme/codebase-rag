"""Seed demo data for user workbench MVP.
Usage: uv run python scripts/seed_demo_data.py --reset --count 3 --neo4j false
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import random
import uuid
from pathlib import Path

from database import async_session_factory
from database.models import KnowledgeSource, ParseJob, ParseStatus, KnowledgeQuery, KnowledgeNote, User
from config import settings


async def ensure_admin(session) -> User:
    result = await session.execute(
        __import__("sqlalchemy").select(User).where(User.email == settings.auth_superuser_email)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    # minimal user
    user = User(
        id=uuid.uuid4(),
        email=settings.auth_superuser_email,
        hashed_password="seeded",
        is_active=True,
        is_superuser=True,
        is_verified=True,
        role="admin",
    )
    session.add(user)
    await session.flush()
    return user


async def reset_tables(session):
    for model in [KnowledgeNote, KnowledgeQuery, ParseJob, KnowledgeSource]:
        await session.execute(__import__("sqlalchemy").text(f"DELETE FROM {model.__tablename__}"))
    await session.commit()


async def seed(count: int = 3):
    async with async_session_factory() as session:
        admin = await ensure_admin(session)

        # sources
        sources = []
        for i in range(count):
            src = KnowledgeSource(
                name=f"demo-repo-{i+1}",
                description="演示知识源",
                source_type="code",
                source_metadata={
                    "maintainers": [{"name": "Alice"}, {"name": "Bob"}],
                    "recommended_questions": [
                        "如何运行项目?",
                        "关键模块依赖有哪些?",
                    ],
                },
                is_active=True,
                created_by=admin.id,
            )
            session.add(src)
            sources.append(src)
        await session.flush()

        # parse jobs last 14 days
        for src in sources:
            for d in range(14):
                status = random.choice([ParseStatus.COMPLETED, ParseStatus.FAILED, ParseStatus.PENDING])
                job = ParseJob(
                    knowledge_source_id=src.id,
                    status=status,
                )
                job.created_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=d)
                session.add(job)

        # knowledge queries and notes
        for src in sources:
            for _ in range(random.randint(8, 15)):
                q = KnowledgeQuery(
                    user_id=admin.id,
                    source_id=src.id,
                    question="演示问题?",
                    answer_summary="演示回答摘要",
                    mode="hybrid",
                    duration_ms=random.randint(20, 4000),
                    status="success",
                )
                session.add(q)
        await session.flush()

        for _ in range(5):
            n = KnowledgeNote(
                user_id=admin.id,
                source_id=random.choice(sources).id,
                question="收藏问题?",
                answer_summary="收藏答案摘要",
            )
            session.add(n)

        await session.commit()
        print(f"Seeded admin: {admin.email}, sources: {len(sources)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--neo4j", type=str, default="false")
    args = parser.parse_args()

    async def run():
        async with async_session_factory() as session:
            if args.reset:
                await reset_tables(session)
        await seed(args.count)
        # optional demo answers directory
        Path(settings.graphrag_demo_answers_path).mkdir(parents=True, exist_ok=True)
        (Path(settings.graphrag_demo_answers_path) / "default.json").write_text(
            '{"answer": "这是一个演示回答。", "confidence": 0.8}', encoding="utf-8"
        )

    asyncio.run(run())


if __name__ == "__main__":
    main()
