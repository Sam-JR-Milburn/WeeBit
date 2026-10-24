from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from weebit import exceptions

error_router = APIRouter(prefix="/api/errors", tags=["Error Registry API"])

class ErrorMetadata(BaseModel):
    type_uri: str
    title: str
    status: int
    description: str

# Keep track of all exceptions here for the error documentation registry.
REGISTERED_EXCEPTIONS = [
    exceptions.InvalidUrlProblem,
    exceptions.InvalidShortCodeProblem,
    exceptions.LinkNotFoundProblem,
    exceptions.CollisionLimitProblem,
    exceptions.InvalidDateProblem
]

@error_router.get("", response_model=list[ErrorMetadata])
async def list_errors() -> list[ErrorMetadata]:
    """Returns all registered error metadata directly from the exception definitions."""

    return [
        ErrorMetadata(
            type_uri=exc.type_uri,
            title=exc.title,
            status=exc.status_code,
            description=exc.description,
        )
        for exc in REGISTERED_EXCEPTIONS
    ]

@error_router.get("/{error_slug}", response_model=ErrorMetadata)
async def get_error_detail(error_slug: str) -> ErrorMetadata:
    """
    Translates a request like GET /errors/invalid-url
    by matching the slug against the exception's type_uri.
    """
    for exc in REGISTERED_EXCEPTIONS:
        if exc.type_uri.endswith(f"/{error_slug}"):
            return ErrorMetadata(
                type_uri=exc.type_uri,
                title=exc.title,
                status=exc.status_code,
                description=exc.description,
            )

    raise HTTPException(status_code=404, detail="Error definition not found")