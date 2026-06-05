from app.domain.models.message_domain import MessageDomain


class MessagePolicy:
    """
    Authorization rules for message access.
    Pure business logic — no DB, no Redis, no FastAPI.
    """

    def can_access(self, message: MessageDomain, user_id: int, is_member: bool) -> bool:
        return is_member and message.room_id is not None
