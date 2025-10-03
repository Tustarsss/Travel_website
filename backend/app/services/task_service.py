"""Background task processing service."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks."""

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """Register a task handler function."""
        self.task_handlers[task_type] = handler

    async def submit_task(self, task_type: str, task_id: str, **kwargs) -> str:
        """
        Submit a background task.

        Args:
            task_type: Type of task (e.g., 'fts_update', 'animation_poll')
            task_id: Unique task identifier
            **kwargs: Task-specific parameters

        Returns:
            Task ID
        """
        if task_type not in self.task_handlers:
            raise ValueError(f"Unknown task type: {task_type}")

        # Create task
        handler = self.task_handlers[task_type]
        task = asyncio.create_task(self._run_task(task_id, handler, **kwargs))

        # Store task reference
        self.tasks[task_id] = task

        logger.info(f"Submitted background task: {task_type} ({task_id})")
        return task_id

    async def _run_task(self, task_id: str, handler: Callable, **kwargs):
        """Execute a background task."""
        try:
            logger.info(f"Starting task {task_id}")
            await handler(**kwargs)
            logger.info(f"Completed task {task_id}")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
        finally:
            # Clean up task reference
            self.tasks.pop(task_id, None)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        task = self.tasks.get(task_id)
        if task:
            return {
                'task_id': task_id,
                'running': not task.done(),
                'done': task.done(),
                'cancelled': task.cancelled() if task.done() else False,
            }
        return None


# Global task service instance
task_service = BackgroundTaskService()


# Task handlers

async def update_fts_index(diary_ids: list[int]):
    """Update FTS index for specified diaries."""
    from app.algorithms.diary_search import get_diary_search_service
    from app.core.db import get_session_maker

    maker = get_session_maker()
    async with maker() as session:
        search_service = get_diary_search_service(session)

        # Rebuild FTS index for affected diaries
        await search_service.rebuild_fts_index()

        logger.info(f"Updated FTS index for diaries: {diary_ids}")


async def poll_animation_status(animation_id: int, task_id: str):
    """Poll animation generation status."""
    from app.services.aigc_service import get_aigc_service
    from app.repositories.diaries import DiaryRepository
    from app.core.db import get_session_maker

    maker = get_session_maker()
    async with maker() as session:
        repo = DiaryRepository(session)
        aigc_service = get_aigc_service(repo)

        # This would be handled by the AIGC service's polling mechanism
        # For now, just log
        logger.info(f"Polling animation status: {animation_id} ({task_id})")


async def cleanup_expired_cache():
    """Clean up expired cache entries."""
    # This would implement cache cleanup logic
    logger.info("Running cache cleanup")


async def generate_popularity_stats():
    """Generate popularity statistics."""
    # This would calculate and cache popularity metrics
    logger.info("Generating popularity statistics")


# Register task handlers
task_service.register_handler('fts_update', update_fts_index)
task_service.register_handler('animation_poll', poll_animation_status)
task_service.register_handler('cache_cleanup', cleanup_expired_cache)
task_service.register_handler('popularity_stats', generate_popularity_stats)


class ScheduledTaskService:
    """Service for running scheduled tasks."""

    def __init__(self):
        self.running = False
        self.tasks = []

    def add_scheduled_task(
        self,
        name: str,
        interval_seconds: int,
        task_func: Callable,
        **kwargs
    ):
        """Add a scheduled task."""
        self.tasks.append({
            'name': name,
            'interval': interval_seconds,
            'func': task_func,
            'kwargs': kwargs,
            'last_run': None,
        })

    async def start(self):
        """Start the scheduled task service."""
        self.running = True
        logger.info("Starting scheduled task service")

        while self.running:
            now = datetime.utcnow()

            for task in self.tasks:
                if (task['last_run'] is None or
                    (now - task['last_run']).total_seconds() >= task['interval']):

                    try:
                        await task['func'](**task['kwargs'])
                        task['last_run'] = now
                        logger.info(f"Executed scheduled task: {task['name']}")
                    except Exception as e:
                        logger.error(f"Scheduled task {task['name']} failed: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def stop(self):
        """Stop the scheduled task service."""
        self.running = False
        logger.info("Stopping scheduled task service")


# Global scheduled task service
scheduled_service = ScheduledTaskService()

# Add default scheduled tasks
scheduled_service.add_scheduled_task(
    name='cache_cleanup',
    interval_seconds=3600,  # 1 hour
    task_func=cleanup_expired_cache,
)

scheduled_service.add_scheduled_task(
    name='popularity_stats',
    interval_seconds=1800,  # 30 minutes
    task_func=generate_popularity_stats,
)