"""Anonymous username generator."""
import re

from src.backend.utils.username import generate_anonymous_username


def test_generate_anonymous_username_format():
    name = generate_anonymous_username()
    assert re.match(r"^[a-z]+-[a-z]+-\d{3}$", name)
