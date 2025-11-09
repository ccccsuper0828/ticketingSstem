from fastapi import APIRouter

from app.api.v1.endpoints import users, tickets, event, analytics, seats, dev, sessions


api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(event.router, prefix="/events", tags=["events"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(seats.router, prefix="/seats", tags=["seats"])
api_router.include_router(dev.router, prefix="/dev", tags=["dev"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


