from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionFieldEntry:
    form_name: str
    api_field: str
    label: str
    group: str
    required: bool
    definition: str
    example: str
    notes: tuple[str, ...] = ()

    @property
    def anchor_id(self) -> str:
        return self.form_name.replace("_", "-")

    @property
    def search_text(self) -> str:
        parts = (
            self.form_name,
            self.api_field,
            self.label,
            self.group,
            self.definition,
            self.example,
            *self.notes,
        )
        return " ".join(parts).lower()


PREDICTION_FIELD_GLOSSARY: tuple[PredictionFieldEntry, ...] = (
    PredictionFieldEntry(
        form_name="query",
        api_field="query",
        label="Search query",
        group="Required inputs",
        required=True,
        definition="The marketplace search phrase that produced the listing you want to estimate.",
        example="ropa mujer",
        notes=(
            "Use the same wording a shopper would type in the marketplace.",
            "This is one of the strongest context fields for the model.",
        ),
    ),
    PredictionFieldEntry(
        form_name="page_number",
        api_field="page_number",
        label="Page number",
        group="Required inputs",
        required=True,
        definition="The result page where the product appeared in the marketplace listing.",
        example="1",
        notes=("Use 1 for the first results page.",),
    ),
    PredictionFieldEntry(
        form_name="position",
        api_field="position",
        label="Position inside page",
        group="Required inputs",
        required=True,
        definition="The ranking position of the product card within the selected results page.",
        example="4",
        notes=(
            "The form expects a one-based position, not zero-based indexing.",
            "Combine it with page number to reproduce listing rank accurately.",
        ),
    ),
    PredictionFieldEntry(
        form_name="title",
        api_field="title",
        label="Product title",
        group="Required inputs",
        required=True,
        definition="The exact product title shown in the listing or as close as possible.",
        example="Polera mujer sport essentials",
        notes=("Keep brand words, variants, and pack signals when they appear in the title.",),
    ),
    PredictionFieldEntry(
        form_name="brand",
        api_field="brand",
        label="Brand",
        group="Marketplace context",
        required=False,
        definition="The product brand associated with the listing.",
        example="Adidas",
        notes=("Leave empty if unknown; the backend will fall back to a generic value.",),
    ),
    PredictionFieldEntry(
        form_name="seller",
        api_field="seller",
        label="Seller name",
        group="Marketplace context",
        required=False,
        definition="The seller or merchant displayed in the marketplace card.",
        example="Falabella",
    ),
    PredictionFieldEntry(
        form_name="seller_id",
        api_field="seller_id",
        label="Seller ID",
        group="Marketplace context",
        required=False,
        definition="The marketplace seller identifier if the payload or listing exposes one.",
        example="seller-1",
    ),
    PredictionFieldEntry(
        form_name="source_domain",
        api_field="source_domain",
        label="Source domain",
        group="Marketplace context",
        required=False,
        definition="The domain where the listing was collected.",
        example="www.falabella.com.pe",
        notes=("Keep the default unless your data comes from another supported source.",),
    ),
    PredictionFieldEntry(
        form_name="rating",
        api_field="rating",
        label="Rating",
        group="Marketplace context",
        required=False,
        definition="The average star rating shown for the product.",
        example="4.7",
        notes=("Valid values are between 0 and 5.",),
    ),
    PredictionFieldEntry(
        form_name="review_count",
        api_field="review_count",
        label="Review count",
        group="Marketplace context",
        required=False,
        definition="The number of user reviews displayed next to the rating.",
        example="44",
    ),
    PredictionFieldEntry(
        form_name="gsc_category_id",
        api_field="gsc_category_id",
        label="Category ID",
        group="Marketplace context",
        required=False,
        definition="The marketplace category identifier extracted from the raw listing payload.",
        example="G08020208",
    ),
    PredictionFieldEntry(
        form_name="provider_name",
        api_field="provider_name",
        label="Provider name",
        group="Marketplace context",
        required=False,
        definition="The provider or backend source name stored in the marketplace payload.",
        example="falabella",
    ),
    PredictionFieldEntry(
        form_name="multipurpose_badges_count",
        api_field="multipurpose_badges_count",
        label="Badge count",
        group="Marketplace context",
        required=False,
        definition="How many marketplace badges or promotional labels the product card shows.",
        example="2",
    ),
    PredictionFieldEntry(
        form_name="sponsored",
        api_field="sponsored",
        label="Sponsored flag",
        group="Flags and availability",
        required=False,
        definition="Whether the listing is marked as sponsored or promoted by the marketplace.",
        example="checked",
    ),
    PredictionFieldEntry(
        form_name="is_best_seller",
        api_field="is_best_seller",
        label="Best seller flag",
        group="Flags and availability",
        required=False,
        definition="Whether the raw payload marks the product as a best seller.",
        example="checked",
    ),
    PredictionFieldEntry(
        form_name="is_frequent_product",
        api_field="is_frequent_product",
        label="Frequent product flag",
        group="Flags and availability",
        required=False,
        definition=(
            "Whether the marketplace payload marks the listing as a frequently bought "
            "or frequent product."
        ),
        example="unchecked",
    ),
    PredictionFieldEntry(
        form_name="international_shipping",
        api_field="availability.internationalShipping",
        label="International shipping",
        group="Flags and availability",
        required=False,
        definition="Whether the product can be shipped internationally.",
        example="checked",
        notes=("This UI checkbox maps to the nested availability payload used by the API.",),
    ),
    PredictionFieldEntry(
        form_name="image_urls_text",
        api_field="image_urls",
        label="Image URLs",
        group="Image inputs",
        required=False,
        definition="One image URL per line for the product images associated with the listing.",
        example="https://images.example/item-1\nhttps://images.example/item-2",
        notes=(
            "Prefer real marketplace image URLs when you have them.",
            "The current model uses image metadata such as count and namespace, not pixel content.",
        ),
    ),
    PredictionFieldEntry(
        form_name="image_files",
        api_field="image_urls",
        label="Local image uploads",
        group="Image inputs",
        required=False,
        definition=(
            "Optional local image files uploaded from your machine to complement the request."
        ),
        example="look-1.png, look-2.webp",
        notes=(
            "Uploaded files are converted to placeholder references for the current model.",
            "They help the workflow, but they do not trigger visual inference in this version.",
        ),
    ),
)
