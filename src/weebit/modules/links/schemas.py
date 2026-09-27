from pydantic import BaseModel, HttpUrl, Field, ConfigDict

class LinkCreate(BaseModel):
    url: HttpUrl = Field(..., description="The link submission for normalisation and shortening")

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