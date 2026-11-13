"""Uvicorn entrypoint with graceful shutdown on SIGTERM/SIGINT."""

import asyncio
import signal
import sys

import uvicorn

from src.config.database import close_db, init_db
from src.config.redis_client import close_redis, init_redis
from src.config.settings import get_settings
from src.utils.logger import configure_logging, get_logger
from src.ws.ws_manager import org_connections

logger = get_logger(__name__)
_shutdown_started = False


async def _shutdown_cleanup() -> None:
    """Close WebSocket clients, Redis, and database pool."""
    for org_id, sockets in list(org_connections.items()):
        for ws in list(sockets):
            try:
                await ws.close(code=1001, reason="Server shutting down")
            except Exception as exc:
                logger.debug("ws_shutdown_close_failed", org_id=str(org_id), error=str(exc))
        org_connections.pop(org_id, None)
    await close_redis()
    await close_db()


def _handle_signal(server: uvicorn.Server) -> None:
    global _shutdown_started
    if _shutdown_started:
        logger.warning("forced_shutdown")
        sys.exit(1)
    _shutdown_started = True
    logger.info("shutdown_signal_received")
    server.should_exit = True


def main() -> None:
    configure_logging()
    settings = get_settings()
    config = uvicorn.Config(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        timeout_graceful_shutdown=30,
        log_level="info",
    )
    server = uvicorn.Server(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: _handle_signal(server))
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda *_args: _handle_signal(server))

    async def _run() -> None:
        await init_db()
        await init_redis()
        await server.serve()
        await _shutdown_cleanup()

    try:
        loop.run_until_complete(asyncio.wait_for(_run(), timeout=35))
        sys.exit(0)
    except TimeoutError:
        logger.error("shutdown_timeout")
        sys.exit(1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
