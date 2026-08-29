"""Shared FastAPI dependencies.

This build has NO authentication — there is intentionally no
`get_current_user` dependency here. Routers should only depend on `get_db`.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

# Using Annotated (rather than `db: Session = Depends(get_db)` in every route
# signature) keeps ruff's B008 (function-call-in-default-argument) happy and
# is the FastAPI-recommended style since 0.95.
DbSession = Annotated[Session, Depends(get_db)]

__all__ = ["DbSession", "get_db"]
