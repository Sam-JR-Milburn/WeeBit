from datetime import date
from fastapi import APIRouter, Depends, Request, Response, status, BackgroundTasks, Query

from weebit.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from weebit.exceptions import InvalidDateProblem
from weebit.modules.analytics import schemas as analytics_schemas, service
from weebit import schemas as main_schemas

analytics_api_router = APIRouter(prefix="/api/analytics", tags=["Link Analytics API"])

@analytics_api_router.get(
    path="/{short_referrer_code}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Yields link analytics JSON if the SRC is valid and if dates are provided, so are the dates",
            "content": {
                "application/json": {
                    "schema": analytics_schemas.LinkAnalyticsResponse.model_json_schema()
                }
            }
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Yield an error if the SRC is not valid",
            "content": {
                "application/problem+json": {
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Yield an error if the SRC or the from_date/to_date have invalid form",
            "content": {
                "application/problem+json": {
                    "schema": main_schemas.ProblemDetailResponse.model_json_schema()
                }
            }
        }
    }
)
async def get_analytics(
    short_referrer_code: str,
    from_date: date = Query(default=None, description="Inclusive start date (YYYY-MM-DD) for the link statistics"),
    to_date: date = Query(default_factory=date.today, description="Inclusive end date (YYYY-MM-DD) for the link statistics"),
    db: AsyncSession = Depends(get_db)
) -> analytics_schemas.LinkAnalyticsResponse:
    """
    Args:
        short_referrer_code: A shortened string representing a stored URL.
        from_date: An ISO 8601 (YYYY-MM-DD) inclusive lower bound.
        to_date: An ISO 8601 (YYYY-MM-DD) inclusive upper bound.
        db: Injected database session.
    Returns:
        A LinkAnalyticsResponse object containing statistics for a link/short code pair.
    """

    min_date = date(2000, 1, 1)
    today = date.today()

    # Validate date queries
    if from_date:
        if from_date < min_date:
            raise InvalidDateProblem(detail=f"Analytics data is only available for dates after {str(min_date)}")
        if from_date > to_date:
            raise InvalidDateProblem(detail="The 'from_date' value can't be later than the 'to_date' value")
        if from_date > today:
            raise InvalidDateProblem(detail="The 'from_date' value can't be in the future")

    # Simply clamp all future dates to today.
    if to_date > today:
        to_date = today

    # Return the analytics.
    return await service.get_analytics(
        short_referrer_code=short_referrer_code,
        from_date=from_date,
        to_date=to_date,
        db=db,
    )