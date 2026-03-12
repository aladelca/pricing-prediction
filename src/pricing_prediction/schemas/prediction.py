from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AvailabilityPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    homeDeliveryShipping: str | None = None
    pickUpFromStoreShipping: str | None = None
    internationalShipping: str | None = None
    primeShipping: str | None = None
    expressShipping: str | None = None


class PredictCurrentPriceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    position: int = Field(ge=1)
    title: str = Field(min_length=1)
    brand: str | None = None
    seller: str | None = None
    seller_id: str | None = None
    source_domain: str = "www.falabella.com.pe"
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    sponsored: bool = False
    gsc_category_id: str | None = None
    provider_name: str | None = None
    availability: AvailabilityPayload = Field(default_factory=AvailabilityPayload)
    image_urls: list[str] = Field(default_factory=list)
    is_best_seller: bool = False
    is_frequent_product: bool = False
    multipurpose_badges_count: int = Field(default=0, ge=0)

    @field_validator("query", "title")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be empty.")
        return value


class PredictCurrentPriceResponse(BaseModel):
    predicted_current_price: float
    currency: str = "PEN"
    model_name: str
    model_version: str
    target: str = "current_price"
    features_version: str
    warnings: list[str] = Field(default_factory=list)
