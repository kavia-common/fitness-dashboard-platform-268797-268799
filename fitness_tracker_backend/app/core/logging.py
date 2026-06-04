from __future__ import annotations

import logging
import sys

from app.core.config import settings


# PUBLIC_INTERFACE
def configure_logging() -> None:
    """Configure application logging.

    Sets a simple stdout logger appropriate for container environments.
    """
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
