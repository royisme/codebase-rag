# monitoring/task_monitor.py
"""
Task Queue Monitoring Panel NiceGUI Module
"""
from nicegui import ui, app
import asyncio
import json
from typing import Optional

# Import actual services and models
from services.task_queue import task_queue, TaskStatus, TaskResult

# Status mapping
STATUS_MAP = {
    'pending': 'Pending',
    'processing': 'Processing',
    'success': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled'
}

TASK_TYPE_MAP = {
    'document_processing': 'Document Processing',
    'schema_parsing': 'Schema Parsing',
    'knowledge_graph_construction': 'Knowledge Graph Construction',
    'batch_processing': 'Batch Processing'
}

# Status colors
STATUS_COLORS = {
    'pending': 'orange',
    'processing': 'blue',
    'success': 'green',
    'failed': 'red',
    'cancelled': 'gray'
}

def setup_monitoring_routes():
    """Setup monitoring routes for NiceGUI"""
    
    @ui.page('/monitor')
    async def monitor_page():
        # Set page title
        ui.page_title('Task Queue Monitoring Panel')
        
        # Add custom styles
        ui.add_css('''
            .stat-card {
                text-align: center;
                padding: 1.5rem;
            }
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
        ''')
        
        async def load_stats():
            """Load statistics data"""
            try:
                stats_data = await task_queue.get_queue_stats()
                
                # Extract statistics from status_breakdown
                breakdown = stats_data.get("status_breakdown", {})
                stats = {
                    'pending_tasks': breakdown.get('pending', 0),
                    'processing_tasks': breakdown.get('processing', 0),
                    'completed_tasks': breakdown.get('success', 0),
                    'failed_tasks': breakdown.get('failed', 0),
                    'cancelled_tasks': breakdown.get('cancelled', 0),
                    'total_tasks': stats_data.get('total_tasks', 0)
                }
                update_stats_display(stats)
            except Exception as e:
                ui.notify(f'Failed to load statistics data: {str(e)}', type='negative')
        
        async def load_tasks(status_filter: Optional[str] = None):
            """Load task list"""
            try:
                # Get tasks from storage for most up-to-date status
                if task_queue._storage:
                    from services.task_storage import TaskStatus as StorageTaskStatus, TaskType
                    
                    # Convert status filter
                    storage_status_enum = None
                    if status_filter:
                        storage_status_enum = StorageTaskStatus(status_filter)
                    
                    # Get tasks from storage
                    storage_tasks = await task_queue._storage.list_tasks(
                        status=storage_status_enum,
                        limit=50
                    )
                    
                    # Convert storage tasks to TaskResult objects for display
                    tasks = []
                    for storage_task in storage_tasks:
                        # Check if task exists in memory, otherwise create it
                        if storage_task.id in task_queue.tasks:
                            memory_task = task_queue.tasks[storage_task.id]
                            # Update memory task with storage status
                            memory_task.status = storage_task.status
                            memory_task.progress = storage_task.progress
                            memory_task.completed_at = storage_task.completed_at
                            memory_task.started_at = storage_task.started_at
                            memory_task.error = storage_task.error_message
                            tasks.append(memory_task)
                        else:
                            # Create TaskResult from storage task
                            from services.task_queue import TaskResult
                            task_result = TaskResult(
                                task_id=storage_task.id,
                                status=storage_task.status,
                                progress=storage_task.progress,
                                message="",
                                error=storage_task.error_message,
                                created_at=storage_task.created_at,
                                started_at=storage_task.started_at,
                                completed_at=storage_task.completed_at,
                                metadata=storage_task.payload
                            )
                            tasks.append(task_result)
                            # Also update memory
                            task_queue.tasks[storage_task.id] = task_result
                else:
                    # Fallback to memory if storage not available
                    status_enum = None
                    if status_filter:
                        status_enum = TaskStatus(status_filter)
                    
                    tasks = task_queue.get_all_tasks(
                        status_filter=status_enum,
                        limit=50
                    )
                
                update_tasks_display(tasks)
            except Exception as e:
                ui.notify(f'Failed to load task list: {str(e)}', type='negative')
        
        def update_stats_display(stats):
            """Update statistics display"""
            try:
                pending_card.set_text(str(stats['pending_tasks']))
                processing_card.set_text(str(stats['processing_tasks']))
                success_card.set_text(str(stats['completed_tasks']))
                failed_card.set_text(str(stats['failed_tasks']))
                cancelled_card.set_text(str(stats['cancelled_tasks']))
                total_card.set_text(str(stats['total_tasks']))
            except Exception as e:
                logger.warning(f"Failed to update stats display: {e}")
        
        def update_tasks_display(tasks):
            """Update task list display"""
            try:
                task_container.clear()
                
                if not tasks:
                    with task_container:
                        ui.label('No tasks').classes('text-gray-500 text-center w-full py-8')
                    return
                
                with task_container:
                    for task in tasks:
                        create_task_card(task)
            except Exception as e:
                logger.warning(f"Failed to update tasks display: {e}")
        
        def create_task_card(task):
            """Create task card"""
            with ui.card().classes('w-full mb-4'):
                with ui.row().classes('w-full justify-between items-start'):
                    with ui.column():
                        ui.label(task.metadata.get('task_name', 'Unnamed task')).classes('font-bold text-lg')
                        ui.label(f"ID: {task.task_id}").classes('text-sm text-gray-600 font-mono')
                    
                    # Status label
                    status = task.status.value
                    status_text = STATUS_MAP.get(status, status)
                    color = STATUS_COLORS.get(status, 'gray')
                    ui.badge(status_text, color=color)
                
                # Task information
                with ui.row().classes('w-full mt-2 gap-x-8'):
                    ui.label(f"Created at: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    ui.label(f"Type: {TASK_TYPE_MAP.get(task.metadata.get('task_type', ''), 'Unknown')}")
                
                # Progress bar (if processing)
                if task.status == TaskStatus.PROCESSING:
                    progress = task.progress
                    ui.linear_progress(value=progress/100).classes('mt-2')
                    ui.label(f"{progress:.1f}% - {task.message}")\
                        .classes('text-sm text-gray-600 mt-1')
                
                # Error information (if any)
                if task.error:
                    ui.label(f"Error: {task.error}").classes('text-red-600 mt-2')
                
                # Action buttons
                with ui.row().classes('mt-3 gap-2'):
                    if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                        ui.button('Cancel', on_click=lambda t=task: cancel_task(t.task_id))\
                            .props('size=sm color=red')
                    
                    ui.button('Details', on_click=lambda t=task: view_task_details(t))\
                        .props('size=sm')
        
        async def create_task():
            """Create new task"""
            task_type = task_type_select.value
            task_name = task_name_input.value
            payload_text = task_payload_input.value
            priority = int(task_priority_select.value)
            
            if not task_type or not task_name:
                ui.notify('Please fill in task type and name', type='warning')
                return
            
            try:
                payload = {}
                if payload_text.strip():
                    payload = json.loads(payload_text)
                
                # Use submit_task method with a dummy function
                task_id = await task_queue.submit_task(
                    task_func=lambda: {"message": "Manual task created"},
                    task_name=task_name,
                    task_type=task_type,
                    metadata=payload,
                    priority=priority
                )
                
                ui.notify(f'Task created successfully! ID: {task_id}', type='positive')
                # Clear form
                task_name_input.value = ''
                task_payload_input.value = ''
                # Refresh data
                await refresh_data()
            except json.JSONDecodeError:
                ui.notify('Payload format error, please enter a valid JSON', type='negative')
            except Exception as e:
                ui.notify(f'Failed to create task: {str(e)}', type='negative')
        
        async def cancel_task(task_id: str):
            """Cancel task"""
            try:
                success = await task_queue.cancel_task(task_id)
                if success:
                    ui.notify('Task cancelled', type='positive')
                else:
                    ui.notify('Failed to cancel task', type='negative')
                await refresh_data()
            except Exception as e:
                ui.notify(f'Failed to cancel task: {str(e)}', type='negative')
        
        def view_task_details(task):
            """View task details"""
            with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
                ui.label('Task Details').classes('text-h6 mb-4')
                
                # Basic info
                with ui.card().classes('w-full mb-4'):
                    ui.label('Basic Information').classes('font-bold mb-2')
                    basic_details = [
                        ('Task ID', task.task_id),
                        ('Task Name', task.metadata.get('task_name', 'Unnamed')),
                        ('Task Type', TASK_TYPE_MAP.get(task.metadata.get('task_type', ''), 'Unknown')),
                        ('Status', STATUS_MAP.get(task.status.value, task.status.value)),
                        ('Progress', f"{task.progress:.1f}%"),
                    ]
                    
                    for label, value in basic_details:
                        with ui.row().classes('w-full justify-between'):
                            ui.label(f'{label}:').classes('font-medium')
                            ui.label(str(value))
                
                # Timing info
                with ui.card().classes('w-full mb-4'):
                    ui.label('Timing Information').classes('font-bold mb-2')
                    
                    created_at = task.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    started_at = task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else 'Not started'
                    completed_at = task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else 'Not completed'
                    
                    # Calculate durations
                    from datetime import datetime
                    now = datetime.now()
                    total_time = 'N/A'
                    processing_time = 'N/A'
                    wait_time = 'N/A'
                    
                    if task.started_at:
                        wait_time = str(task.started_at - task.created_at).split('.')[0]
                        if task.completed_at:
                            processing_time = str(task.completed_at - task.started_at).split('.')[0]
                            total_time = str(task.completed_at - task.created_at).split('.')[0]
                        elif task.status.value == 'processing':
                            processing_time = str(now - task.started_at).split('.')[0] + ' (ongoing)'
                            total_time = str(now - task.created_at).split('.')[0] + ' (ongoing)'
                    else:
                        wait_time = str(now - task.created_at).split('.')[0] + ' (waiting)'
                    
                    timing_details = [
                        ('Created at', created_at),
                        ('Started at', started_at),
                        ('Completed at', completed_at),
                        ('Wait time', wait_time),
                        ('Processing time', processing_time),
                        ('Total time', total_time),
                    ]
                    
                    for label, value in timing_details:
                        with ui.row().classes('w-full justify-between'):
                            ui.label(f'{label}:').classes('font-medium')
                            ui.label(str(value))
                
                # Status and message
                if task.message or task.error:
                    with ui.card().classes('w-full mb-4'):
                        ui.label('Status & Messages').classes('font-bold mb-2')
                        
                        if task.message:
                            ui.label('Current message:').classes('font-medium')
                            ui.label(task.message).classes('text-blue-600 mb-2')
                        
                        if task.error:
                            ui.label('Error:').classes('font-medium text-red-600')
                            ui.label(task.error).classes('text-red-600')
                
                # Metadata
                if hasattr(task, 'metadata') and task.metadata:
                    with ui.card().classes('w-full mb-4'):
                        ui.label('Metadata').classes('font-bold mb-2')
                        
                        # Show relevant metadata
                        metadata_items = []
                        if 'filename' in task.metadata:
                            metadata_items.append(('Filename', task.metadata['filename']))
                        if 'file_size' in task.metadata:
                            metadata_items.append(('File size', f"{task.metadata['file_size']:,} chars"))
                        if 'directory_path' in task.metadata:
                            metadata_items.append(('Directory', task.metadata['directory_path']))
                        
                        for label, value in metadata_items:
                            with ui.row().classes('w-full justify-between'):
                                ui.label(f'{label}:').classes('font-medium')
                                ui.label(str(value))
                
                # Close button
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=dialog.close).props('color=primary')
            
            dialog.open()
        
        def load_example_payload():
            """Load example payload"""
            task_type = task_type_select.value
            examples = {
                'document_processing': '{"document_content": "This is an example document content", "document_type": "text"}',
                'schema_parsing': '{"schema_content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));", "schema_type": "sql"}',
                'knowledge_graph_construction': '{"data_sources": [{"type": "document", "content": "example content"}]}',
                'batch_processing': '{"directory_path": "/path/to/documents", "file_patterns": ["*.txt", "*.md"]}'
            }
            task_payload_input.value = examples.get(task_type, '{}')
        
        async def refresh_data():
            """Refresh all data"""
            await load_stats()
            await load_tasks(status_filter_select.value if status_filter_select.value else None)
        
        async def smart_refresh():
            """Smart refresh that only updates when needed"""
            try:
                # Only refresh if there are active (pending/processing) tasks
                active_tasks = task_queue.get_all_tasks(limit=10)
                has_active = any(t.status.value in ['pending', 'processing'] for t in active_tasks)
                
                if has_active:
                    # Refresh both stats and tasks when there's activity
                    await load_stats()
                    await load_tasks(status_filter_select.value if status_filter_select.value else None)
                else:
                    # Only refresh stats when no active tasks
                    await load_stats()
                        
            except Exception as e:
                logger.debug(f"Smart refresh error: {e}")
        
        def detect_file_type(filename: str) -> str:
            """Detect file type based on extension"""
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            
            type_mapping = {
                'txt': 'text',
                'md': 'markdown',
                'java': 'java',
                'py': 'python',
                'js': 'javascript',
                'sql': 'sql',
                'json': 'json',
                'xml': 'xml',
                'html': 'html',
                'csv': 'csv'
            }
            
            return type_mapping.get(extension, 'text')
        
        async def handle_file_upload(e):
            """Handle file upload for document processing"""
            try:
                # Get uploaded file content
                content = e.content.read().decode('utf-8')
                filename = e.name
                file_type = detect_file_type(filename)
                file_size = len(content)
                
                # Display file info
                file_info_label.set_text(f'📄 {filename} | {file_size:,} chars | Type: {file_type}')
                
                # Check file size limits
                if file_size > 50 * 1024:  # 50KB threshold
                    ui.notify(
                        f'文件过大 ({file_size:,} 字符)！\n'
                        f'建议使用以下方式处理大文件：\n'
                        f'1. 使用"目录处理"功能，将文件放在目录中进行批量处理\n'
                        f'2. 通过 MCP 客户端处理大文件\n'
                        f'3. 将文件分割成较小的片段\n'
                        f'当前限制：50KB 以下',
                        type='warning'
                    )
                    return
                
                # For acceptable file sizes, process directly
                task_kwargs = {
                    "document_content": content,
                    "document_type": file_type
                }
                
                # Create document processing task
                from services.task_processors import process_document_task
                task_id = await task_queue.submit_task(
                    task_func=process_document_task,
                    task_kwargs=task_kwargs,
                    task_name=f"Process File: {filename}",
                    task_type="document_processing",
                    metadata={"filename": filename, "file_size": file_size},
                    priority=1
                )
                
                ui.notify(f'File "{filename}" uploaded and processing started! Task ID: {task_id}', type='positive')
                
                # Update the form
                task_type_select.value = 'document_processing'
                task_name_input.value = f"Process File: {filename}"
                
                # Refresh task list
                await refresh_data()
                
            except UnicodeDecodeError:
                ui.notify('File encoding error. Please ensure the file is in UTF-8 format.', type='negative')
            except Exception as error:
                ui.notify(f'File upload failed: {str(error)}', type='negative')
        
        async def handle_directory_processing():
            """Handle directory batch processing"""
            try:
                directory_path = directory_input.value.strip()
                if not directory_path:
                    ui.notify('Please enter a directory path', type='warning')
                    return
                
                # Parse file patterns
                patterns = [p.strip() for p in file_patterns_input.value.split(',') if p.strip()]
                if not patterns:
                    patterns = ['*.*']
                
                # Create batch processing task
                from services.task_processors import process_batch_processing_task
                task_id = await task_queue.submit_task(
                    task_func=process_batch_processing_task,
                    task_kwargs={
                        "directory_path": directory_path,
                        "file_patterns": patterns
                    },
                    task_name=f"Process Directory: {directory_path}",
                    task_type="batch_processing",
                    metadata={"directory_path": directory_path},
                    priority=1
                )
                
                ui.notify(f'Directory processing started! Task ID: {task_id}', type='positive')
                
                # Update the form
                task_type_select.value = 'batch_processing'
                task_name_input.value = f"Process Directory: {directory_path}"
                
                # Refresh task list
                await refresh_data()
                
            except Exception as error:
                ui.notify(f'Directory processing failed: {str(error)}', type='negative')
        
        # Create UI layout
        with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
            # Title
            with ui.card().classes('w-full mb-6'):
                ui.label('Task Queue Monitoring Panel').classes('text-2xl font-bold')
                ui.label('Real-time monitoring and management of asynchronous task processing status').classes('text-gray-600')
            
            # Statistics cards
            with ui.row().classes('w-full gap-4 mb-6'):
                with ui.card().classes('flex-1 stat-card'):
                    pending_card = ui.label('0').classes('stat-number text-orange-600')
                    ui.label('Pending').classes('text-gray-600')
                
                with ui.card().classes('flex-1 stat-card'):
                    processing_card = ui.label('0').classes('stat-number text-blue-600')
                    ui.label('Processing').classes('text-gray-600')
                
                with ui.card().classes('flex-1 stat-card'):
                    success_card = ui.label('0').classes('stat-number text-green-600')
                    ui.label('Completed').classes('text-gray-600')
                
                with ui.card().classes('flex-1 stat-card'):
                    failed_card = ui.label('0').classes('stat-number text-red-600')
                    ui.label('Failed').classes('text-gray-600')
                
                with ui.card().classes('flex-1 stat-card'):
                    cancelled_card = ui.label('0').classes('stat-number text-gray-600')
                    ui.label('Cancelled').classes('text-gray-600')
                
                with ui.card().classes('flex-1 stat-card'):
                    total_card = ui.label('0').classes('stat-number')
                    ui.label('Total').classes('text-gray-600')
            
            # Create task form
            with ui.card().classes('w-full mb-6 p-6'):
                ui.label('Create New Task').classes('text-xl font-bold mb-4')
                
                with ui.column().classes('w-full gap-4'):
                    task_type_select = ui.select(
                        label='Task Type',
                        options={
                            '': 'Please select task type',
                            'document_processing': 'Document Processing',
                            'schema_parsing': 'Schema Parsing',
                            'knowledge_graph_construction': 'Knowledge Graph Construction',
                            'batch_processing': 'Batch Processing'
                        },
                        value=''
                    ).classes('w-full')
                    
                    task_name_input = ui.input('Task Name', placeholder='Enter task name').classes('w-full')
                    
                    # File upload and directory input section
                    with ui.expansion('📁 File & Directory Operations', icon='upload_file').classes('w-full'):
                        with ui.column().classes('w-full gap-4 p-4'):
                            # File upload for document processing
                            ui.label('Upload Small Files (≤ 50KB) for Document Processing').classes('font-bold')
                            ui.label('For larger files, use Directory Processing below').classes('text-sm text-gray-600 mb-2')
                            with ui.row().classes('w-full gap-2 items-end'):
                                file_upload = ui.upload(
                                    on_upload=lambda e: handle_file_upload(e),
                                    multiple=False,
                                    max_file_size=100 * 1024 * 1024  # 100MB browser limit (we check 50KB in code)
                                ).props('accept=".txt,.md,.java,.py,.js,.sql,.json,.xml,.html,.csv"').classes('flex-1')
                                
                                ui.button(
                                    'Clear',
                                    on_click=lambda: file_upload.reset(),
                                    icon='clear'
                                ).props('size=sm')
                            
                            # File info display
                            file_info_label = ui.label('').classes('text-sm text-gray-600')
                            
                            # Directory path for batch processing
                            ui.separator().classes('my-4')
                            ui.label('Directory Path for Batch Processing').classes('font-bold')
                            
                            with ui.row().classes('w-full gap-2'):
                                directory_input = ui.input(
                                    'Directory Path',
                                    placeholder='/path/to/your/documents'
                                ).classes('flex-1')
                                
                                ui.button(
                                    'Process Directory',
                                    on_click=lambda: handle_directory_processing(),
                                    icon='folder_open'
                                ).props('color=blue')
                            
                            file_patterns_input = ui.input(
                                'File Patterns (comma-separated)',
                                placeholder='*.txt,*.md,*.java,*.py',
                                value='*.txt,*.md,*.java,*.py,*.js,*.sql'
                            ).classes('w-full')
                            
                            # Help text
                            with ui.expansion('ℹ️ Help & Supported Formats', icon='help').classes('w-full mt-4'):
                                ui.html('''
                                <div class="text-sm space-y-2">
                                    <p><strong>📁 File Upload (小文件 ≤ 50KB):</strong></p>
                                    <ul class="list-disc list-inside ml-4 space-y-1">
                                        <li>Supported formats: .txt, .md, .java, .py, .js, .sql, .json, .xml, .html, .csv</li>
                                        <li>Maximum file size: 50KB (约50,000字符)</li>
                                        <li>Files are automatically processed and added to the knowledge graph</li>
                                        <li>File type is detected automatically from the extension</li>
                                        <li><strong>Large files will be rejected with suggestions</strong></li>
                                    </ul>
                                    
                                    <p><strong>📂 Directory Processing (推荐用于大文件):</strong></p>
                                    <ul class="list-disc list-inside ml-4 space-y-1">
                                        <li>处理超过50KB的大文件的<strong>首选方法</strong></li>
                                        <li>将大文件放在本地目录中，然后指定目录路径</li>
                                        <li>Use comma-separated patterns like: *.txt,*.md,*.java</li>
                                        <li>Supports nested directories (recursive search)</li>
                                        <li>Each file is processed as a separate document, regardless of size</li>
                                        <li>No file size restrictions for directory processing</li>
                                    </ul>
                                    
                                    <p><strong>🤖 MCP Client (程序化处理):</strong></p>
                                    <ul class="list-disc list-inside ml-4 space-y-1">
                                        <li>Use <code>uv run mcp_client</code> for large file processing</li>
                                        <li>Supports unlimited file sizes</li>
                                        <li>Best for integration with AI assistants</li>
                                        <li>Programmatic access to all knowledge graph features</li>
                                    </ul>
                                    
                                    <p><strong>🔧 Features:</strong></p>
                                    <ul class="list-disc list-inside ml-4 space-y-1">
                                        <li>Real-time progress monitoring</li>
                                        <li>Automatic task queue management</li>
                                        <li>Error handling and retry mechanisms</li>
                                        <li>Knowledge graph integration</li>
                                    </ul>
                                </div>
                                ''')
                    
                    task_payload_input = ui.textarea(
                        'Payload (JSON)',
                        placeholder='{"document_content": "example content", "document_type": "text"}'
                    ).classes('w-full')
                    
                    task_priority_select = ui.select(
                        options={'0': 'Normal', '1': 'High', '2': 'Urgent'},
                        label='Priority',
                        value='0'
                    ).classes('w-full')
                    
                    with ui.row().classes('gap-2'):
                        ui.button('Create Task', on_click=create_task).props('color=green')
                        ui.button('Load Example', on_click=load_example_payload)
            
            # Task list
            with ui.card().classes('w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Task List').classes('text-xl font-bold')
                    
                    with ui.row().classes('gap-2'):
                        status_filter_select = ui.select(
                            options={
                                '': 'All Status',
                                'pending': 'Pending',
                                'processing': 'Processing',
                                'success': 'Completed',
                                'failed': 'Failed',
                                'cancelled': 'Cancelled'
                            },
                            value='',
                            on_change=lambda: asyncio.create_task(refresh_data())
                        )
                        
                        with ui.row().classes('gap-2'):
                            ui.button('🔄 Manual Refresh', on_click=refresh_data).props('color=primary size=sm')
                            ui.badge('🟢 Live Updates', color='green').classes('text-xs')
                
                # Task container
                task_container = ui.column().classes('w-full')
        
        # Initial load data
        await refresh_data()
        
        # Setup smart refresh (less intrusive than before)
        ui.timer(5.0, lambda: asyncio.create_task(smart_refresh()))
    
    @ui.page('/')
    async def root_page():
        """Root page that redirects to monitor"""
        ui.page_title('Code Graph Knowledge System')
        
        with ui.column().classes('w-full max-w-4xl mx-auto p-8'):
            with ui.card().classes('w-full text-center p-8'):
                ui.label('Code Graph Knowledge System').classes('text-3xl font-bold mb-4')
                ui.label('Neo4j-based intelligent knowledge management system').classes('text-gray-600 mb-6')
                
                with ui.row().classes('gap-4 justify-center'):
                    ui.button('Task Monitor', on_click=lambda: ui.navigate.to('/monitor')).props('size=lg color=primary')
                    ui.button('API Docs', on_click=lambda: ui.navigate.to('/docs')).props('size=lg color=secondary')
                
                with ui.expansion('System Information', icon='info').classes('w-full mt-6'):
                    ui.label('Available Features:').classes('font-bold mb-2')
                    features = [
                        'Document Processing and Knowledge Extraction',
                        'SQL Schema Parsing and Analysis', 
                        'Knowledge Graph Construction',
                        'Vector Search and RAG Queries',
                        'Batch File Processing',
                        'Real-time Task Monitoring'
                    ]
                    for feature in features:
                        ui.label(f'• {feature}').classes('ml-4 mb-1')