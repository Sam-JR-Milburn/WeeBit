from typing import Any, Optional
from fastapi import status

#
#   RFC 9457: Problem Details for HTTP APIs
#

class ProblemException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    title: str = "Internal Server Error"
    type_uri: str = "about:blank"
    description: str = "An unexpected error occurred."

    def __init__(
        self,
        status_code: Optional[int] = None,
        title: Optional[str] = None,
        detail: str = "An unexpected error occurred.",
        type_uri: Optional[str] = None,
        extensions: Optional[dict[str, Any]] = None,
    ):
        self.status_code = status_code or self.status_code
        self.title = title or self.title
        self.detail = detail
        self.type_uri = type_uri or self.type_uri
        self.extensions = extensions or {}
        super().__init__(self.detail)

class InvalidUrlProblem(ProblemException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT
    title: str = "Unprocessable URL"
    type_uri: str = "/errors/invalid-url"
    description: str = "The URL failed validation checks."

    def __init__(self, detail: str):
        super().__init__(detail=detail)

class LinkNotFoundProblem(ProblemException):
    status_code: int = status.HTTP_404_NOT_FOUND
    title: str = "Link Not Found"
    type_uri: str = "/errors/link-not-found"
    description: str = "The short referrer code doesn't exist in the database."

    def __init__(self, short_ref_code: str):
        super().__init__(detail=f"The short reference code '{short_ref_code}' has not been registered in the system.")

class CollisionLimitProblem(ProblemException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    title: str = "Collision Limit Reached"
    type_uri: str = "/errors/collision-limit"
    description: str = "The system exhausted available short codes for this link."

    def __init__(self):
        super().__init__(detail="Short code collision limit reached. I am statistically improbable.")