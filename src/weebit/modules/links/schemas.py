from pydantic import BaseModel, HttpUrl, Field, ConfigDict, field_validator


class LinkCreate(BaseModel):
    url: HttpUrl = Field(..., description="The link submission for normalisation and shortening")

    @field_validator("url", mode="before")
    @classmethod
    def ensure_url_scheme(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
            # prepend https://
            if not (value.startswith("http://") or value.startswith("https://")):
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