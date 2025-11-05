"""知识源管理服务。"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Select, func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import KnowledgeSource, ParseJob, ParseStatus, User
from schemas import KnowledgeSourceCreate, KnowledgeSourceUpdate, ParseJobCreate, ParseJobUpdate
from services.audit_logger import audit_logger


class SourceServiceError(Exception):
    """知识源服务异常基类。"""
    pass


class SourceNotFoundError(SourceServiceError):
    """知识源未找到异常。"""
    pass


class SourceValidationError(SourceServiceError):
    """知识源验证异常。"""
    pass


class JobNotFoundError(SourceServiceError):
    """解析任务未找到异常。"""
    pass


class InvalidJobTransitionError(SourceServiceError):
    """无效的任务状态转换异常。"""
    pass


class SourceService:
    """知识源和解析任务管理服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # KnowledgeSource CRUD operations
    async def create_source(
        self,
        source_data: KnowledgeSourceCreate,
        created_by: Optional[uuid.UUID] = None,
        actor_info: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeSource:
        """创建新的知识源。"""
        # 验证知识源名称唯一性
        existing = await self.get_source_by_name(source_data.name)
        if existing:
            raise SourceValidationError(f"知识源名称 '{source_data.name}' 已存在")

        source = KnowledgeSource(
            name=source_data.name,
            description=source_data.description,
            source_type=source_data.source_type,
            connection_config=source_data.connection_config,
            source_metadata=source_data.metadata,
            is_active=source_data.is_active,
            sync_frequency_minutes=source_data.sync_frequency_minutes,
            created_by=created_by,
        )

        self.session.add(source)
        await self.session.flush()

        # 记录审计日志
        await audit_logger.record_event(
            actor_id=created_by,
            actor_email=actor_info.get("email") if actor_info else None,
            resource="knowledge_sources",
            action="create",
            status="success",
            target=str(source.id),
            details=f"创建知识源: {source.name}",
            metadata={
                "source_type": source.source_type,
                "is_active": source.is_active,
            },
            ip_address=actor_info.get("ip_address") if actor_info else None,
            session=self.session,
        )

        return source

    async def get_source_by_id(
        self,
        source_id: uuid.UUID,
        include_jobs: bool = False,
    ) -> Optional[KnowledgeSource]:
        """根据ID获取知识源。"""
        query = select(KnowledgeSource).where(KnowledgeSource.id == source_id)

        if include_jobs:
            query = query.options(selectinload(KnowledgeSource.parse_jobs))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_source_by_name(
        self,
        name: str,
    ) -> Optional[KnowledgeSource]:
        """根据名称获取知识源。"""
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.name == name)
        )
        return result.scalar_one_or_none()

    async def list_sources(
        self,
        *,
        page: int = 1,
        size: int = 20,
        source_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> Tuple[List[KnowledgeSource], int]:
        """分页获取知识源列表。"""
        filters = []

        if source_type:
            filters.append(KnowledgeSource.source_type == source_type)

        if is_active is not None:
            filters.append(KnowledgeSource.is_active == is_active)

        if created_by:
            filters.append(KnowledgeSource.created_by == created_by)

        if search:
            search_filter = or_(
                KnowledgeSource.name.ilike(f"%{search}%"),
                KnowledgeSource.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)

        # 构建查询
        query: Select[tuple[KnowledgeSource]] = select(KnowledgeSource)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(KnowledgeSource.created_at.desc())

        # 获取总数
        count_query = select(func.count(KnowledgeSource.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total = await self.session.scalar(count_query)

        # 分页查询
        offset = (page - 1) * size
        result = await self.session.execute(query.limit(size).offset(offset))
        sources = list(result.scalars().all())

        return sources, int(total or 0)

    async def update_source(
        self,
        source_id: uuid.UUID,
        update_data: KnowledgeSourceUpdate,
        actor_info: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeSource:
        """更新知识源。"""
        source = await self.get_source_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"知识源 {source_id} 不存在")

        # 如果更新名称，检查唯一性
        if update_data.name and update_data.name != source.name:
            existing = await self.get_source_by_name(update_data.name)
            if existing:
                raise SourceValidationError(f"知识源名称 '{update_data.name}' 已存在")

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_fields = list(update_dict.keys())

        if "metadata" in update_dict:
            source.source_metadata = update_dict.pop("metadata")

        for field, value in update_dict.items():
            setattr(source, field, value)

        await self.session.flush()

        # 记录审计日志
        await audit_logger.record_event(
            actor_id=actor_info.get("user_id") if actor_info else None,
            actor_email=actor_info.get("email") if actor_info else None,
            resource="knowledge_sources",
            action="update",
            status="success",
            target=str(source.id),
            details=f"更新知识源: {source.name}",
            metadata={"updated_fields": updated_fields},
            ip_address=actor_info.get("ip_address") if actor_info else None,
            session=self.session,
        )

        return source

    async def delete_source(
        self,
        source_id: uuid.UUID,
        actor_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """软删除知识源（设置为非活跃）。"""
        source = await self.get_source_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"知识源 {source_id} 不存在")

        source.is_active = False
        await self.session.flush()

        # 记录审计日志
        await audit_logger.record_event(
            actor_id=actor_info.get("user_id") if actor_info else None,
            actor_email=actor_info.get("email") if actor_info else None,
            resource="knowledge_sources",
            action="delete",
            status="success",
            target=str(source.id),
            details=f"软删除知识源: {source.name}",
            ip_address=actor_info.get("ip_address") if actor_info else None,
            session=self.session,
        )

    # ParseJob operations
    async def create_parse_job(
        self,
        job_data: ParseJobCreate,
        created_by: Optional[uuid.UUID] = None,
        actor_info: Optional[Dict[str, Any]] = None,
    ) -> ParseJob:
        """创建解析任务。"""
        # 验证知识源存在
        source = await self.get_source_by_id(job_data.knowledge_source_id)
        if not source:
            raise SourceNotFoundError(f"知识源 {job_data.knowledge_source_id} 不存在")

        # 检查是否有正在运行的任务
        running_job = await self.get_running_job(job_data.knowledge_source_id)
        if running_job:
            raise SourceValidationError(
                f"知识源 {source.name} 已有正在运行的解析任务 {running_job.id}"
            )

        job = ParseJob(
            knowledge_source_id=job_data.knowledge_source_id,
            status=ParseStatus.PENDING,
            job_config=job_data.job_config,
            created_by=created_by,
        )

        self.session.add(job)
        await self.session.flush()

        # 记录审计日志
        await audit_logger.record_event(
            actor_id=created_by,
            actor_email=actor_info.get("email") if actor_info else None,
            resource="parse_jobs",
            action="create",
            status="success",
            target=str(job.id),
            details=f"为知识源 '{source.name}' 创建解析任务",
            metadata={
                "knowledge_source_id": str(job_data.knowledge_source_id),
                "source_name": source.name,
            },
            ip_address=actor_info.get("ip_address") if actor_info else None,
            session=self.session,
        )

        return job

    async def get_job_by_id(self, job_id: uuid.UUID) -> Optional[ParseJob]:
        """根据ID获取解析任务。"""
        result = await self.session.execute(
            select(ParseJob)
            .options(selectinload(ParseJob.knowledge_source))
            .where(ParseJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_running_job(
        self,
        source_id: uuid.UUID,
    ) -> Optional[ParseJob]:
        """获取指定知识源的正在运行的任务。"""
        result = await self.session.execute(
            select(ParseJob)
            .where(
                and_(
                    ParseJob.knowledge_source_id == source_id,
                    ParseJob.status.in_([ParseStatus.PENDING, ParseStatus.RUNNING])
                )
            )
            .order_by(ParseJob.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        *,
        page: int = 1,
        size: int = 20,
        source_id: Optional[uuid.UUID] = None,
        status: Optional[ParseStatus] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> Tuple[List[ParseJob], int]:
        """分页获取解析任务列表。"""
        filters = []

        if source_id:
            filters.append(ParseJob.knowledge_source_id == source_id)

        if status:
            filters.append(ParseJob.status == status)

        if created_by:
            filters.append(ParseJob.created_by == created_by)

        # 构建查询
        query: Select[tuple[ParseJob]] = (
            select(ParseJob)
            .options(selectinload(ParseJob.knowledge_source))
        )

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(ParseJob.created_at.desc())

        # 获取总数
        count_query = select(func.count(ParseJob.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total = await self.session.scalar(count_query)

        # 分页查询
        offset = (page - 1) * size
        result = await self.session.execute(query.limit(size).offset(offset))
        jobs = list(result.scalars().all())

        return jobs, int(total or 0)

    async def update_job(
        self,
        job_id: uuid.UUID,
        update_data: ParseJobUpdate,
        actor_info: Optional[Dict[str, Any]] = None,
    ) -> ParseJob:
        """更新解析任务。"""
        job = await self.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"解析任务 {job_id} 不存在")

        # 验证状态转换
        if update_data.status and update_data.status != job.status:
            self._validate_status_transition(job.status, update_data.status)

        # 设置时间戳
        update_dict = update_data.model_dump(exclude_unset=True)
        if update_data.status == ParseStatus.RUNNING and job.status != ParseStatus.RUNNING:
            update_dict["started_at"] = dt.datetime.now(dt.timezone.utc)
        elif update_data.status in [ParseStatus.COMPLETED, ParseStatus.FAILED, ParseStatus.CANCELLED]:
            update_dict["completed_at"] = dt.datetime.now(dt.timezone.utc)

        # 更新字段
        for field, value in update_dict.items():
            setattr(job, field, value)

        await self.session.flush()

        # 记录审计日志
        await audit_logger.record_event(
            actor_id=actor_info.get("user_id") if actor_info else None,
            actor_email=actor_info.get("email") if actor_info else None,
            resource="parse_jobs",
            action="update",
            status="success",
            target=str(job.id),
            details=f"更新解析任务状态为: {job.status}",
            metadata={
                "knowledge_source_id": str(job.knowledge_source_id),
                "status": job.status,
                "progress": job.progress_percentage,
            },
            ip_address=actor_info.get("ip_address") if actor_info else None,
            session=self.session,
        )

        return job

    def _validate_status_transition(
        self,
        from_status: ParseStatus,
        to_status: ParseStatus,
    ) -> None:
        """验证任务状态转换是否合法。"""
        valid_transitions = {
            ParseStatus.PENDING: [ParseStatus.RUNNING, ParseStatus.CANCELLED, ParseStatus.FAILED],
            ParseStatus.RUNNING: [ParseStatus.COMPLETED, ParseStatus.FAILED, ParseStatus.CANCELLED],
            ParseStatus.COMPLETED: [],  # 终态
            ParseStatus.FAILED: [ParseStatus.PENDING],  # 可以重试
            ParseStatus.CANCELLED: [ParseStatus.PENDING],  # 可以重新启动
        }

        if to_status not in valid_transitions.get(from_status, []):
            raise InvalidJobTransitionError(
                f"无效的状态转换: {from_status} -> {to_status}"
            )

    async def get_source_stats(self, source_id: uuid.UUID) -> Dict[str, Any]:
        """获取知识源的统计信息。"""
        source = await self.get_source_by_id(source_id, include_jobs=True)
        if not source:
            raise SourceNotFoundError(f"知识源 {source_id} 不存在")

        jobs = source.parse_jobs
        total_jobs = len(jobs)
        completed_jobs = sum(1 for job in jobs if job.status == ParseStatus.COMPLETED)
        failed_jobs = sum(1 for job in jobs if job.status == ParseStatus.FAILED)
        running_jobs = sum(1 for job in jobs if job.status == ParseStatus.RUNNING)
        pending_jobs = sum(1 for job in jobs if job.status == ParseStatus.PENDING)

        last_job = jobs[0] if jobs else None
        last_sync = last_job.completed_at if last_job and last_job.status == ParseStatus.COMPLETED else None

        return {
            "source_id": source.id,
            "source_name": source.name,
            "source_type": source.source_type,
            "is_active": source.is_active,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": running_jobs,
            "pending_jobs": pending_jobs,
            "success_rate": completed_jobs / total_jobs if total_jobs > 0 else 0,
            "last_sync": last_sync,
            "last_sync_job_id": str(last_job.id) if last_job else None,
        }


def get_source_service(session: AsyncSession) -> SourceService:
    """获取知识源服务实例。"""
    return SourceService(session)
