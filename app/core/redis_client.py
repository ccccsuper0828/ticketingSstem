from __future__ import annotations

import redis

from app.core.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    try:
        _client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            socket_timeout=3,
            socket_connect_timeout=3,
            health_check_interval=30,
        )
        # probe
        _client.ping()
        return _client
    except Exception:
        # Redis 不可用时返回 None，业务回退到 DB 原子更新
        _client = None
        return None


