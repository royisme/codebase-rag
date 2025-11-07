"""
Prometheus metrics service for monitoring and observability
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from typing import Dict, Any
import time
from functools import wraps
from loguru import logger
from codebase_rag.config import settings

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# =================================
# Request metrics
# =================================

# HTTP request counter
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

# HTTP request duration histogram
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

# =================================
# Code ingestion metrics
# =================================

# Repository ingestion counter
repo_ingestion_total = Counter(
    'repo_ingestion_total',
    'Total repository ingestions',
    ['status', 'mode'],  # status: success/error, mode: full/incremental
    registry=registry
)

# Files ingested counter
files_ingested_total = Counter(
    'files_ingested_total',
    'Total files ingested',
    ['language', 'repo_id'],
    registry=registry
)

# Ingestion duration histogram
ingestion_duration_seconds = Histogram(
    'ingestion_duration_seconds',
    'Repository ingestion duration in seconds',
    ['mode'],  # full/incremental
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)

# =================================
# Graph operations metrics
# =================================

# Graph query counter
graph_queries_total = Counter(
    'graph_queries_total',
    'Total graph queries',
    ['operation', 'status'],  # operation: related/impact/search, status: success/error
    registry=registry
)

# Graph query duration histogram
graph_query_duration_seconds = Histogram(
    'graph_query_duration_seconds',
    'Graph query duration in seconds',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

# =================================
# Neo4j metrics
# =================================

# Neo4j connection status
neo4j_connected = Gauge(
    'neo4j_connected',
    'Neo4j connection status (1=connected, 0=disconnected)',
    registry=registry
)

# Neo4j nodes count
neo4j_nodes_total = Gauge(
    'neo4j_nodes_total',
    'Total number of nodes in Neo4j',
    ['label'],  # File, Symbol, Repo
    registry=registry
)

# Neo4j relationships count
neo4j_relationships_total = Gauge(
    'neo4j_relationships_total',
    'Total number of relationships in Neo4j',
    ['type'],  # CALLS, IMPORTS, DEFINED_IN, etc.
    registry=registry
)

# =================================
# Context pack metrics
# =================================

# Context pack generation counter
context_pack_total = Counter(
    'context_pack_total',
    'Total context packs generated',
    ['stage', 'status'],  # stage: plan/review/implement, status: success/error
    registry=registry
)

# Context pack budget usage
context_pack_budget_used = Histogram(
    'context_pack_budget_used',
    'Token budget used in context packs',
    ['stage'],
    buckets=[100, 500, 1000, 1500, 2000, 3000, 5000],
    registry=registry
)

# =================================
# Task queue metrics
# =================================

# Task queue size
task_queue_size = Gauge(
    'task_queue_size',
    'Number of tasks in queue',
    ['status'],  # pending, running, completed, failed
    registry=registry
)

# Task processing duration
task_processing_duration_seconds = Histogram(
    'task_processing_duration_seconds',
    'Task processing duration in seconds',
    ['task_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)


class MetricsService:
    """Service for managing Prometheus metrics"""

    def __init__(self):
        self.registry = registry
        logger.info("Metrics service initialized")

    def get_metrics(self) -> bytes:
        """
        Generate Prometheus metrics in text format

        Returns:
            bytes: Metrics in Prometheus text format
        """
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """
        Get content type for metrics endpoint

        Returns:
            str: Content type string
        """
        return CONTENT_TYPE_LATEST

    @staticmethod
    def track_http_request(method: str, endpoint: str, status: int):
        """Track HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()

    @staticmethod
    def track_http_duration(method: str, endpoint: str, duration: float):
        """Track HTTP request duration"""
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    @staticmethod
    def track_repo_ingestion(status: str, mode: str):
        """Track repository ingestion"""
        repo_ingestion_total.labels(status=status, mode=mode).inc()

    @staticmethod
    def track_file_ingested(language: str, repo_id: str):
        """Track file ingestion"""
        files_ingested_total.labels(language=language, repo_id=repo_id).inc()

    @staticmethod
    def track_ingestion_duration(mode: str, duration: float):
        """Track ingestion duration"""
        ingestion_duration_seconds.labels(mode=mode).observe(duration)

    @staticmethod
    def track_graph_query(operation: str, status: str):
        """Track graph query"""
        graph_queries_total.labels(operation=operation, status=status).inc()

    @staticmethod
    def track_graph_duration(operation: str, duration: float):
        """Track graph query duration"""
        graph_query_duration_seconds.labels(operation=operation).observe(duration)

    @staticmethod
    def update_neo4j_status(connected: bool):
        """Update Neo4j connection status"""
        neo4j_connected.set(1 if connected else 0)

    @staticmethod
    def update_neo4j_nodes(label: str, count: int):
        """Update Neo4j node count"""
        neo4j_nodes_total.labels(label=label).set(count)

    @staticmethod
    def update_neo4j_relationships(rel_type: str, count: int):
        """Update Neo4j relationship count"""
        neo4j_relationships_total.labels(type=rel_type).set(count)

    @staticmethod
    def track_context_pack(stage: str, status: str, budget_used: int):
        """Track context pack generation"""
        context_pack_total.labels(stage=stage, status=status).inc()
        context_pack_budget_used.labels(stage=stage).observe(budget_used)

    @staticmethod
    def update_task_queue_size(status: str, size: int):
        """Update task queue size"""
        task_queue_size.labels(status=status).set(size)

    @staticmethod
    def track_task_duration(task_type: str, duration: float):
        """Track task processing duration"""
        task_processing_duration_seconds.labels(task_type=task_type).observe(duration)

    async def update_neo4j_metrics(self, graph_service):
        """
        Update Neo4j metrics by querying the graph database

        Args:
            graph_service: The Neo4j graph service instance
        """
        try:
            # Update connection status
            is_connected = getattr(graph_service, '_connected', False)
            self.update_neo4j_status(is_connected)

            if not is_connected:
                return

            # Get node counts
            with graph_service.driver.session(database=settings.neo4j_database) as session:
                # Count File nodes
                result = session.run("MATCH (n:File) RETURN count(n) as count")
                file_count = result.single()["count"]
                self.update_neo4j_nodes("File", file_count)

                # Count Symbol nodes
                result = session.run("MATCH (n:Symbol) RETURN count(n) as count")
                symbol_count = result.single()["count"]
                self.update_neo4j_nodes("Symbol", symbol_count)

                # Count Repo nodes
                result = session.run("MATCH (n:Repo) RETURN count(n) as count")
                repo_count = result.single()["count"]
                self.update_neo4j_nodes("Repo", repo_count)

                # Count relationships by type
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as rel_type, count(r) as count
                """)
                for record in result:
                    self.update_neo4j_relationships(record["rel_type"], record["count"])

        except Exception as e:
            logger.error(f"Failed to update Neo4j metrics: {e}")
            self.update_neo4j_status(False)


# Create singleton instance
metrics_service = MetricsService()


def track_duration(operation: str, metric_type: str = "graph"):
    """
    Decorator to track operation duration

    Args:
        operation: Operation name
        metric_type: Type of metric (graph, ingestion, task)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                if metric_type == "graph":
                    metrics_service.track_graph_duration(operation, duration)
                elif metric_type == "ingestion":
                    metrics_service.track_ingestion_duration(operation, duration)
                elif metric_type == "task":
                    metrics_service.track_task_duration(operation, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time

                if metric_type == "graph":
                    metrics_service.track_graph_duration(operation, duration)

                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                if metric_type == "graph":
                    metrics_service.track_graph_duration(operation, duration)
                elif metric_type == "ingestion":
                    metrics_service.track_ingestion_duration(operation, duration)
                elif metric_type == "task":
                    metrics_service.track_task_duration(operation, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time

                if metric_type == "graph":
                    metrics_service.track_graph_duration(operation, duration)

                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
