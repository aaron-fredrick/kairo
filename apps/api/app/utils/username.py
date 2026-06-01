import random
import os
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

def load_words(file_path: str) -> list[str]:
    """Load words from a text file."""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}. Using fallbacks.")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        return words
    except Exception as e:
        logger.error(f"Error loading words from {file_path}", error=str(e))
        return []

def generate_username() -> str:
    """Generate a random anonymous username in adjective-noun format with a small numeric suffix."""
    adjectives = load_words(settings.ADJECTIVES_FILE)
    nouns = load_words(settings.NOUNS_FILE)
    
    # Fallbacks in case files are missing
    if not adjectives:
        adjectives = ["swift", "silent", "shadowy", "bright"]
    if not nouns:
        nouns = ["panda", "fox", "badger", "falcon"]

    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    suffix = random.randint(100, 999)
    return f"{adj}-{noun}-{suffix}"
