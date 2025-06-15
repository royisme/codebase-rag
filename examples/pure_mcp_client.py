#!/usr/bin/env python3
"""
Pure MCP Client Real-time Monitoring Example

Demonstrates how to perform real-time task monitoring via MCP tools without relying on HTTP SSE API
"""

import asyncio
import json
from typing import Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demo_pure_mcp_monitoring():
    """Demonstrate pure MCP real-time monitoring"""
    
    print("🚀 Pure MCP Real-time Monitoring Demo")
    print("=" * 50)
    
    # 连接到MCP服务器
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✅ Connected to MCP server")
            
            # 1. Submit document processing task
            print("\n📄 Submitting document via MCP...")
            
            result = await session.call_tool(
                "add_document",
                {
                    "content": "This is a large document content that will trigger background processing..." * 200,
                    "title": "Large Test Document",
                    "metadata": {"source": "mcp_demo", "type": "test"}
                }
            )
            
            if result.isError:
                print(f"❌ Failed to submit task: {result.error}")
                return
                
            task_id = result.content[0].text
            task_data = json.loads(task_id)
            
            if not task_data.get("success"):
                print(f"❌ Task submission failed: {task_data.get('error')}")
                return
                
            actual_task_id = task_data.get("task_id")
            print(f"✅ Task submitted! Task ID: {actual_task_id}")
            
            # 2. Use MCP watch_task tool for real-time monitoring
            print(f"\n📡 Starting MCP real-time monitoring for task {actual_task_id}...")
            
            watch_result = await session.call_tool(
                "watch_task",
                {
                    "task_id": actual_task_id,
                    "timeout": 300,  # 5分钟超时
                    "interval": 1.0  # 每秒检查一次
                }
            )
            
            if watch_result.isError:
                print(f"❌ Watch task failed: {watch_result.error}")
                return
                
            # Parse monitoring results
            watch_data = json.loads(watch_result.content[0].text)
            
            if watch_data.get("success"):
                print(f"\n🎉 Task completed successfully!")
                print(f"Final Status: {watch_data.get('final_status')}")
                print(f"Final Message: {watch_data.get('final_message')}")
                print(f"Total Watch Time: {watch_data.get('total_watch_time', 0):.2f}s")
                
                # Show progress history
                progress_history = watch_data.get('progress_history', [])
                if progress_history:
                    print(f"\n📊 Progress History ({len(progress_history)} updates):")
                    for i, entry in enumerate(progress_history[-5:]):  # Show last 5 updates
                        print(f"  {i+1}. {entry['progress']:.1f}% - {entry['status']} - {entry['message']}")
                        
                # Show final result
                final_result = watch_data.get('result')
                if final_result:
                    print(f"\n✨ Final Result: {final_result}")
                    
            else:
                print(f"❌ Watch failed: {watch_data.get('error')}")

async def demo_multiple_tasks_mcp():
    """Demonstrate MCP multiple tasks monitoring"""
    
    print("\n🚀 Multiple Tasks MCP Monitoring Demo")
    print("=" * 50)
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✅ Connected to MCP server")
            
            # Submit multiple tasks
            task_ids = []
            for i in range(3):
                print(f"\n📄 Submitting document {i+1}...")
                
                result = await session.call_tool(
                    "add_document",
                    {
                        "content": f"Document {i+1} content that needs processing..." * 50,
                        "title": f"Test Document {i+1}",
                        "metadata": {"batch": "demo", "index": i+1}
                    }
                )
                
                if not result.isError:
                    task_data = json.loads(result.content[0].text)
                    if task_data.get("success"):
                        task_id = task_data.get("task_id")
                        task_ids.append(task_id)
                        print(f"✅ Task {i+1} submitted: {task_id}")
            
            if not task_ids:
                print("❌ No tasks submitted successfully")
                return
                
            # Use watch_tasks to monitor all tasks
            print(f"\n📡 Monitoring {len(task_ids)} tasks...")
            
            watch_result = await session.call_tool(
                "watch_tasks",
                {
                    "task_ids": task_ids,
                    "timeout": 300,
                    "interval": 2.0
                }
            )
            
            if watch_result.isError:
                print(f"❌ Watch tasks failed: {watch_result.error}")
                return
                
            # Parse batch monitoring results
            watch_data = json.loads(watch_result.content[0].text)
            
            if watch_data.get("success"):
                print(f"\n🎉 All tasks monitoring completed!")
                
                summary = watch_data.get('summary', {})
                print(f"📊 Summary:")
                print(f"  Total: {summary.get('total_tasks', 0)}")
                print(f"  Successful: {summary.get('successful', 0)}")
                print(f"  Failed: {summary.get('failed', 0)}")
                print(f"  Total Time: {watch_data.get('total_watch_time', 0):.2f}s")
                
                # Show final status of each task
                final_results = watch_data.get('final_results', {})
                print(f"\n📋 Final Results:")
                for task_id, result in final_results.items():
                    status = result.get('status', 'unknown')
                    message = result.get('message', '')
                    print(f"  {task_id[:8]}: {status} - {message}")
                    
            else:
                print(f"❌ Batch watch failed: {watch_data.get('error')}")

async def demo_task_listing():
    """Demonstrate task list querying"""
    
    print("\n🚀 Task Listing Demo")
    print("=" * 30)
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # List all tasks
            result = await session.call_tool(
                "list_tasks",
                {
                    "limit": 10
                }
            )
            
            if result.isError:
                print(f"❌ List tasks failed: {result.error}")
                return
                
            tasks_data = json.loads(result.content[0].text)
            
            if tasks_data.get("success"):
                tasks = tasks_data.get('tasks', [])
                print(f"📋 Found {len(tasks)} recent tasks:")
                
                for task in tasks[:5]:  # Show first 5
                    task_id = task['task_id']
                    status = task['status']
                    progress = task['progress']
                    message = task['message']
                    print(f"  {task_id[:8]}: {progress:.1f}% - {status} - {message}")
                    
            else:
                print(f"❌ Failed to list tasks: {tasks_data.get('error')}")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "multi":
            asyncio.run(demo_multiple_tasks_mcp())
        elif sys.argv[1] == "list":
            asyncio.run(demo_task_listing())
        else:
            print("Usage: python pure_mcp_client.py [multi|list]")
    else:
        asyncio.run(demo_pure_mcp_monitoring())

if __name__ == "__main__":
    main()