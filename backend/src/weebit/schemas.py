from pydantic import BaseModel, Field

# RFC 9457 definition for the Swagger docs.
class ProblemDetailResponse(BaseModel):
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Short summary of the problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")