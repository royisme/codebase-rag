#!/usr/bin/env python3
"""
Code Graph Knowledge Service 启动脚本
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import settings, validate_milvus_connection, validate_neo4j_connection, validate_ollama_connection
from loguru import logger

def check_dependencies():
    """检查服务依赖"""
    logger.info("检查服务依赖...")
    
    checks = [
        ("Milvus", validate_milvus_connection),
        ("Neo4j", validate_neo4j_connection),
        ("Ollama", validate_ollama_connection)
    ]
    
    all_passed = True
    for service_name, check_func in checks:
        try:
            if check_func():
                logger.info(f"✓ {service_name} 连接成功")
            else:
                logger.error(f"✗ {service_name} 连接失败")
                all_passed = False
        except Exception as e:
            logger.error(f"✗ {service_name} 检查出错: {e}")
            all_passed = False
    
    return all_passed

def wait_for_services(max_retries=30, retry_interval=2):
    """等待服务启动"""
    logger.info("等待服务启动...")
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"尝试 {attempt}/{max_retries}...")
        
        if check_dependencies():
            logger.info("所有服务已就绪!")
            return True
        
        if attempt < max_retries:
            logger.info(f"等待 {retry_interval} 秒后重试...")
            time.sleep(retry_interval)
    
    logger.error("服务启动超时!")
    return False

def print_startup_info():
    """打印启动信息"""
    print("\n" + "="*60)
    print("🚀 Code Graph Knowledge Service")
    print("="*60)
    print(f"版本: {settings.app_version}")
    print(f"主机: {settings.host}:{settings.port}")
    print(f"调试模式: {settings.debug}")
    print()
    print("📊 服务配置:")
    print(f"  Milvus: {settings.milvus_host}:{settings.milvus_port}")
    print(f"  Neo4j: {settings.neo4j_uri}")
    print(f"  Ollama: {settings.ollama_base_url}")
    print()
    print("🤖 模型配置:")
    print(f"  LLM: {settings.ollama_model}")
    print(f"  Embedding: {settings.embedding_model}")
    print("="*60)
    print()

def main():
    """主函数"""
    print_startup_info()
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        logger.error("需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查环境变量
    logger.info("检查环境配置...")
    
    # 可选：等待服务启动（在开发环境中很有用）
    if not settings.debug or input("是否跳过服务依赖检查? (y/N): ").lower().startswith('y'):
        logger.info("跳过服务依赖检查")
    else:
        if not wait_for_services():
            logger.error("服务依赖检查失败，继续启动可能会遇到问题")
            if not input("是否继续启动? (y/N): ").lower().startswith('y'):
                sys.exit(1)
    
    # 启动应用
    logger.info("启动 FastAPI 应用...")
    
    try:
        from main import start_server
        start_server()
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 