"""知识源和解析任务的 Pydantic 模式。"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

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
    metadata: Optional[Dict[str, Any]] = Field(None, description="源元数据")
    is_active: bool = Field(True, description="是否激活")
    sync_frequency_minutes: Optional[int] = Field(None, ge=1, description="自动同步间隔（分钟）")


class KnowledgeSourceCreate(KnowledgeSourceBase):
    """创建知识源请求模式。"""
    pass


class KnowledgeSourceUpdate(BaseModel):
    """更新知识源请求模式。"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: Optional[SourceType] = None
    connection_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sync_frequency_minutes: Optional[int] = Field(None, ge=1)


class KnowledgeSourceResponse(KnowledgeSourceBase):
    """知识源响应模式。"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "生产环境数据库",
                "description": "生产环境 PostgreSQL 数据库 Schema",
                "source_type": "database",
                "connection_config": {
                    "host": "prod-db.internal",
                    "port": 5432,
                    "database": "cit_knowledge"
                },
                "metadata": {
                    "environment": "production",
                    "owner": "data-platform"
                },
                "is_active": True,
                "sync_frequency_minutes": 60,
                "last_synced_at": "2025-10-20T08:30:55Z",
                "created_at": "2025-10-20T07:12:10Z",
                "updated_at": "2025-10-20T08:30:55Z",
                "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c"
            }
        },
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
                        "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1
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
                "result_summary": {
                    "new_nodes": 64,
                    "relationships": 128
                },
                "job_config": {
                    "sync_mode": "incremental"
                },
                "created_at": "2025-10-20T08:30:59Z",
                "updated_at": "2025-10-20T08:31:45Z",
                "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c"
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
                        "created_by": "42f687f6-bc62-4e17-b284-1d3d5a2c9d3c"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1
            }
        }
    )


# GraphRAG 查询相关模式
class GraphRAGQueryRequest(BaseModel):
    """GraphRAG 查询请求模式。"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    source_ids: Optional[List[uuid.UUID]] = Field(None, description="限制查询的知识源ID列表")
    max_results: int = Field(10, ge=1, le=100, description="最大返回结果数")
    include_evidence: bool = Field(True, description="是否包含证据信息")
    timeout_seconds: int = Field(30, ge=5, le=300, description="查询超时时间（秒）")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "总结客户资料导入流程涉及的关键表和字段",
                "source_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "3d6f0a1c-49f1-4c61-86df-d2dfd52a9bfa"
                ],
                "max_results": 5,
                "include_evidence": True,
                "timeout_seconds": 30
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
                "section_title": "数据导入校验"
            }
        }
    )


class GraphRAGQueryResponse(BaseModel):
    """GraphRAG 查询响应模式。"""
    answer: str = Field(..., description="生成的答案")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="答案置信度")
    evidence_anchors: List[EvidenceAnchor] = Field(default_factory=list, description="证据锚点列表")
    sources_queried: List[uuid.UUID] = Field(..., description="实际查询的知识源ID列表")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    query_id: uuid.UUID = Field(..., description="查询ID")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "导入流程分为数据校验、暂存、入库三个阶段……",
                "confidence_score": 0.78,
                "evidence_anchors": [
                    {
                        "source_id": "550e8400-e29b-41d4-a716-446655440000",
                        "source_name": "客户数据库 · customer_orders 表",
                        "content_snippet": "导入流程会先校验客户编号是否存在于 customer_core 表……",
                        "relevance_score": 0.87,
                        "page_number": 12,
                        "section_title": "数据导入校验"
                    }
                ],
                "sources_queried": [
                    "550e8400-e29b-41d4-a716-446655440000"
                ],
                "processing_time_ms": 1432,
                "query_id": "f19bb9b1-30fe-4c3f-ae2e-25a6ca28f0e3"
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
                "processing_time_ms": 30050
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
    "GraphRAGQueryRequest",
    "GraphRAGQueryResponse",
    "GraphRAGErrorResponse",
    "EvidenceAnchor",
]
