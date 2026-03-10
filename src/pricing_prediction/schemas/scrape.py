from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateScrapeRunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1)
    max_pages: int | None = Field(default=None, ge=1)
    source: str = "falabella_pe"

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must not be empty.")
        return value


class ListRunItemsQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
