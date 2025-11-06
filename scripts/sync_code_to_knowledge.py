"""
将代码图谱的内容同步到知识索引

这个脚本从 Neo4j 的代码图谱（File, Function, Class 节点）中提取信息，
转换为 Document 节点并插入到知识索引中，供 GraphRAG 查询使用。
"""
import asyncio
from loguru import logger
from llama_index.core import Document
from services.neo4j_knowledge_service import neo4j_knowledge_service
from services.graph_service import graph_service


async def sync_code_to_knowledge():
    """将代码图谱的内容同步到知识索引"""
    
    logger.info("开始同步代码图谱到知识索引...")
    
    # 1. 初始化服务
    await neo4j_knowledge_service.initialize()
    
    if not neo4j_knowledge_service.knowledge_index:
        logger.error("知识索引未初始化")
        return
    
    # 2. 从代码图谱获取所有文件及其内容
    query = """
    MATCH (f:File)
    OPTIONAL MATCH (f)<-[:DEFINES]-(func:Function)
    OPTIONAL MATCH (f)<-[:DEFINES]-(cls:Class)
    OPTIONAL MATCH (f)-[:IMPORTS]->(imported:File)
    OPTIONAL MATCH (f)<-[:CHANGED_FILE]-(c:Commit)
    OPTIONAL MATCH (c)-[:AUTHORED_BY]->(p:Person)
    RETURN 
        f.path as path,
        f.description as description,
        f.language as language,
        f.content as content,
        collect(DISTINCT func.name) as functions,
        collect(DISTINCT cls.name) as classes,
        collect(DISTINCT imported.path)[0..5] as imports,
        collect(DISTINCT {
            message: c.message,
            author: p.name,
            date: c.timestamp
        })[0..3] as recent_commits
    """
    
    result = await graph_service.execute_cypher(query, {})
    
    if not result.raw_result:
        logger.warning("代码图谱中没有文件节点")
        logger.info("提示：请先导入代码库到代码图谱")
        return
    
    # 3. 为每个文件创建文档
    documents = []
    for record in result.raw_result:
        path = record['path']
        description = record.get('description', '')
        language = record.get('language', 'unknown')
        content = record.get('content', '')
        functions = [f for f in record.get('functions', []) if f]
        classes = [c for c in record.get('classes', []) if c]
        imports = [i for i in record.get('imports', []) if i]
        commits = [c for c in record.get('recent_commits', []) if c.get('message')]
        
        # 构建文档内容
        content_parts = [f"# 文件: {path}"]
        
        if description:
            content_parts.append(f"\n描述: {description}")
        
        content_parts.append(f"\n编程语言: {language}")
        
        if functions:
            content_parts.append(f"\n## 函数列表")
            for func in functions[:15]:  # 最多列出15个函数
                content_parts.append(f"- {func}")
        
        if classes:
            content_parts.append(f"\n## 类列表")
            for cls in classes[:10]:  # 最多列出10个类
                content_parts.append(f"- {cls}")
        
        if imports:
            content_parts.append(f"\n## 依赖文件")
            for imp in imports:
                content_parts.append(f"- {imp}")
        
        if commits:
            content_parts.append(f"\n## 最近修改")
            for commit in commits:
                msg = commit.get('message', '').split('\n')[0][:100]  # 取第一行
                author = commit.get('author', 'Unknown')
                content_parts.append(f"- {msg} (作者: {author})")
        
        # 如果有文件内容，添加摘要
        if content and len(content) > 100:
            content_parts.append(f"\n## 代码摘要")
            content_parts.append(content[:500])  # 前500字符
        
        doc_text = "\n".join(content_parts)
        
        doc = Document(
            text=doc_text,
            metadata={
                'source_type': 'code_file',
                'file_path': path,
                'language': language,
                'function_count': len(functions),
                'class_count': len(classes),
            }
        )
        documents.append(doc)
    
    logger.info(f"准备同步 {len(documents)} 个文件到知识索引")
    
    # 4. 插入到知识索引
    try:
        for i, doc in enumerate(documents):
            neo4j_knowledge_service.knowledge_index.insert(doc)
            if (i + 1) % 10 == 0:
                logger.debug(f"已同步 {i + 1}/{len(documents)} 个文档")
        
        logger.success(f"✅ 成功同步 {len(documents)} 个文档到知识索引")
    except Exception as e:
        logger.error(f"同步失败: {e}")
        raise
    
    # 5. 验证
    logger.info("验证知识索引...")
    retriever = neo4j_knowledge_service.knowledge_index.as_retriever(
        similarity_top_k=3
    )
    test_nodes = retriever.retrieve("python code function")
    
    if test_nodes and test_nodes[0].text != "No relationships found.":
        logger.success(f"✅ 验证成功，检索到 {len(test_nodes)} 个相关文档")
        logger.info(f"示例文档: {test_nodes[0].text[:100]}...")
    else:
        logger.warning("⚠️ 验证失败，可能需要重启服务以重建索引")


if __name__ == "__main__":
    asyncio.run(sync_code_to_knowledge())
