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
                # Convert status filter
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
            pending_card.set_content(str(stats['pending_tasks']))
            processing_card.set_content(str(stats['processing_tasks']))
            success_card.set_content(str(stats['completed_tasks']))
            failed_card.set_content(str(stats['failed_tasks']))
            cancelled_card.set_content(str(stats['cancelled_tasks']))
            total_card.set_content(str(stats['total_tasks']))
        
        def update_tasks_display(tasks):
            """Update task list display"""
            task_container.clear()
            
            if not tasks:
                with task_container:
                    ui.label('No tasks').classes('text-gray-500 text-center w-full py-8')
                return
            
            with task_container:
                for task in tasks:
                    create_task_card(task)
        
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
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('Task Details').classes('text-h6')
                
                details = [
                    ('Task ID', task.task_id),
                    ('Task Name', task.metadata.get('task_name', 'Unnamed')),
                    ('Task Type', TASK_TYPE_MAP.get(task.metadata.get('task_type', ''), 'Unknown')),
                    ('Status', STATUS_MAP.get(task.status.value, task.status.value)),
                    ('Progress', f"{task.progress:.1f}%"),
                    ('Created at', task.created_at.strftime('%Y-%m-%d %H:%M:%S')),
                    ('Started at', task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else 'Not started'),
                    ('Completed at', task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else 'Not completed'),
                    ('Message', task.message),
                ]
                
                for label, value in details:
                    with ui.row().classes('w-full'):
                        ui.label(f'{label}:').classes('font-bold')
                        ui.label(str(value))
                
                if task.error:
                    ui.label('Error:').classes('font-bold text-red-600 mt-2')
                    ui.label(task.error).classes('text-red-600')
                
                ui.button('Close', on_click=dialog.close).classes('mt-4')
            
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
                    
                    task_payload_input = ui.textarea(
                        'Payload (JSON)',
                        placeholder='{"document_content": "example content", "document_type": "text"}'
                    ).classes('w-full')
                    
                    task_priority_select = ui.select(
                        'Priority',
                        options={'0': 'Normal', '1': 'High', '2': 'Urgent'},
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
                        ui.button('Refresh', on_click=refresh_data).props('icon=refresh')
                
                # Task container
                task_container = ui.column().classes('w-full')
        
        # Initial load data
        await refresh_data()
        
        # Set auto refresh (every 5 seconds)
        ui.timer(5.0, refresh_data)