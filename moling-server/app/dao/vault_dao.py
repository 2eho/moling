"""澧ㄧ伒 (Moling) 鈥?Vault DAO (unified access to all vault entity types)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld


class VaultDAO:
    """Data access for all four vault entity types.

    Provides unified query methods under a single class rather than
    separate DAOs for each vault model.
    """

    # ---- Characters ----

    async def get_characters(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[VaultCharacter]:
        """List all vault characters for a project."""
        stmt = (
            select(VaultCharacter)
            .where(VaultCharacter.project_id == project_id)
            .order_by(VaultCharacter.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_character(
        self,
        db: AsyncSession,
        character_id: int,
    ) -> VaultCharacter | None:
        """Get a single vault character by id."""
        stmt = select(VaultCharacter).where(VaultCharacter.id == character_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_character(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> VaultCharacter:
        """Create a new vault character."""
        db_obj = VaultCharacter(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_character(
        self,
        db: AsyncSession,
        db_obj: VaultCharacter,
        obj_in: dict,
    ) -> VaultCharacter:
        """Update an existing vault character."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_character(
        self,
        db: AsyncSession,
        character_id: int,
    ) -> None:
        """Delete a vault character by id."""
        stmt = select(VaultCharacter).where(VaultCharacter.id == character_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await db.delete(db_obj)
            await db.flush()

    # ---- Timeline ----

    async def get_timeline(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[VaultTimeline]:
        """List all timeline events for a project, ordered by chapter."""
        stmt = (
            select(VaultTimeline)
            .where(VaultTimeline.project_id == project_id)
            .order_by(VaultTimeline.chapter_number.asc(), VaultTimeline.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_timeline_event(
        self,
        db: AsyncSession,
        event_id: int,
    ) -> VaultTimeline | None:
        """Get a single timeline event by id."""
        stmt = select(VaultTimeline).where(VaultTimeline.id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_timeline_event(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> VaultTimeline:
        """Create a new timeline event."""
        db_obj = VaultTimeline(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_timeline_event(
        self,
        db: AsyncSession,
        db_obj: VaultTimeline,
        obj_in: dict,
    ) -> VaultTimeline:
        """Update an existing timeline event."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_timeline_event(
        self,
        db: AsyncSession,
        event_id: int,
    ) -> None:
        """Delete a timeline event by id."""
        stmt = select(VaultTimeline).where(VaultTimeline.id == event_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await db.delete(db_obj)
            await db.flush()

    # ---- Plot Promises ----

    async def get_plot_promises(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[VaultPlotPromise]:
        """List all plot promises for a project."""
        stmt = (
            select(VaultPlotPromise)
            .where(VaultPlotPromise.project_id == project_id)
            .order_by(VaultPlotPromise.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_plot_promise(
        self,
        db: AsyncSession,
        promise_id: int,
    ) -> VaultPlotPromise | None:
        """Get a single plot promise by id."""
        stmt = select(VaultPlotPromise).where(VaultPlotPromise.id == promise_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_plot_promise(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> VaultPlotPromise:
        """Create a new plot promise."""
        db_obj = VaultPlotPromise(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_plot_promise(
        self,
        db: AsyncSession,
        db_obj: VaultPlotPromise,
        obj_in: dict,
    ) -> VaultPlotPromise:
        """Update an existing plot promise."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_plot_promise(
        self,
        db: AsyncSession,
        promise_id: int,
    ) -> None:
        """Delete a plot promise by id."""
        stmt = select(VaultPlotPromise).where(VaultPlotPromise.id == promise_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await db.delete(db_obj)
            await db.flush()

    # ---- World ----

    async def get_world_entries(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[VaultWorld]:
        """List all world-building entries for a project."""
        stmt = (
            select(VaultWorld)
            .where(VaultWorld.project_id == project_id)
            .order_by(VaultWorld.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_world_entry(
        self,
        db: AsyncSession,
        entry_id: int,
    ) -> VaultWorld | None:
        """Get a single world entry by id."""
        stmt = select(VaultWorld).where(VaultWorld.id == entry_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_world_entry(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> VaultWorld:
        """Create a new world entry."""
        db_obj = VaultWorld(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_world_entry(
        self,
        db: AsyncSession,
        db_obj: VaultWorld,
        obj_in: dict,
    ) -> VaultWorld:
        """Update an existing world entry."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_world_entry(
        self,
        db: AsyncSession,
        entry_id: int,
    ) -> None:
        """Delete a world entry by id."""
        stmt = select(VaultWorld).where(VaultWorld.id == entry_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await db.delete(db_obj)
            await db.flush()

    # ---- Aggregation / Counts ----

    async def count_characters(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Count vault characters for a project."""
        stmt = (
            select(func.count())
            .select_from(VaultCharacter)
            .where(VaultCharacter.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    # ---- Batch by IDs ----

    async def get_characters_by_ids(
        self,
        db: AsyncSession,
        project_id: int,
        character_ids: list[int],
    ) -> list[VaultCharacter]:
        """Fetch characters by their IDs within a project."""
        if not character_ids:
            return []
        stmt = (
            select(VaultCharacter)
            .where(
                VaultCharacter.project_id == project_id,
                VaultCharacter.id.in_(character_ids),
            )
            .order_by(VaultCharacter.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_plot_promises_by_ids(
        self,
        db: AsyncSession,
        project_id: int,
        promise_ids: list[int],
    ) -> list[VaultPlotPromise]:
        """Fetch plot promises by their IDs within a project."""
        if not promise_ids:
            return []
        stmt = (
            select(VaultPlotPromise)
            .where(
                VaultPlotPromise.project_id == project_id,
                VaultPlotPromise.id.in_(promise_ids),
            )
            .order_by(VaultPlotPromise.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_world_entries_by_ids(
        self,
        db: AsyncSession,
        project_id: int,
        entry_ids: list[int],
    ) -> list[VaultWorld]:
        """Fetch world entries by their IDs within a project."""
        if not entry_ids:
            return []
        stmt = (
            select(VaultWorld)
            .where(
                VaultWorld.project_id == project_id,
                VaultWorld.id.in_(entry_ids),
            )
            .order_by(VaultWorld.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Lookup by name/term ----

    async def get_character_by_name(
        self,
        db: AsyncSession,
        project_id: int,
        name: str,
    ) -> VaultCharacter | None:
        """Find a character by name within a project."""
        stmt = select(VaultCharacter).where(
            VaultCharacter.project_id == project_id,
            VaultCharacter.name == name,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_world_entry_by_term(
        self,
        db: AsyncSession,
        project_id: int,
        term: str,
    ) -> VaultWorld | None:
        """Find a world entry by term within a project."""
        stmt = select(VaultWorld).where(
            VaultWorld.project_id == project_id,
            VaultWorld.term == term,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_timeline_events(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Count timeline events for a project."""
        stmt = (
            select(func.count())
            .select_from(VaultTimeline)
            .where(VaultTimeline.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def count_plot_promises(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Count plot promises for a project."""
        stmt = (
            select(func.count())
            .select_from(VaultPlotPromise)
            .where(VaultPlotPromise.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def count_world_entries(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Count world-building entries for a project."""
        stmt = (
            select(func.count())
            .select_from(VaultWorld)
            .where(VaultWorld.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def count_characters_by_status(
        self,
        db: AsyncSession,
        project_id: int,
        status: str,
    ) -> int:
        """Count vault characters filtered by status."""
        stmt = (
            select(func.count())
            .select_from(VaultCharacter)
            .where(
                VaultCharacter.project_id == project_id,
                VaultCharacter.status == status,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def count_plot_promises_by_status(
        self,
        db: AsyncSession,
        project_id: int,
        status: str,
    ) -> int:
        """Count plot promises filtered by status."""
        stmt = (
            select(func.count())
            .select_from(VaultPlotPromise)
            .where(
                VaultPlotPromise.project_id == project_id,
                VaultPlotPromise.status == status,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    # ---- Complex finders ----

    async def find_promise_by_description(
        self,
        db: AsyncSession,
        project_id: int,
        description_fragment: str,
    ) -> VaultPlotPromise | None:
        """Find a plot promise by partial description match (first 80 chars)."""
        stmt = select(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id,
            VaultPlotPromise.description.contains(description_fragment),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_promise_by_type_and_char(
        self,
        db: AsyncSession,
        project_id: int,
        promise_type: str,
        char_name: str,
        statuses: list[str],
    ) -> VaultPlotPromise | None:
        """Find a plot promise by type + related character + status filter."""
        stmt = select(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id,
            VaultPlotPromise.type == promise_type,
            VaultPlotPromise.related_characters.contains(char_name),
            VaultPlotPromise.status.in_(statuses),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
