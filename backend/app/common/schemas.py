"""Shared Pydantic schema pieces: pagination envelope (D-021)."""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class Page(BaseModel, Generic[T]):
    data: list[T]
    meta: PageMeta


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 25


def paginate_meta(page: int, page_size: int, total_items: int) -> PageMeta:
    total_pages = (total_items + page_size - 1) // page_size if page_size else 0
    return PageMeta(
        page=page, page_size=page_size, total_items=total_items, total_pages=max(total_pages, 0)
    )
