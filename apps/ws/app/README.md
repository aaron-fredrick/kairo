"""
WebSocket Architecture

The WebSocket module provides real-time communication for the Kairo chat application.

Structure:
├── __init__.py
├── auth.py                      # JWT token extraction from query params
├── connection.py                # ConnectionManager for tracking active connections
├── manager.py                   # WebSocketManager coordinates all WS operations
├── routes.py                    # FastAPI WebSocket route handler
└── dependencies/
    ├── __init__.py
    ├── auth.py                  # (shared with API)
    ├── container.py             # Dependency injection container
    ├── db.py                    # Database session for WS
    ├── repositories.py          # Repository dependencies
    └── services.py              # Service dependencies
└── handlers/
    ├── __init__.py
    ├── connection_handler.py     # Handles connect/disconnect events
    ├── message_handler.py        # Handles incoming messages and events
    └── room_handler.py           # Handles room-specific broadcasts


Key Concepts:

1. Authentication:
   - Token passed as query parameter: ws://host/ws/rooms/{room_id}?token={jwt_token}
   - JWT decoded once on connection, user trusted thereafter
   - No password checks in WebSocket layer

2. Connection Management:
   - ConnectionManager maintains active connections grouped by room
   - Tracks (user_id, websocket) pairs per room
   - Automatic cleanup on disconnect

3. Event Types:
   - on_connect: User joins room
   - on_disconnect: User leaves room
   - on_message: User sends chat/typing/reaction event
   - Room broadcasts: All events routed through RoomHandler

4. Message Flow:
   Client -> WebSocket -> routes.py -> handlers -> ConnectionManager -> Broadcast

5. Repositories & Services:
   - Reuse API repositories (MessageRepository, UserRepository, RoomRepository)
   - Shared container for cache_manager and event_manager
   - Same database session management
