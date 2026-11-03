from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from weebit import exceptions
from weebit.exceptions import ProblemException, ErrorNotFoundProblem
from weebit import schemas
import inspect

error_router = APIRouter(prefix="/api/errors", tags=["Error Registry API"])

class ErrorMetadata(BaseModel):
    type_uri: str
    title: str
    status: int
    description: str

def get_registered_exceptions() -> list[type[ProblemException]]:
    """Dynamically find all classes inheriting from ProblemException."""
    # Ensure all modules defining exceptions are imported/inspected
    # inspect.getmembers filters for classes defined within the exceptions module
    exceptions_list = []
    for _, obj in inspect.getmembers(exceptions, inspect.isclass):
        if issubclass(obj, ProblemException) and obj is not ProblemException:
            exceptions_list.append(obj)
    return exceptions_list

@error_router.get(
    "",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "If there is some issue in resolving the errors for output.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema(),
                }
            }
        }
    },
    response_model=list[ErrorMetadata])
async def list_errors() -> list[ErrorMetadata]:
    """Returns all registered error metadata directly from the exception definitions."""
    try:
        return [
            ErrorMetadata(
                **exc.get_metadata()
            )
            for exc in get_registered_exceptions()
        ]
    except Exception:
        raise ProblemException(detail="Something went wrong with listing all of the errors at /api/errors")

@error_router.get(
    "/{error_slug}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Error definition not found",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema(),
                }
            }
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "If there is some issue in resolving the errors for output.",
            "content": {
                "application/problem+json": {
                    "schema": schemas.ProblemDetailResponse.model_json_schema(),
                }
            }
        }
    },
    response_model=ErrorMetadata)
async def get_error_detail(error_slug: str) -> ErrorMetadata:
    """
    Translates a request like GET /errors/invalid-url
    by matching the slug against the exception's type_uri.
    """
    try:
        for exc in get_registered_exceptions():
            if exc.type_uri.endswith(f"/{error_slug}"):
                return ErrorMetadata(
                    **exc.get_metadata()
                )

        raise ErrorNotFoundProblem
    except Exception:
        raise ProblemException(detail="fSomething went wrong with listing all the error at /api/errors/{error_slug}")