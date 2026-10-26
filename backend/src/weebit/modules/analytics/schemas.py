from typing import Dict, Optional
from pydantic import BaseModel, Field

from datetime import date

class LinkAnalyticsResponse(BaseModel):
    short_ref_code: str
    normalised_url: str
    from_date: Optional[date] = None
    to_date: date
    creates: Dict[str, int] = Field(..., description="Dictionary of ISO 8601 dates to creation counts")
    redirects: Dict[str, int] = Field(..., description="Dictionary of ISO 8601 dates to redirection counts")
    unique_visitors: Dict[str, int] = Field(..., description="Dictionary of unique visitor counts")