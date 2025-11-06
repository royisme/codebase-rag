"""知识源和解析任务的 Pydantic 模式。"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class SourceType(str, Enum):
    """知识源类型枚举。"""

    DOCUMENT = "document"
    DATABASE = "database"
    API = "api"
    WEBSITE = "website"
    CODE = "code"
    OTHER = "other"


class ParseStatus(str, Enum):
    """解析任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# KnowledgeSource 相关模式
class KnowledgeSourceBase(BaseModel):
    """知识源基础模式。"""

    name: str = Field(..., min_length=1, max_length=255, description="知识源名称")
    description: Optional[str] = Field(None, description="知识源描述")
    source_type: SourceType = Field(SourceType.OTHER, description="知识源类型")
    connection_config: Optional[Dict[str, Any]] = Field(None, description="连接配置")
    source_metadata: Optional[Dict[str, Any]] = Field(None, description="源元数据")
    is_active: bool = Field(True, description="是否激活")
    sync_frequency_minutes: Optional[int] = Field(
        None, ge=1, description="自动同步间隔（分钟）"
    )


class KnowledgeSourceCreate(KnowledgeSourceBase):
    """创建知识源请求模式。"""

    pass


class KnowledgeSourceUpdate(BaseModel):
    """更新知识源请求模式。"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: Optional[SourceType] = None
    connection_config: Optional[Dict[str, Any]] = None
    source_metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sync_frequency_minutes: Optional[int] = Field(None, ge=1)


class KnowledgeSourceResponse(KnowledgeSourceBase):
    """知识源响应模式。"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "生产环境数据库",
                "description": "生产环境 PostgreSQL 数据库 Schema",
                "source_type": "database",
                "connection_config": {
                    "host": "prod-db.internal",
                    "port": 5432,
                    "database": "cit_knowledge",
                },
                "source_metadata": {"environment": "production", "owner": "data-platform"},
                "is_active": True,
                "sync_frequency_minutes": 60,
                "last_synced_at": "2025-10-20T08:30:55Z",
                "created_at": "2025-10-20T07:12:10Z",
                "updated_at": "2025-10-20T08:30:55Z",
                "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c",
            }
        },
    )

    source_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="源元数据",
    )
    id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime
    last_synced_at: Optional[dt.datetime] = None
    created_by: Optional[uuid.UUID] = None


class KnowledgeSourceListResponse(BaseModel):
    """知识源列表响应模式。"""

    items: List[KnowledgeSourceResponse]
    total: int
    page: int
    size: int
    pages: int
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "生产环境数据库",
                        "description": "生产环境 PostgreSQL 数据库 Schema",
                        "source_type": "database",
                        "is_active": True,
                        "sync_frequency_minutes": 60,
                        "last_synced_at": "2025-10-20T08:30:55Z",
                        "created_at": "2025-10-20T07:12:10Z",
                        "updated_at": "2025-10-20T08:30:55Z",
                        "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c",
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1,
            }
        }
    )


# ParseJob 相关模式
class ParseJobBase(BaseModel):
    """解析任务基础模式。"""

    job_config: Optional[Dict[str, Any]] = Field(None, description="任务特定配置")


class ParseJobCreate(ParseJobBase):
    """创建解析任务请求模式。"""

    knowledge_source_id: uuid.UUID = Field(..., description="知识源ID")


class ParseJobUpdate(BaseModel):
    """更新解析任务请求模式。"""

    status: Optional[ParseStatus] = None
    error_message: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    items_processed: Optional[int] = Field(None, ge=0)
    total_items: Optional[int] = Field(None, ge=1)
    result_summary: Optional[Dict[str, Any]] = None


