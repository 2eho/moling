"""墨灵 (Moling) — Vault DAO (unified access to all vault entity types).

Individual DAOs inherit ``BaseDAO`` for standard CRUD.  ``VaultDAO`` is a thin
facade that composes them, preserving the existing call-site API.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld


# =========================================================================
# Individual DAOs (inheriting BaseDAO)
# =========================================================================


class VaultCharacterDAO(BaseDAO[VaultCharacter]):
    """Data access for vault characters."""

    def __init__(self) -> None:
        super().__init__(VaultCharacter)

    # ---- Project-scoped queries ----

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> list[VaultCharacter]:
        """List all vault characters for a project."""
        return await self.get_multi(
            db, filters={"project_id": project_id}, limit=10_000,
            order_by="id", descending=False,
        )

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> int:
        return await self.count(db, filters={"project_id": project_id})

    async def count_by_status(
        self,
        db: AsyncSession,
        project_id: str,
        status: str,
    ) -> int:
        return await self.count(
            db, filters={"project_id": project_id, "status": status},
        )

    async def get_by_ids(
        self,
        db: AsyncSession,
        project_id: str,
        character_ids: list[str],
    ) -> list[VaultCharacter]:
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

    async def get_by_name(
        self,
        db: AsyncSession,
        project_id: str,
        name: str,
    ) -> VaultCharacter | None:
        stmt = select(VaultCharacter).where(
            VaultCharacter.project_id == project_id,
            VaultCharacter.name == name,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class VaultTimelineDAO(BaseDAO[VaultTimeline]):
    """Data access for vault timeline events."""

    def __init__(self) -> None:
        super().__init__(VaultTimeline)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> list[VaultTimeline]:
        stmt = (
            select(VaultTimeline)
            .where(VaultTimeline.project_id == project_id)
            .order_by(VaultTimeline.chapter_number.asc(), VaultTimeline.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> int:
        return await self.count(db, filters={"project_id": project_id})


class VaultPlotPromiseDAO(BaseDAO[VaultPlotPromise]):
    """Data access for vault plot promises."""

    def __init__(self) -> None:
        super().__init__(VaultPlotPromise)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> list[VaultPlotPromise]:
        return await self.get_multi(
            db, filters={"project_id": project_id}, limit=10_000,
            order_by="id", descending=False,
        )

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> int:
        return await self.count(db, filters={"project_id": project_id})

    async def count_by_status(
        self,
        db: AsyncSession,
        project_id: str,
        status: str,
    ) -> int:
        return await self.count(
            db, filters={"project_id": project_id, "status": status},
        )

    async def get_by_ids(
        self,
        db: AsyncSession,
        project_id: str,
        promise_ids: list[str],
    ) -> list[VaultPlotPromise]:
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

    async def find_by_description(
        self,
        db: AsyncSession,
        project_id: str,
        description_fragment: str,
    ) -> VaultPlotPromise | None:
        stmt = select(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id,
            VaultPlotPromise.description.contains(description_fragment),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_type_and_char(
        self,
        db: AsyncSession,
        project_id: str,
        promise_type: str,
        char_name: str,
        statuses: list[str],
    ) -> VaultPlotPromise | None:
        stmt = select(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id,
            VaultPlotPromise.type == promise_type,
            VaultPlotPromise.related_characters.contains(char_name),
            VaultPlotPromise.status.in_(statuses),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class VaultWorldDAO(BaseDAO[VaultWorld]):
    """Data access for vault world-building entries."""

    def __init__(self) -> None:
        super().__init__(VaultWorld)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> list[VaultWorld]:
        return await self.get_multi(
            db, filters={"project_id": project_id}, limit=10_000,
            order_by="id", descending=False,
        )

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> int:
        return await self.count(db, filters={"project_id": project_id})

    async def get_by_ids(
        self,
        db: AsyncSession,
        project_id: str,
        entry_ids: list[str],
    ) -> list[VaultWorld]:
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

    async def get_by_term(
        self,
        db: AsyncSession,
        project_id: str,
        term: str,
    ) -> VaultWorld | None:
        stmt = select(VaultWorld).where(
            VaultWorld.project_id == project_id,
            VaultWorld.name == term,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# =========================================================================
# Facade — backward-compatible VaultDAO
# =========================================================================


class VaultDAO:
    """Thin facade composing the four individual vault DAOs.

    All CRUD is delegated to the typed DAO instances.  Callers that used
    ``vault_dao.get_characters(...)`` see no breakage.
    """

    def __init__(self) -> None:
        self.characters = VaultCharacterDAO()
        self.timeline = VaultTimelineDAO()
        self.promises = VaultPlotPromiseDAO()
        self.world = VaultWorldDAO()

    # ---- Characters (delegated) ----

    async def get_characters(self, db: AsyncSession, project_id: str) -> list[VaultCharacter]:
        return await self.characters.get_by_project(db, project_id)

    async def get_character(self, db: AsyncSession, character_id: str) -> VaultCharacter | None:
        return await self.characters.get(db, character_id)

    async def create_character(self, db: AsyncSession, obj_in: dict) -> VaultCharacter:
        return await self.characters.create(db, obj_in)

    async def update_character(self, db: AsyncSession, db_obj: VaultCharacter, obj_in: dict) -> VaultCharacter:
        return await self.characters.update(db, db_obj, obj_in)

    async def delete_character(self, db: AsyncSession, character_id: str) -> None:
        await self.characters.delete(db, character_id)

    async def count_characters(self, db: AsyncSession, project_id: str) -> int:
        return await self.characters.count_by_project(db, project_id)

    async def get_characters_by_ids(self, db: AsyncSession, project_id: str, character_ids: list[str]) -> list[VaultCharacter]:
        return await self.characters.get_by_ids(db, project_id, character_ids)

    async def get_character_by_name(self, db: AsyncSession, project_id: str, name: str) -> VaultCharacter | None:
        return await self.characters.get_by_name(db, project_id, name)

    async def count_characters_by_status(self, db: AsyncSession, project_id: str, status: str) -> int:
        return await self.characters.count_by_status(db, project_id, status)

    # ---- Timeline (delegated) ----

    async def get_timeline(self, db: AsyncSession, project_id: str) -> list[VaultTimeline]:
        return await self.timeline.get_by_project(db, project_id)

    async def get_timeline_event(self, db: AsyncSession, event_id: str) -> VaultTimeline | None:
        return await self.timeline.get(db, event_id)

    async def create_timeline_event(self, db: AsyncSession, obj_in: dict) -> VaultTimeline:
        return await self.timeline.create(db, obj_in)

    async def update_timeline_event(self, db: AsyncSession, db_obj: VaultTimeline, obj_in: dict) -> VaultTimeline:
        return await self.timeline.update(db, db_obj, obj_in)

    async def delete_timeline_event(self, db: AsyncSession, event_id: str) -> None:
        await self.timeline.delete(db, event_id)

    async def count_timeline_events(self, db: AsyncSession, project_id: str) -> int:
        return await self.timeline.count_by_project(db, project_id)

    # ---- Plot Promises (delegated) ----

    async def get_plot_promises(self, db: AsyncSession, project_id: str) -> list[VaultPlotPromise]:
        return await self.promises.get_by_project(db, project_id)

    async def get_plot_promise(self, db: AsyncSession, promise_id: str) -> VaultPlotPromise | None:
        return await self.promises.get(db, promise_id)

    async def create_plot_promise(self, db: AsyncSession, obj_in: dict) -> VaultPlotPromise:
        return await self.promises.create(db, obj_in)

    async def update_plot_promise(self, db: AsyncSession, db_obj: VaultPlotPromise, obj_in: dict) -> VaultPlotPromise:
        return await self.promises.update(db, db_obj, obj_in)

    async def delete_plot_promise(self, db: AsyncSession, promise_id: str) -> None:
        await self.promises.delete(db, promise_id)

    async def count_plot_promises(self, db: AsyncSession, project_id: str) -> int:
        return await self.promises.count_by_project(db, project_id)

    async def get_plot_promises_by_ids(self, db: AsyncSession, project_id: str, promise_ids: list[str]) -> list[VaultPlotPromise]:
        return await self.promises.get_by_ids(db, project_id, promise_ids)

    async def count_plot_promises_by_status(self, db: AsyncSession, project_id: str, status: str) -> int:
        return await self.promises.count_by_status(db, project_id, status)

    async def find_promise_by_description(self, db: AsyncSession, project_id: str, description_fragment: str) -> VaultPlotPromise | None:
        return await self.promises.find_by_description(db, project_id, description_fragment)

    async def find_promise_by_type_and_char(self, db: AsyncSession, project_id: str, promise_type: str, char_name: str, statuses: list[str]) -> VaultPlotPromise | None:
        return await self.promises.find_by_type_and_char(db, project_id, promise_type, char_name, statuses)

    # ---- World (delegated) ----

    async def get_world_entries(self, db: AsyncSession, project_id: str) -> list[VaultWorld]:
        return await self.world.get_by_project(db, project_id)

    async def get_world_entry(self, db: AsyncSession, entry_id: str) -> VaultWorld | None:
        return await self.world.get(db, entry_id)

    async def create_world_entry(self, db: AsyncSession, obj_in: dict) -> VaultWorld:
        return await self.world.create(db, obj_in)

    async def update_world_entry(self, db: AsyncSession, db_obj: VaultWorld, obj_in: dict) -> VaultWorld:
        return await self.world.update(db, db_obj, obj_in)

    async def delete_world_entry(self, db: AsyncSession, entry_id: str) -> None:
        await self.world.delete(db, entry_id)

    async def count_world_entries(self, db: AsyncSession, project_id: str) -> int:
        return await self.world.count_by_project(db, project_id)

    async def get_world_entries_by_ids(self, db: AsyncSession, project_id: str, entry_ids: list[str]) -> list[VaultWorld]:
        return await self.world.get_by_ids(db, project_id, entry_ids)

    async def get_world_entry_by_term(self, db: AsyncSession, project_id: str, term: str) -> VaultWorld | None:
        return await self.world.get_by_term(db, project_id, term)
