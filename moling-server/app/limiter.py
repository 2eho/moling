"""Shared slowapi Limiter instance — avoids circular imports.

Import from here rather than ``app.main`` so router modules
can decorate endpoints without pulling in the FastAPI app.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