class ParseJobResponse(ParseJobBase):
    """解析任务响应模式。"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e1b4c136-b7ca-4f78-8ed3-927076e0af5d",
                "knowledge_source_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "started_at": "2025-10-20T08:31:00Z",
                "completed_at": None,
                "error_message": None,
                "progress_percentage": 45,
                "items_processed": 1200,
                "total_items": 2500,
                "result_summary": {"new_nodes": 64, "relationships": 128},
                "job_config": {"sync_mode": "incremental"},
                "created_at": "2025-10-20T08:30:59Z",
                "updated_at": "2025-10-20T08:31:45Z",
                "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c",
            }
        },
    )

    id: uuid.UUID
    knowledge_source_id: uuid.UUID
    status: ParseStatus
    started_at: Optional[dt.datetime] = None
    completed_at: Optional[dt.datetime] = None
    error_message: Optional[str] = None
    progress_percentage: int
    items_processed: int
    total_items: Optional[int] = None
    result_summary: Optional[Dict[str, Any]] = None
    created_at: dt.datetime
    updated_at: dt.datetime
    created_by: Optional[uuid.UUID] = None


class ParseJobListResponse(BaseModel):
    """解析任务列表响应模式。"""

    items: List[ParseJobResponse]
    total: int
    page: int
    size: int
    pages: int


class KnowledgeSourceValidationRequest(BaseModel):
    """知识源连接验证请求。"""

    repo_url: str = Field(..., description="Git 仓库地址")
    auth_type: Literal["token", "none"] = Field("none", description="认证方式")
    access_token: Optional[str] = Field(None, description="访问令牌（按需提供）")
    branch: Optional[str] = Field(None, description="待验证的分支名称")


class KnowledgeSourceValidationResponse(BaseModel):
    """知识源连接验证响应。"""

    valid: bool = Field(..., description="是否验证成功")
    message: Optional[str] = Field(None, description="验证结果说明")
    accessible_branches: Optional[List[str]] = Field(
        None, description="可访问的分支列表"
    )
    default_branch: Optional[str] = Field(None, description="推断的默认分支名称")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "e1b4c136-b7ca-4f78-8ed3-927076e0af5d",
                        "knowledge_source_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "running",
                        "progress_percentage": 45,
                        "items_processed": 1200,
                        "total_items": 2500,
                        "created_at": "2025-10-20T08:30:59Z",
                        "updated_at": "2025-10-20T08:31:45Z",
                        "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c",
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1,
            }
        }
    )


# GraphRAG 查询相关模式
class GraphRelatedEntity(BaseModel):
    """关联实体信息。"""

    type: str = Field(..., description="实体类型，例如 file、commit、module、person")
    name: str = Field(..., description="实体名称或路径")
    importance: Literal["high", "medium", "low"] = Field(
        "medium", description="重要程度"
    )
    detail: Optional[str] = Field(None, description="实体的描述或补充信息")
    link: Optional[str] = Field(None, description="可选的跳转链接")
    extra: Optional[Dict[str, Any]] = Field(None, description="附加字段")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "file",
                "name": "backend/services/graph_rag_service.py",
                "importance": "high",
                "detail": "最近 2 次提交涉及此文件",
                "link": "https://git.example.com/blob/commit",
            }
        }
    )


class GraphEvidenceItem(BaseModel):
    """证据片段。"""

    id: Optional[str] = Field(None, description="证据 ID")
    snippet: str = Field(..., description="证据文本片段")
    source_type: Optional[str] = Field(
        None, description="证据来源类型，如 commit/file/doc"
    )
    source_ref: Optional[str] = Field(
        None, description="引用标识，如提交哈希或文件路径"
    )
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="相关性评分")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "commit:f19bb9b1",
                "snippet": "Refactor GraphRAG service to expose structured response.",
                "source_type": "commit",
                "source_ref": "f19bb9b1-30fe-4c3f-ae2e-25a6ca28f0e3",
                "score": 0.82,
            }
        }
    )


class GraphRAGAnswerPayload(BaseModel):
    """GraphRAG 查询回答主体。"""

    summary: str = Field(..., description="面向用户的总体回答")
    related_entities: List[GraphRelatedEntity] = Field(
        default_factory=list, description="关联实体列表"
    )
    evidence: List[GraphEvidenceItem] = Field(
        default_factory=list, description="证据片段列表"
    )
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "登录流程最近在 2025-10-23 的提交中进行了错误处理优化。",
                "related_entities": [
                    {
                        "type": "file",
                        "name": "backend/services/auth_service.py",
                        "importance": "high",
                        "detail": "提交 98c1 修改了异常处理逻辑",
                    }
                ],
                "evidence": [
                    {
                        "id": "commit:98c1",
                        "snippet": "Improve login error handling by surfacing audit entries.",
                        "source_type": "commit",
                        "source_ref": "98c1f3d",
                    }
                ],
                "next_actions": [
                    "查看这些文件最近的提交详情。",
                    "联系相关负责人确认变更计划。",
                ],
            }
        }
    )


class GraphRAGQueryRequest(BaseModel):
    """GraphRAG 查询请求模式。"""

    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    source_ids: Optional[List[uuid.UUID]] = Field(
        None, description="限制查询的知识源ID列表"
    )
    max_results: int = Field(10, ge=1, le=100, description="最大返回结果数")
    include_evidence: bool = Field(True, description="是否包含证据信息")
    timeout_seconds: int = Field(30, ge=5, le=300, description="查询超时时间（秒）")
    context_query_id: Optional[uuid.UUID] = Field(
        None,
        description="上一轮查询的 query_id，命中缓存时用于多轮上下文",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "总结客户资料导入流程涉及的关键表和字段",
                "source_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "3d6f0a1c-49f1-4c61-86df-d2dfd52a9bfa",
                ],
                "max_results": 5,
                "include_evidence": True,
                "timeout_seconds": 30,
                "context_query_id": "ab2f89c3-7f02-4f39-a815-0123456789ab",
            }
        }
    )


class StreamQueryRequest(BaseModel):
    """流式查询请求模式（兼容前端 SSE 协议）。"""

    question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    source_ids: Optional[List[str]] = Field(
        None, description="知识源 ID 列表，未指定时默认查询所有可用知识源"
    )
    retrieval_mode: Optional[str] = Field(
        "hybrid", description="检索模式: graph/vector/hybrid"
    )
    top_k: Optional[int] = Field(8, ge=1, le=100, description="返回结果数量")
    timeout: Optional[int] = Field(120, ge=10, le=600, description="超时时间（秒）")
    session_id: Optional[str] = Field(None, description="会话 ID，用于多轮对话")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "如何实现用户认证？",
                "source_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "retrieval_mode": "hybrid",
                "top_k": 8,
                "timeout": 120,
                "session_id": "session-123",
            }
        }
    )


class EvidenceAnchor(BaseModel):
    """证据锚点模式。"""

    source_id: uuid.UUID
    source_name: str
    content_snippet: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "source_name": "客户数据库 · customer_orders 表",
                "content_snippet": "导入流程会先校验客户编号是否存在于 customer_core 表……",
                "relevance_score": 0.87,
                "page_number": 12,
                "section_title": "数据导入校验",
            }
        }
    )


class GraphRAGQueryResponse(BaseModel):
    """GraphRAG 查询响应模式。"""

    answer: GraphRAGAnswerPayload = Field(..., description="结构化回答")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="答案置信度")
    evidence_anchors: List[EvidenceAnchor] = Field(
        default_factory=list, description="原始证据锚点列表"
    )
    raw_messages: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="LLM 或检索返回的原始消息"
    )
    sources_queried: List[str] = Field(
        default_factory=list, description="实际查询的知识源标识列表"
    )
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    query_id: Optional[uuid.UUID] = Field(None, description="查询ID")
    issues: List[str] = Field(
        default_factory=list, description="上下文构建中的警告信息"
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": {
                    "summary": "导入流程最近的改动集中在 `backend/services/importer.py`，提交 f19bb9b1 调整了错误处理。",
                    "related_entities": [
                        {
                            "type": "file",
                            "name": "backend/services/importer.py",
                            "importance": "high",
                            "detail": "在提交 f19bb9b1 中更新",
                        },
                        {
                            "type": "commit",
                            "name": "f19bb9b1",
                            "importance": "high",
                            "detail": "Refactor importer error handling",
                        },
                    ],
                    "evidence": [
                        {
                            "id": "commit:f19bb9b1",
                            "snippet": "Refactor importer error handling to capture audit entries.",
                            "source_type": "commit",
                            "source_ref": "f19bb9b1",
                        }
                    ],
                    "next_actions": [
                        "查看这些文件最近的提交详情。",
                        "联系相关负责人确认变更计划。",
                    ],
                },
                "confidence_score": 0.78,
                "sources_queried": ["550e8400-e29b-41d4-a716-446655440000"],
                "processing_time_ms": 1432,
                "query_id": "f19bb9b1-30fe-4c3f-ae2e-25a6ca28f0e3",
                "issues": [],
            }
        }
    )


class StreamTextDeltaEvent(BaseModel):
    """流式文本增量事件（Token级别）。"""
    
    type: Literal["text_delta"] = "text_delta"
    content: str = Field(..., description="文本增量片段")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "text_delta",
                "content": "登录流程",
            }
        }
    )


class StreamStatusEvent(BaseModel):
    """流式状态事件。"""
    
    type: Literal["status"] = "status"
    stage: str = Field(..., description="当前阶段，如 'context'/'llm'/'finalizing'")
    message: str = Field(..., description="状态描述")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "status",
                "stage": "llm",
                "message": "正在生成回答…",
            }
        }
    )


class StreamEntityEvent(BaseModel):
    """流式实体事件。"""
    
    type: Literal["entity"] = "entity"
    entity: GraphRelatedEntity = Field(..., description="关联实体")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "entity",
                "entity": {
                    "type": "file",
                    "name": "backend/services/auth.py",
                    "importance": "high",
                },
            }
        }
    )


class StreamMetadataEvent(BaseModel):
    """流式元数据事件。"""
    
    type: Literal["metadata"] = "metadata"
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    execution_time_ms: Optional[int] = None
    sources_queried: List[str] = Field(default_factory=list)
    retrieval_mode: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "metadata",
                "confidence_score": 0.85,
                "execution_time_ms": 1234,
                "sources_queried": ["repo-1"],
                "retrieval_mode": "hybrid",
            }
        }
    )


class StreamDoneEvent(BaseModel):
    """流式完成事件。"""
    
    type: Literal["done"] = "done"
    query_id: str = Field(..., description="查询ID")
    timestamp: str = Field(..., description="完成时间戳")
    summary: Optional[str] = Field(None, description="完整摘要（供缓存）")
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    sources_queried: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "done",
                "query_id": "f19bb9b1-30fe-4c3f-ae2e-25a6ca28f0e3",
                "timestamp": "2025-10-20T08:31:45Z",
                "summary": "登录流程最近在提交 98c1 中优化。",
                "next_actions": ["查看提交详情"],
                "confidence_score": 0.85,
                "sources_queried": ["repo-1"],
                "processing_time_ms": 1234,
            }
        }
    )


class StreamErrorEvent(BaseModel):
    """流式错误事件。"""
    
    type: Literal["error"] = "error"
    message: str = Field(..., description="错误信息")
    code: Optional[str] = Field(None, description="错误代码")
    processing_time_ms: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "error",
                "message": "查询超时",
                "code": "TIMEOUT",
                "processing_time_ms": 30000,
            }
        }
    )


class GraphRAGErrorResponse(BaseModel):
    """GraphRAG 错误响应模式。"""

    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    query_id: Optional[uuid.UUID] = None
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "TIMEOUT",
                "error_message": "查询超时，请尝试简化查询或增加超时时间",
                "query_id": "f19bb9b1-30fe-4c3f-ae2e-25a6ca28f0e3",
                "processing_time_ms": 30050,
            }
        }
    )


__all__ = [
    # SourceType and ParseStatus
    "SourceType",
    "ParseStatus",
    # KnowledgeSource schemas
    "KnowledgeSourceBase",
    "KnowledgeSourceCreate",
    "KnowledgeSourceUpdate",
    "KnowledgeSourceResponse",
    "KnowledgeSourceListResponse",
    # ParseJob schemas
    "ParseJobBase",
    "ParseJobCreate",
    "ParseJobUpdate",
    "ParseJobResponse",
    "ParseJobListResponse",
    # GraphRAG schemas
    "GraphRelatedEntity",
    "GraphEvidenceItem",
    "GraphRAGAnswerPayload",
    "GraphRAGQueryRequest",
    "GraphRAGQueryResponse",
    "GraphRAGErrorResponse",
    "EvidenceAnchor",
    "StreamQueryRequest",
    # Streaming event schemas
    "StreamTextDeltaEvent",
    "StreamStatusEvent",
    "StreamEntityEvent",
    "StreamMetadataEvent",
    "StreamDoneEvent",
    "StreamErrorEvent",
]
