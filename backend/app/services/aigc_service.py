"""AIGC animation generation service for travel diaries."""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx

from app.core.config import settings
from app.models.diaries import DiaryAnimation
from app.repositories.diaries import DiaryRepository
from app.services.diary import DiaryService


class AIGCAnimationService:
    """Service for generating AI-powered travel animations."""

    def __init__(self, repo: DiaryRepository):
        self.repo = repo
        # In production, these would come from settings
        self.api_base_url = "https://api.wan25.com"  # Placeholder
        self.api_key = settings.wan25_api_key if hasattr(settings, 'wan25_api_key') else None
        self.timeout = 300  # 5 minutes timeout

    async def generate_animation(
        self,
        diary_id: int,
        generation_params: Dict[str, Any],
    ) -> DiaryAnimation:
        """
        Generate travel animation for a diary.

        Process:
        1. Extract content and images from diary
        2. Prepare generation request
        3. Submit to AIGC API
        4. Create database record
        5. Start async polling task

        Args:
            diary_id: ID of the diary
            generation_params: Generation parameters (style, duration, etc.)

        Returns:
            DiaryAnimation record
        """
        # Get diary details
        diary = await self.repo.get_by_id(diary_id, load_relationships=True)
        if not diary:
            raise ValueError("Diary not found")

        # Prepare generation data
        generation_data = await self._prepare_generation_data(diary, generation_params)

        # Submit to AIGC API
        task_id = await self._submit_generation_task(generation_data)

        # Create animation record
        animation = DiaryAnimation(
            diary_id=diary_id,
            generation_params=generation_params,
            status='pending',
            progress=0,
            task_id=task_id,
        )

        created = await self.repo.create_animation(animation)

        # Start background polling task
        asyncio.create_task(self._poll_generation_status(created.id, task_id))

        return created

    async def _prepare_generation_data(
        self,
        diary: Any,  # Diary model
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare data for AIGC generation.

        Extracts images, generates description, etc.
        """
        # Extract images (limit to first 10)
        images = diary.media_urls[:10] if diary.media_urls else []

        # Generate description from diary content
        description = self._generate_description(diary, params)

        return {
            'images': images,
            'description': description,
            'style': params.get('style', 'travel'),
            'duration': params.get('duration', 30),
            'custom_description': params.get('custom_description'),
        }

    def _generate_description(self, diary: Any, params: Dict[str, Any]) -> str:
        """Generate animation description from diary content."""
        base_description = f"Travel animation for: {diary.title}"

        if diary.summary:
            base_description += f"\nSummary: {diary.summary}"

        # Add custom description if provided
        if params.get('custom_description'):
            base_description += f"\nCustom: {params['custom_description']}"

        # Add tags for context
        if diary.tags:
            base_description += f"\nTags: {', '.join(diary.tags)}"

        return base_description[:500]  # Limit length

    async def _submit_generation_task(self, generation_data: Dict[str, Any]) -> str:
        """
        Submit generation task to AIGC API.

        This is a placeholder implementation.
        In production, this would call the actual wan2.5 API.
        """
        # Generate a mock task ID for now
        # In production, this would be returned by the API
        task_id = str(uuid.uuid4())

        # Simulate API call delay
        await asyncio.sleep(0.1)

        # Here you would make actual HTTP request:
        # async with httpx.AsyncClient(timeout=self.timeout) as client:
        #     response = await client.post(
        #         f"{self.api_base_url}/generate",
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #         json=generation_data
        #     )
        #     response.raise_for_status()
        #     result = response.json()
        #     return result['task_id']

        return task_id

    async def _poll_generation_status(self, animation_id: int, task_id: str):
        """
        Poll AIGC API for generation status.

        Updates animation record as generation progresses.
        """
        max_attempts = 120  # 2 hours max
        attempt = 0

        while attempt < max_attempts:
            try:
                # Check status with AIGC API
                status_data = await self._check_generation_status(task_id)

                # Update animation record
                await self.repo.update_animation(
                    animation_id,
                    status=status_data['status'],
                    progress=status_data.get('progress', 0),
                    video_url=status_data.get('video_url'),
                    thumbnail_url=status_data.get('thumbnail_url'),
                    error_message=status_data.get('error_message'),
                )

                # Check if completed or failed
                if status_data['status'] in ['completed', 'failed']:
                    break

                # Wait before next check
                await asyncio.sleep(30)  # 30 seconds
                attempt += 1

            except Exception as e:
                # Log error and update animation
                await self.repo.update_animation(
                    animation_id,
                    status='failed',
                    error_message=str(e),
                )
                break

    async def _check_generation_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check generation status from AIGC API.

        This is a placeholder implementation.
        """
        # Simulate status checking
        # In production, this would call the actual API

        # For demo purposes, simulate progress
        import random
        progress = random.randint(0, 100)

        if progress < 90:
            return {
                'status': 'processing',
                'progress': progress,
            }
        else:
            return {
                'status': 'completed',
                'progress': 100,
                'video_url': f"https://example.com/animations/{task_id}.mp4",
                'thumbnail_url': f"https://example.com/thumbnails/{task_id}.jpg",
            }

        # Production implementation:
        # async with httpx.AsyncClient(timeout=30) as client:
        #     response = await client.get(
        #         f"{self.api_base_url}/tasks/{task_id}",
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #     )
        #     response.raise_for_status()
        #     return response.json()

    async def get_animation_status(self, animation_id: int) -> Optional[DiaryAnimation]:
        """Get current animation status."""
        # This would be implemented in the repository
        # For now, return None
        return None

    async def cancel_generation(self, animation_id: int) -> bool:
        """
        Cancel animation generation.

        Returns True if successfully cancelled.
        """
        animation = await self.repo.get_animations(animation_id)
        if not animation or animation.status not in ['pending', 'processing']:
            return False

        # Cancel with AIGC API (placeholder)
        # await self._cancel_api_task(animation.task_id)

        # Update status
        await self.repo.update_animation(
            animation_id,
            status='cancelled',
        )

        return True


# Factory function
def get_aigc_service(repo: DiaryRepository) -> AIGCAnimationService:
    """Get AIGC animation service instance."""
    return AIGCAnimationService(repo)