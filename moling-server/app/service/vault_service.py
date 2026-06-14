"""Moling - Vault Service.

Business logic for the Four Databases (四库): Characters, Timeline, Plot Promises, World Building.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao, project_dao
from app.errors import NotFoundError, ErrorCode, ForbiddenError
from app.models import VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld
from app.schemas.vault import CharacterResp, TimelineResp, PlotPromiseResp, WorldResp


class VaultService:
    """Service for vault operations (four databases)."""

    # ============ Characters ============

    async def list_characters(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[CharacterResp]:
        """List all characters in a project's vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        characters = await vault_dao.get_characters(db, project_id)
        return [CharacterResp.model_validate(c) for c in characters]

    async def create_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_data: dict,
    ) -> CharacterResp:
        """Create a new character in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Create character
        character_data["project_id"] = project_id
        character = await vault_dao.create_character(db, character_data)
        await db.commit()
        await db.refresh(character)

        return CharacterResp.model_validate(character)

    async def update_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
        character_data: dict,
    ) -> CharacterResp:
        """Update a character in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get character
        character = await vault_dao.get_character(db, character_id)
        if character is None or character.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHARACTER_NOT_FOUND,
                detail="Character not found",
            )

        # Update character
        character = await vault_dao.update_character(db, character, character_data)
        await db.commit()
        await db.refresh(character)

        return CharacterResp.model_validate(character)

    async def delete_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
    ) -> None:
        """Delete a character from the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Delete character
        await vault_dao.delete_character(db, character_id)
        await db.commit()

    async def get_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
    ) -> CharacterResp:
        """Get a single character by ID."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get character
        character = await vault_dao.get_character(db, character_id)
        if character is None or character.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHARACTER_NOT_FOUND,
                detail="Character not found",
            )

        return CharacterResp.model_validate(character)

    # ============ Timeline ============

    async def list_timeline(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[TimelineResp]:
        """List all timeline events in a project's vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        events = await vault_dao.get_timeline(db, project_id)
        return [TimelineResp.model_validate(e) for e in events]

    async def create_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_data: dict,
    ) -> TimelineResp:
        """Create a new timeline event in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Create event
        event_data["project_id"] = project_id
        event = await vault_dao.create_timeline_event(db, event_data)
        await db.commit()
        await db.refresh(event)

        return TimelineResp.model_validate(event)

    async def get_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
    ) -> TimelineResp:
        """Get a single timeline event by ID."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get event
        event = await vault_dao.get_timeline_event(db, event_id)
        if event is None or event.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.TIMELINE_NOT_FOUND,
                detail="Timeline event not found",
            )

        return TimelineResp.model_validate(event)

    async def update_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
        event_data: dict,
    ) -> TimelineResp:
        """Update a timeline event in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get event
        event = await vault_dao.get_timeline_event(db, event_id)
        if event is None or event.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.TIMELINE_NOT_FOUND,
                detail="Timeline event not found",
            )

        # Update event
        event = await vault_dao.update_timeline_event(db, event, event_data)
        await db.commit()
        await db.refresh(event)

        return TimelineResp.model_validate(event)

    async def delete_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
    ) -> None:
        """Delete a timeline event from the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Delete event
        await vault_dao.delete_timeline_event(db, event_id)
        await db.commit()

    # ============ Plot Promises ============

    async def list_plot_promises(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[PlotPromiseResp]:
        """List all plot promises in a project's vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        promises = await vault_dao.get_plot_promises(db, project_id)
        return [PlotPromiseResp.model_validate(p) for p in promises]

    async def create_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_data: dict,
    ) -> PlotPromiseResp:
        """Create a new plot promise in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Create promise
        promise_data["project_id"] = project_id
        promise = await vault_dao.create_plot_promise(db, promise_data)
        await db.commit()
        await db.refresh(promise)

        return PlotPromiseResp.model_validate(promise)

    async def get_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
    ) -> PlotPromiseResp:
        """Get a single plot promise by ID."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get promise
        promise = await vault_dao.get_plot_promise(db, promise_id)
        if promise is None or promise.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.PLOT_PROMISE_NOT_FOUND,
                detail="Plot promise not found",
            )

        return PlotPromiseResp.model_validate(promise)

    async def update_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
        promise_data: dict,
    ) -> PlotPromiseResp:
        """Update a plot promise in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get promise
        promise = await vault_dao.get_plot_promise(db, promise_id)
        if promise is None or promise.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.PLOT_PROMISE_NOT_FOUND,
                detail="Plot promise not found",
            )

        # Update promise
        promise = await vault_dao.update_plot_promise(db, promise, promise_data)
        await db.commit()
        await db.refresh(promise)

        return PlotPromiseResp.model_validate(promise)

    async def delete_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
    ) -> None:
        """Delete a plot promise from the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Delete promise
        await vault_dao.delete_plot_promise(db, promise_id)
        await db.commit()

    # ============ World Building ============

    async def list_world_entries(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[WorldResp]:
        """List all world-building entries in a project's vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        entries = await vault_dao.get_world_entries(db, project_id)
        return [WorldResp.model_validate(e) for e in entries]

    async def create_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_data: dict,
    ) -> WorldResp:
        """Create a new world-building entry in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Create entry
        entry_data["project_id"] = project_id
        entry = await vault_dao.create_world_entry(db, entry_data)
        await db.commit()
        await db.refresh(entry)

        return WorldResp.model_validate(entry)

    async def get_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
    ) -> WorldResp:
        """Get a single world-building entry by ID."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get entry
        entry = await vault_dao.get_world_entry(db, entry_id)
        if entry is None or entry.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.WORLD_NOT_FOUND,
                detail="World entry not found",
            )

        return WorldResp.model_validate(entry)

    async def update_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
        entry_data: dict,
    ) -> WorldResp:
        """Update a world-building entry in the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Get entry
        entry = await vault_dao.get_world_entry(db, entry_id)
        if entry is None or entry.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.WORLD_NOT_FOUND,
                detail="World entry not found",
            )

        # Update entry
        entry = await vault_dao.update_world_entry(db, entry, entry_data)
        await db.commit()
        await db.refresh(entry)

        return WorldResp.model_validate(entry)

    async def delete_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
    ) -> None:
        """Delete a world-building entry from the vault."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Delete entry
        await vault_dao.delete_world_entry(db, entry_id)
        await db.commit()

    async def get_summary(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> dict:
        """Get four databases summary (characters, timeline, plot promises, world)."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise ForbiddenError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        from sqlalchemy import select, func

        # Count characters
        stmt = select(func.count()).select_from(VaultCharacter).where(
            VaultCharacter.project_id == project_id
        )
        result = await db.execute(stmt)
        character_count = result.scalar() or 0

        # Count timeline events
        stmt = select(func.count()).select_from(VaultTimeline).where(
            VaultTimeline.project_id == project_id
        )
        result = await db.execute(stmt)
        timeline_count = result.scalar() or 0

        # Count plot promises
        stmt = select(func.count()).select_from(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id
        )
        result = await db.execute(stmt)
        promise_count = result.scalar() or 0

        # Count world entries
        stmt = select(func.count()).select_from(VaultWorld).where(
            VaultWorld.project_id == project_id
        )
        result = await db.execute(stmt)
        world_count = result.scalar() or 0

        # Get recent characters
        stmt = (
            select(VaultCharacter)
            .where(VaultCharacter.project_id == project_id)
            .order_by(VaultCharacter.updated_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        recent_characters = list(result.scalars().all())

        return {
            "success": True,
            "summary": {
                "character_count": character_count,
                "timeline_count": timeline_count,
                "promise_count": promise_count,
                "world_count": world_count,
            },
            "recent_characters": [
                CharacterResp.model_validate(c) for c in recent_characters
            ],
        }


# Singleton instance
vault_service = VaultService()
