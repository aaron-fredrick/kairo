from app.api.dependencies.container import get_container
from app.container import AppContainer


def get_container_ws() -> AppContainer:
    """WebSocket dependency for application container."""
    return get_container()
