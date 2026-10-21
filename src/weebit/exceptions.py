from typing import Any, Optional
from fastapi import status

#
#   RFC 9457: Problem Details for HTTP APIs
#

class ProblemException(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        type_uri: str = "about:blank",
        extensions: Optional[dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri
        self.extensions = extensions or {}
        super().__init__(detail)

class InvalidUrlProblem(ProblemException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Unprocessable URL",
            detail=detail,
            type_uri="/errors/invalid-url",
        )

class LinkNotFoundProblem(ProblemException):
    def __init__(self, short_ref_code: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Link Not Found",
            detail=f"The short reference code '{short_ref_code}' has not been registered in the system.",
            type_uri="/errors/not-found",
        )

class CollisionLimitProblem(ProblemException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Collision Limit Reached",
            detail="Short code collision limit reached. I am statistically improbable.",
            type_uri="/errors/collision-limit",
        )