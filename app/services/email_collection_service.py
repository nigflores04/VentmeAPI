from typing import List, Optional
from prisma import Prisma
from app.models.email_schemas import (
    EmailSubscribeRequest, 
    EmailSubscriberPublic,
    EmailListResponse
)


class EmailCollectionService:
    def __init__(self, db: Prisma):
        self.db = db

    async def subscribe_email(self, subscribe_data: EmailSubscribeRequest) -> Optional[EmailSubscriberPublic]:
        """Add an email to the collection"""
        try:
            # Check if email already exists
            existing = await self.db.emailsubscriber.find_unique(
                where={"email": subscribe_data.email}
            )
            
            if existing:
                if existing.isActive:
                    # Already subscribed and active
                    return EmailSubscriberPublic(
                        id=existing.id,
                        email=existing.email,
                        name=existing.name,
                        source=existing.source,
                        isActive=existing.isActive,
                        createdAt=existing.createdAt
                    )
                else:
                    # Reactivate existing subscription
                    updated = await self.db.emailsubscriber.update(
                        where={"id": existing.id},
                        data={"isActive": True}
                    )
                    return EmailSubscriberPublic(
                        id=updated.id,
                        email=updated.email,
                        name=updated.name,
                        source=updated.source,
                        isActive=updated.isActive,
                        createdAt=updated.createdAt
                    )
            
            # Create new subscription
            subscriber = await self.db.emailsubscriber.create(
                data={
                    "email": subscribe_data.email,
                    "name": subscribe_data.name,
                    "source": subscribe_data.source or "api"
                }
            )
            
            return EmailSubscriberPublic(
                id=subscriber.id,
                email=subscriber.email,
                name=subscriber.name,
                source=subscriber.source,
                isActive=subscriber.isActive,
                createdAt=subscriber.createdAt
            )
            
        except Exception:
            return None

    async def get_subscribers(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> EmailListResponse:
        """Get all email subscribers"""
        where_clause = {"isActive": True} if active_only else {}
        
        subscribers = await self.db.emailsubscriber.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"createdAt": "desc"}
        )
        
        total = await self.db.emailsubscriber.count(where=where_clause)
        
        subscriber_list = [
            EmailSubscriberPublic(
                id=sub.id,
                email=sub.email,
                name=sub.name,
                source=sub.source,
                isActive=sub.isActive,
                createdAt=sub.createdAt
            )
            for sub in subscribers
        ]
        
        return EmailListResponse(
            total=total,
            subscribers=subscriber_list
        )

    async def unsubscribe_email(self, email: str) -> bool:
        """Deactivate an email subscription"""
        try:
            await self.db.emailsubscriber.update(
                where={"email": email},
                data={"isActive": False}
            )
            return True
        except:
            return False

    async def get_subscriber_count(self) -> dict:
        """Get simple statistics"""
        total = await self.db.emailsubscriber.count()
        active = await self.db.emailsubscriber.count(where={"isActive": True})
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active
        }
