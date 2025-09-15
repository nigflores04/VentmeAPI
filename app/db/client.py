from __future__ import annotations

from typing import Optional

# Singleton Prisma client reference (initialized on demand)
prisma: Optional[object] = None


async def connect() -> None:
    global prisma
    if prisma is None:
        # Lazy import so app can start even if prisma client is not yet generated/installed
        from prisma import Prisma  # type: ignore

        prisma = Prisma()
    if not prisma.is_connected():  # type: ignore[attr-defined]
        await prisma.connect()  # type: ignore[func-returns-value]


async def disconnect() -> None:
    global prisma
    if prisma is not None and prisma.is_connected():  # type: ignore[attr-defined]
        await prisma.disconnect()  # type: ignore[func-returns-value]


async def get_db():
    """FastAPI dependency to get database connection"""
    await connect()
    return prisma
