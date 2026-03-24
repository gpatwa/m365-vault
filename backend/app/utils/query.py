"""Shared query utilities for server-side pagination, sorting, and filtering.

Used by all list API endpoints to ensure consistent behavior at scale.
"""
from fastapi import Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query as SAQuery


def apply_sorting(stmt, model, sort_by: str = None, sort_order: str = "desc"):
    """Apply server-side sorting to a SQLAlchemy statement."""
    if sort_by and hasattr(model, sort_by):
        col = getattr(model, sort_by)
        stmt = stmt.order_by(desc(col) if sort_order == "desc" else asc(col))
    return stmt


def apply_pagination(stmt, page: int, page_size: int):
    """Apply offset/limit pagination."""
    return stmt.offset((page - 1) * page_size).limit(page_size)


# Common query parameters as FastAPI dependencies
class ListParams:
    """Standard list query parameters for all data table endpoints."""
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=100),
        sort_by: str = Query(None),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        search: str = Query(None),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.search = search
