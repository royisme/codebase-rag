#!/usr/bin/env python3
"""
HTTP SSE客户端示例（混合实现）

演示如何通过HTTP API提交任务并使用SSE进行实时监控
注意：这不是纯MCP实现，而是HTTP + SSE的混合方案
"""

import asyncio
import json
import aiohttp
from typing import Optional, Dict, Any
import time

class MCPSSEClient:
    """MCP + SSE Combined Client"""
    
    def __init__(self, mcp_server_url: str = "stdio", sse_base_url: str = "http://localhost:8000/api/v1/sse"):
        self.mcp_server_url = mcp_server_url
        self.sse_base_url = sse_base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def stream_task_progress(self, task_id: str, callback=None):
        """
        Stream task progress via SSE
        
        Args:
            task_id: Task ID
            callback: Progress callback function
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")
        
        url = f"{self.sse_base_url}/task/{task_id}"
        
        try:
            async with self.session.get(url) as response:
                print(f"📡 Connected to SSE stream for task {task_id}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        
                        try:
                            data = json.loads(data_str)
                            await self._handle_sse_event(data, callback)
                            
                            # Exit stream if task completed
                            if data.get('type') in ['completed', 'error']:
                                break
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ Invalid JSON data: {data_str}")
                            
        except aiohttp.ClientError as e:
            print(f"❌ SSE connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    async def _handle_sse_event(self, data: Dict[str, Any], callback=None):
        """Handle SSE events"""
        event_type = data.get('type')
        
        if event_type == 'connected':
            print(f"✅ Connected to task monitoring")
            
        elif event_type == 'progress':
            progress = data.get('progress', 0)
            status = data.get('status', 'unknown')
            message = data.get('message', '')
            print(f"📊 Progress: {progress:.1f}% | Status: {status} | {message}")
            
            if callback:
                await callback('progress', data)
                
        elif event_type == 'completed':
            final_status = data.get('final_status', 'unknown')
            final_message = data.get('final_message', '')
            print(f"🎉 Task completed: {final_status} | {final_message}")
            
            if callback:
                await callback('completed', data)
                
        elif event_type == 'error':
            error = data.get('error', 'Unknown error')
            print(f"❌ Error: {error}")
            
            if callback:
                await callback('error', data)

async def demo_mcp_with_sse():
    """Demonstrate MCP + SSE combined usage"""
    
    print("🚀 MCP + SSE Real-time Monitoring Demo")
    print("=" * 50)
    
    # Simulate task submission via MCP (using HTTP request to simulate MCP call)
    async with aiohttp.ClientSession() as session:
        
        # 1. Submit document processing task
        print("📄 Submitting document processing task...")
        
        task_data = {
            "task_name": "Process Large Document",
            "task_type": "document_processing",
            "payload": {
                "document_content": "This is a large document content..." * 100,  # Simulate large document
                "document_type": "text"
            }
        }
        
        # Submit task via API (simulate MCP call)
        async with session.post(
            "http://localhost:8000/api/v1/tasks/submit",
            json=task_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                task_id = result.get('task_id')
                print(f"✅ Task submitted successfully! Task ID: {task_id}")
            else:
                print(f"❌ Failed to submit task: {response.status}")
                return
    
    # 2. Use SSE for real-time task progress monitoring
    print(f"\n📡 Starting real-time monitoring for task {task_id}...")
    
    async def progress_callback(event_type: str, data: Dict[str, Any]):
        """Custom progress callback"""
        if event_type == 'progress':
            # Can add custom logic here, such as updating UI, sending notifications, etc.
            pass
        elif event_type == 'completed':
            print(f"✨ Task result: {data.get('result', {})}")
    
    # 3. Start SSE stream monitoring
    async with MCPSSEClient() as client:
        await client.stream_task_progress(task_id, progress_callback)
    
    print("\n🎯 Demo completed!")

async def demo_multiple_tasks_monitoring():
    """Demonstrate multiple tasks monitoring"""
    
    print("🚀 Multiple Tasks Monitoring Demo")
    print("=" * 50)
    
    task_ids = []
    
    # Submit multiple tasks
    async with aiohttp.ClientSession() as session:
        for i in range(3):
            task_data = {
                "task_name": f"Document {i+1}",
                "task_type": "document_processing",
                "payload": {
                    "document_content": f"Document {i+1} content..." * 50,
                    "document_type": "text"
                }
            }
            
            async with session.post(
                "http://localhost:8000/api/v1/tasks/submit",
                json=task_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result.get('task_id')
                    task_ids.append(task_id)
                    print(f"✅ Task {i+1} submitted: {task_id}")
    
    # Monitor all tasks
    print(f"\n📡 Monitoring {len(task_ids)} tasks...")
    
    async with MCPSSEClient() as client:
        url = f"{client.sse_base_url}/tasks"
        
        async with client.session.get(url) as response:
            print("📊 Connected to all tasks stream")
            
            tasks_completed = 0
            async for line in response.content:
                line = line.decode('utf-8').strip()
                
                if line.startswith('data: '):
                    data_str = line[6:]
                    
                    try:
                        data = json.loads(data_str)
                        event_type = data.get('type')
                        
                        if event_type == 'task_updated':
                            task_id = data.get('task_id')
                            status = data.get('status')
                            progress = data.get('progress', 0)
                            
                            if task_id in task_ids:
                                print(f"📊 Task {task_id[:8]}: {progress:.1f}% | {status}")
                                
                                if status in ['success', 'failed', 'cancelled']:
                                    tasks_completed += 1
                                    
                                    if tasks_completed >= len(task_ids):
                                        print("🎉 All tasks completed!")
                                        break
                                        
                    except json.JSONDecodeError:
                        pass

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        asyncio.run(demo_multiple_tasks_monitoring())
    else:
        asyncio.run(demo_mcp_with_sse())

if __name__ == "__main__":
    main()