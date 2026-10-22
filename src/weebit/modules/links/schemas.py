from pydantic import BaseModel, HttpUrl, Field, ConfigDict, field_validator
from urllib.parse import urlparse

class LinkCreate(BaseModel):
    url: HttpUrl = Field(..., description="The link submission for normalisation and shortening")

    @field_validator("url", mode="before")
    @classmethod
    def ensure_url_scheme(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
            parsed = urlparse(value)

            # prepend https://
            if not parsed.scheme:
                return f"https://{value}"
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": 'https://example.com/link',
            }
        }
    )

class LinkResponse(BaseModel):
    short_ref_code: str
    normalised_url: str

    model_config = ConfigDict(from_attributes = True)

# RFC 9457 definition for the Swagger docs.
class ProblemDetailResponse(BaseModel):
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Short summary of the problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")