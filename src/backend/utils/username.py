import random

ADJECTIVES = [
    "swift", "silent", "shadowy", "bright", "cozy", "clever", "wild", "gentle",
    "brave", "calm", "eager", "fierce", "jolly", "lively", "proud", "witty",
    "crimson", "emerald", "azure", "golden", "silver", "dusty", "frosty", "misty"
]

NOUNS = [
    "panda", "fox", "badger", "falcon", "otter", "koala", "lynx", "owl",
    "rabbit", "turtle", "dolphin", "wolf", "tiger", "bear", "deer", "eagle",
    "sparrow", "raccoon", "hedgehog", "squirrel", "panther", "cobra", "gecko", "bison"
]

def generate_anonymous_username() -> str:
    """Generate a random anonymous username in adjective-noun format with a small numeric suffix."""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    suffix = random.randint(100, 999)
    return f"{adj}-{noun}-{suffix}"
