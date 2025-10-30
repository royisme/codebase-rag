"""管理员相关API路由，包括知识源管理。"""

from __future__ import annotations

import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from database import async_session_factory
from database.models import ParseStatus
from services.source_service import get_source_service, SourceServiceError, SourceNotFoundError
from services.task_queue import submit_knowledge_source_sync_task
from services.code_indexing import validate_git_connection
from security.casbin_enforcer import require_permission
from schemas import (
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
    KnowledgeSourceResponse,
    KnowledgeSourceListResponse,
    KnowledgeSourceValidationRequest,
    KnowledgeSourceValidationResponse,
    ParseJobCreate,
    ParseJobResponse,
    ParseJobListResponse,
)
from loguru import logger

router = APIRouter(prefix="/api/v1/admin/sources", tags=["knowledge-sources"])


# Helper function to get actor info from request
def get_actor_info(user) -> Dict[str, Any]:
    """从请求中获取行动者信息。"""
    return {
        "user_id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "ip_address": getattr(user, "ip_address", None),
    }


@router.post(
    "/validate",
    response_model=KnowledgeSourceValidationResponse,
    summary="验证知识源连接",
    description="校验 Git 仓库凭据及可访问分支列表。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "验证结果返回"},
        400: {"description": "请求参数不合法"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def validate_knowledge_source_connection(
    payload: KnowledgeSourceValidationRequest,
    user=Depends(require_permission("/admin/sources/validate", "POST")),
):
    """验证代码仓库连接和凭据。"""

    try:
        valid, message, branches = await validate_git_connection(
            payload.repo_url,
            auth_type=payload.auth_type,
            access_token=payload.access_token,
            branch=payload.branch,
        )

        default_branch = payload.branch or (branches[0] if branches else None)

        return KnowledgeSourceValidationResponse(
            valid=valid,
            message=message,
            accessible_branches=branches or None,
            default_branch=default_branch,
        )
    except Exception as exc:  # pragma: no cover - validation failure path
        logger.error(f"仓库连接验证失败: {exc}")
        raise HTTPException(status_code=500, detail="仓库连接验证失败")


@router.post(
    "",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识源",
    description="创建新的知识源记录，并立即返回规范化响应结构。",
    response_model_exclude_none=True,
    responses={
        201: {"description": "知识源创建成功"},
        400: {"description": "请求参数不合法或知识源名称已存在"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def create_knowledge_source(
    source_data: KnowledgeSourceCreate,
    user=Depends(require_permission("/admin/sources", "POST")),
):
    """创建新的知识源。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            actor_info = get_actor_info(user)

            source = await source_service.create_source(
                source_data,
                created_by=actor_info.get("user_id"),
                actor_info=actor_info,
            )

            await session.commit()
            return KnowledgeSourceResponse.model_validate(source)

    except SourceServiceError as e:
        logger.error(f"创建知识源失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建知识源时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "",
    response_model=KnowledgeSourceListResponse,
    summary="分页获取知识源列表",
    description="支持分页、状态、类型与关键字搜索的知识源管理列表。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "成功返回知识源分页列表"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def list_knowledge_sources(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    source_type: Optional[str] = Query(None, description="按源类型过滤"),
    is_active: Optional[bool] = Query(None, description="按激活状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    created_by: Optional[uuid.UUID] = Query(None, description="按创建者过滤"),
    user=Depends(require_permission("/admin/sources", "GET")),
):
    """分页获取知识源列表。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            sources, total = await source_service.list_sources(
                page=page,
                size=size,
                source_type=source_type,
                is_active=is_active,
                search=search,
                created_by=created_by,
            )

            # 计算总页数
            pages = (total + size - 1) // size

            return KnowledgeSourceListResponse(
                items=[KnowledgeSourceResponse.model_validate(source) for source in sources],
                total=total,
                page=page,
                size=size,
                pages=pages,
            )

    except Exception as e:
        logger.error(f"获取知识源列表失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/{source_id}",
    response_model=KnowledgeSourceResponse,
    summary="获取单个知识源详情",
    description="根据知识源ID返回完整信息，包含最近一次同步信息。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "返回指定知识源详情"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def get_knowledge_source(
    source_id: uuid.UUID,
    user=Depends(require_permission("/admin/sources/*", "GET")),
):
    """获取指定知识源的详细信息。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            source = await source_service.get_source_by_id(source_id)
            if not source:
                raise HTTPException(status_code=404, detail="知识源不存在")

            return KnowledgeSourceResponse.model_validate(source)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识源详情失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.patch(
    "/{source_id}",
    response_model=KnowledgeSourceResponse,
    summary="更新知识源",
    description="支持更新名称、描述、配置、状态等字段，返回最新信息。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "更新成功并返回最新数据"},
        400: {"description": "请求参数不合法或知识源名称冲突"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def update_knowledge_source(
    source_id: uuid.UUID,
    update_data: KnowledgeSourceUpdate,
    user=Depends(require_permission("/admin/sources/*", "PATCH")),
):
    """更新知识源信息。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            actor_info = get_actor_info(user)

            source = await source_service.update_source(
                source_id,
                update_data,
                actor_info=actor_info,
            )

            await session.commit()
            return KnowledgeSourceResponse.model_validate(source)

    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="知识源不存在")
    except SourceServiceError as e:
        logger.error(f"更新知识源失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新知识源时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除知识源",
    description="将知识源标记为非活跃状态，并记录审计日志。",
    responses={
        204: {"description": "删除成功，无返回体"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def delete_knowledge_source(
    source_id: uuid.UUID,
    user=Depends(require_permission("/admin/sources/*", "DELETE")),
):
    """软删除知识源（设置为非活跃）。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            actor_info = get_actor_info(user)

            await source_service.delete_source(
                source_id,
                actor_info=actor_info,
            )

            await session.commit()

    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="知识源不存在")
    except Exception as e:
        logger.error(f"删除知识源失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/{source_id}/stats",
    summary="获取知识源统计信息",
    description="返回指定知识源的同步情况、任务统计等信息。",
    responses={
        200: {"description": "返回知识源统计信息"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def get_source_statistics(
    source_id: uuid.UUID,
    user=Depends(require_permission("/admin/sources/*", "GET")),
):
    """获取知识源的统计信息。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            stats = await source_service.get_source_stats(source_id)
            return stats

    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="知识源不存在")
    except Exception as e:
        logger.error(f"获取知识源统计失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# Parse Job endpoints
@router.post(
    "/{source_id}/jobs",
    response_model=ParseJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="为知识源创建解析任务",
    description="创建解析任务并提交同步队列，返回任务详情。",
    response_model_exclude_none=True,
    responses={
        201: {"description": "解析任务创建成功"},
        400: {"description": "请求参数不合法或存在冲突任务"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def create_parse_job(
    source_id: uuid.UUID,
    job_data: ParseJobCreate,
    user=Depends(require_permission("/admin/sources/*", "POST")),
):
    """为知识源创建解析任务。"""
    try:
        # 确保任务的知识源ID与URL参数一致
        job_data.knowledge_source_id = source_id

        async with async_session_factory() as session:
            source_service = get_source_service(session)
            actor_info = get_actor_info(user)

            # 验证知识源存在
            source = await source_service.get_source_by_id(source_id)
            if not source:
                raise HTTPException(status_code=404, detail="知识源不存在")

            # 创建解析任务
            job = await source_service.create_parse_job(
                job_data,
                created_by=actor_info.get("user_id"),
                actor_info=actor_info,
            )

            await session.commit()

            # 提交同步任务到任务队列
            try:
                task_id = await submit_knowledge_source_sync_task(
                    source_id=str(source_id),
                    job_id=str(job.id),
                    sync_config=job_data.job_config or {},
                )
                logger.info(f"已提交知识源同步任务: {task_id}")
            except Exception as task_error:
                logger.error(f"提交同步任务失败: {task_error}")
                # 不影响API响应，只记录日志

            return ParseJobResponse.model_validate(job)

    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="知识源不存在")
    except SourceServiceError as e:
        logger.error(f"创建解析任务失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建解析任务时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/{source_id}/jobs",
    response_model=ParseJobListResponse,
    summary="列出知识源解析任务",
    description="分页返回指定知识源的解析任务列表，支持状态与创建者过滤。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "返回解析任务分页列表"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def list_parse_jobs(
    source_id: uuid.UUID,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[ParseStatus] = Query(None, description="按状态过滤"),
    created_by: Optional[uuid.UUID] = Query(None, description="按创建者过滤"),
    user=Depends(require_permission("/admin/sources/*", "GET")),
):
    """获取知识源的解析任务列表。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            # 验证知识源存在
            source = await source_service.get_source_by_id(source_id)
            if not source:
                raise HTTPException(status_code=404, detail="知识源不存在")

            jobs, total = await source_service.list_jobs(
                page=page,
                size=size,
                source_id=source_id,
                status=status,
                created_by=created_by,
            )

            # 计算总页数
            pages = (total + size - 1) // size

            return ParseJobListResponse(
                items=[ParseJobResponse.model_validate(job) for job in jobs],
                total=total,
                page=page,
                size=size,
                pages=pages,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取解析任务列表失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/jobs/{job_id}",
    response_model=ParseJobResponse,
    summary="获取解析任务详情",
    description="根据任务ID返回解析任务的完整状态、进度与结果信息。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "返回解析任务详情"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "解析任务不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def get_parse_job(
    job_id: uuid.UUID,
    user=Depends(require_permission("/admin/sources/*", "GET")),
):
    """获取解析任务的详细信息。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            job = await source_service.get_job_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="解析任务不存在")

            return ParseJobResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取解析任务详情失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post(
    "/{source_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发知识源同步",
    description="创建新的解析任务并提交到后台同步队列。",
    responses={
        202: {"description": "同步任务提交成功"},
        400: {"description": "知识源未激活或请求参数不合法"},
        403: {"description": "RBAC：权限不足"},
        404: {"description": "知识源不存在"},
        500: {"description": "内部服务器错误"},
    },
)
async def sync_knowledge_source(
    source_id: uuid.UUID,
    sync_config: Optional[Dict[str, Any]] = None,
    user=Depends(require_permission("/admin/sources/*", "POST")),
):
    """手动触发知识源同步。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            actor_info = get_actor_info(user)

            # 验证知识源存在且激活
            source = await source_service.get_source_by_id(source_id)
            if not source:
                raise HTTPException(status_code=404, detail="知识源不存在")

            if not source.is_active:
                raise HTTPException(status_code=400, detail="知识源未激活，无法同步")

            # 创建解析任务
            job_data = ParseJobCreate(
                knowledge_source_id=source_id,
                job_config=sync_config or {},
            )

            job = await source_service.create_parse_job(
                job_data,
                created_by=actor_info.get("user_id"),
                actor_info=actor_info,
            )

            await session.commit()

            # 提交同步任务
            task_id = await submit_knowledge_source_sync_task(
                source_id=str(source_id),
                job_id=str(job.id),
                sync_config=sync_config or {},
            )

            return {
                "message": "知识源同步任务已提交",
                "source_id": str(source_id),
                "source_name": source.name,
                "job_id": str(job.id),
                "task_id": task_id,
                "status": "submitted",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发知识源同步失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
