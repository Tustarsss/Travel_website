"""Repository for diary data access."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.diaries import Diary, DiaryAnimation, DiaryMedia, DiaryRating, DiaryView
from app.models.enums import DiaryMediaType, DiaryStatus
from app.models.users import User
from app.models.locations import Region


class DiaryRepository:
    """Data access layer for diaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, diary: Diary) -> Diary:
        """Create a new diary."""
        self.session.add(diary)
        await self.session.commit()
        await self.session.refresh(diary)
        return diary

    async def add_media(
        self,
        diary_id: int,
        *,
        placeholder: str,
        filename: str,
        content_type: str,
        media_type: DiaryMediaType,
        payload: bytes,
        is_compressed: bool,
        original_size: int,
        compressed_size: int,
    ) -> DiaryMedia:
        """Persist a single media file for a diary."""
        media = DiaryMedia(
            diary_id=diary_id,
            placeholder=placeholder,
            filename=filename,
            content_type=content_type,
            media_type=media_type,
            data=payload,
            is_compressed=is_compressed,
            original_size=original_size,
            compressed_size=compressed_size,
        )
        self.session.add(media)
        await self.session.flush()
        await self.session.refresh(media)
        return media

    async def get_media(
        self,
        diary_id: int,
        media_id: int,
    ) -> Optional[DiaryMedia]:
        """Fetch a diary media entry by id."""
        query = select(DiaryMedia).where(
            and_(
                DiaryMedia.id == media_id,
                DiaryMedia.diary_id == diary_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, 
        diary_id: int,
        load_relationships: bool = True
    ) -> Optional[Diary]:
        """Get diary by ID with optional relationship loading."""
        query = select(Diary).where(Diary.id == diary_id)
        
        if load_relationships:
            query = query.options(
                selectinload(Diary.author),
                selectinload(Diary.ratings).selectinload(DiaryRating.user),
                selectinload(Diary.media_items),
                selectinload(Diary.region),
            )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, diary: Diary) -> Diary:
        """Update an existing diary."""
        self.session.add(diary)
        await self.session.commit()
        await self.session.refresh(diary)
        return diary

    async def delete(self, diary: Diary) -> None:
        """Delete a diary."""
        await self.session.delete(diary)
        await self.session.commit()

    async def list_diaries(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        region_id: Optional[int] = None,
        author_id: Optional[int] = None,
        status: Optional[DiaryStatus] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
    ) -> tuple[List[Diary], int]:
        """
        List diaries with filtering and pagination.
        
        Returns:
            Tuple of (diaries, total_count)
        """
        # Base query
        conditions = []
        
        if region_id:
            conditions.append(Diary.region_id == region_id)
        if author_id:
            conditions.append(Diary.user_id == author_id)
        if status:
            conditions.append(Diary.status == status)
        
        # Tag filtering (at least one tag matches)
        if tags:
            tag_conditions = [Diary.tags.contains([tag]) for tag in tags]
            conditions.append(or_(*tag_conditions))
        
        # Search query (simple LIKE search on title and content)
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    Diary.title.ilike(search_pattern),
                    Diary.content.ilike(search_pattern),
                )
            )
        
        # Build where clause
        where_clause = and_(*conditions) if conditions else True
        
        # Count query
        count_query = select(func.count(Diary.id)).where(where_clause)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query with pagination
        offset = (page - 1) * page_size
        data_query = (
            select(Diary)
            .where(where_clause)
            .options(
                selectinload(Diary.author),
                selectinload(Diary.region),
            )
            .offset(offset)
            .limit(page_size)
        )
        
        result = await self.session.execute(data_query)
        diaries = list(result.scalars().all())
        
        return diaries, total

    async def get_top_k_diaries(
        self,
        k: int,
        filters: Optional[dict] = None,
    ) -> List[Diary]:
        """
        Get all candidate diaries for ranking (without sorting).
        Actual sorting will be done in-memory using ranking algorithms.
        """
        conditions = []
        
        # Apply filters
        if filters:
            if filters.get('region_id'):
                conditions.append(Diary.region_id == filters['region_id'])
            if filters.get('status'):
                conditions.append(Diary.status == filters['status'])
            else:
                # Default to published only
                conditions.append(Diary.status == DiaryStatus.PUBLISHED)
        
        where_clause = and_(*conditions) if conditions else Diary.status == DiaryStatus.PUBLISHED
        
        # Fetch all candidates (we'll rank in-memory)
        # For better performance with large datasets, consider limiting here
        query = (
            select(Diary)
            .where(where_clause)
            .options(
                selectinload(Diary.author),
                selectinload(Diary.region),
            )
            .limit(k * 10)  # Fetch more candidates than needed for better ranking
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_regions_by_ids(self, region_ids: List[int]) -> dict[int, Region]:
        """Fetch regions by id and return mapping keyed by region id."""
        unique_ids = list({rid for rid in region_ids if rid})
        if not unique_ids:
            return {}

        query = select(Region).where(Region.id.in_(unique_ids))
        result = await self.session.execute(query)
        regions = result.scalars().all()
        return {region.id: region for region in regions}

    # === Rating Operations ===
    
    async def add_rating(
        self,
        diary_id: int,
        user_id: int,
        score: int,
        comment: Optional[str] = None,
    ) -> DiaryRating:
        """Add or update a user's rating for a diary."""
        # Check if rating exists
        query = select(DiaryRating).where(
            and_(
                DiaryRating.diary_id == diary_id,
                DiaryRating.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing rating
            existing.score = score
            existing.comment = comment
            existing.updated_at = datetime.utcnow()
            rating = existing
        else:
            # Create new rating
            rating = DiaryRating(
                diary_id=diary_id,
                user_id=user_id,
                score=score,
                comment=comment,
            )
            self.session.add(rating)
        
        await self.session.commit()
        await self.session.refresh(rating)
        
        # Update diary's aggregated rating
        await self._update_diary_rating(diary_id)
        
        return rating

    async def _update_diary_rating(self, diary_id: int) -> None:
        """Recalculate and update diary's average rating and count."""
        query = select(
            func.avg(DiaryRating.score).label('avg_rating'),
            func.count(DiaryRating.id).label('count'),
            func.count(DiaryRating.comment).label('comments_count'),
        ).where(DiaryRating.diary_id == diary_id)
        
        result = await self.session.execute(query)
        row = result.one()
        
        # Update diary
        diary = await self.get_by_id(diary_id, load_relationships=False)
        if diary:
            diary.rating = float(row.avg_rating) if row.avg_rating else 0.0
            diary.ratings_count = row.count
            diary.comments_count = row.comments_count or 0
            await self.session.commit()

    async def list_ratings(
        self,
        diary_id: int,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[DiaryRating], int]:
        """List ratings for a diary with pagination."""
        offset = (page - 1) * page_size

        query = (
            select(DiaryRating)
            .where(DiaryRating.diary_id == diary_id)
            .options(selectinload(DiaryRating.user))
            .order_by(desc(DiaryRating.updated_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        count_query = select(func.count(DiaryRating.id)).where(DiaryRating.diary_id == diary_id)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        return items, total

    async def get_rating_statistics(self, diary_id: int) -> dict:
        """Calculate aggregated rating statistics for a diary."""
        distribution_columns = [
            func.sum(case((DiaryRating.score == score, 1), else_=0)).label(f"score_{score}")
            for score in range(1, 6)
        ]

        stats_query = select(
            func.avg(DiaryRating.score).label('avg_rating'),
            func.count(DiaryRating.id).label('total'),
            func.count(DiaryRating.comment).label('comments_count'),
            *distribution_columns,
        ).where(DiaryRating.diary_id == diary_id)

        result = await self.session.execute(stats_query)
        row = result.one()

        distribution: dict[int, int] = {}
        for score in range(1, 6):
            value = getattr(row, f"score_{score}") or 0
            distribution[score] = int(value)

        return {
            "average": float(row.avg_rating) if row.avg_rating else 0.0,
            "total": int(row.total) if row.total else 0,
            "comments_count": int(row.comments_count) if row.comments_count else 0,
            "distribution": distribution,
        }

    async def get_rating_by_user(self, diary_id: int, user_id: int) -> Optional[DiaryRating]:
        """Fetch a specific user's rating for a diary if it exists."""
        query = (
            select(DiaryRating)
            .where(
                and_(
                    DiaryRating.diary_id == diary_id,
                    DiaryRating.user_id == user_id,
                )
            )
            .options(selectinload(DiaryRating.user))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # === View Operations ===
    
    async def record_view(
        self,
        diary_id: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DiaryView:
        """Record a diary view."""
        view = DiaryView(
            diary_id=diary_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(view)
        await self.session.commit()
        
        # Update diary popularity (view count)
        await self._update_diary_popularity(diary_id)
        
        return view

    async def _update_diary_popularity(self, diary_id: int) -> None:
        """Update diary's popularity (view count)."""
        query = select(func.count(DiaryView.id)).where(
            DiaryView.diary_id == diary_id
        )
        result = await self.session.execute(query)
        count = result.scalar_one()
        
        # Update diary
        diary = await self.get_by_id(diary_id, load_relationships=False)
        if diary:
            diary.popularity = count
            await self.session.commit()

    # === Animation Operations ===
    
    async def create_animation(
        self,
        animation: DiaryAnimation
    ) -> DiaryAnimation:
        """Create a new animation record."""
        self.session.add(animation)
        await self.session.commit()
        await self.session.refresh(animation)
        return animation

    async def update_animation(
        self,
        animation_id: int,
        **kwargs
    ) -> Optional[DiaryAnimation]:
        """Update animation status/progress."""
        query = select(DiaryAnimation).where(DiaryAnimation.id == animation_id)
        result = await self.session.execute(query)
        animation = result.scalar_one_or_none()
        
        if animation:
            for key, value in kwargs.items():
                if hasattr(animation, key):
                    setattr(animation, key, value)
            
            animation.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(animation)
        
        return animation

    async def get_animations(
        self,
        diary_id: int
    ) -> List[DiaryAnimation]:
        """Get all animations for a diary."""
        query = select(DiaryAnimation).where(
            DiaryAnimation.diary_id == diary_id
        ).order_by(desc(DiaryAnimation.created_at))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
