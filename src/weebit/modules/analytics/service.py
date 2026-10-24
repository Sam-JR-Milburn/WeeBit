from datetime import date, datetime, time, timezone

from aiocache import BaseCache
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from collections import defaultdict

from weebit.modules.analytics import schemas as analytics_schemas
from weebit.modules.analytics.schemas import LinkAnalyticsResponse
from weebit.modules.links import models as links_models

from weebit.exceptions import LinkNotFoundProblem

async def get_analytics(
    short_referrer_code: str,
    from_date: date,
    to_date: date,
    db: AsyncSession,
) -> analytics_schemas.LinkAnalyticsResponse:
    """
    Args:
        short_referrer_code:
        from_date:
        to_date:
        db:
    Returns:
        asdasdsa
    """

    # Verify the link object exists
    link_exists_stmt = select(links_models.Link.id).where(links_models.Link.short_ref_code == short_referrer_code)
    link_id = (await db.execute(link_exists_stmt)).scalar_one_or_none()

    if link_id is None:
        raise LinkNotFoundProblem(short_ref_code=short_referrer_code)

    # Needs to be timezone-aware (UTC) to be passed to the DB
    utc_start = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    utc_end = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

    # Filter by link id and slice a time period, then group by date and event type.
    query = (
        select(
            func.date(links_models.Analytic.timestamp).label("event_date"),
            links_models.Analytic.event_type,
            func.count().label("count")
        )
        .where(
            # Only the link implied by the short code
            links_models.Analytic.link_id == link_id,
            # Only those analytics before the end timestamp
            links_models.Analytic.timestamp <= utc_end
        )
    )

    # Add the from_date value to the query, if it exists
    if utc_start is not None:
        query = query.where(links_models.Analytic.timestamp >= utc_start)
    query = query.group_by(
        func.date(links_models.Analytic.timestamp),
        links_models.Analytic.event_type
    )

    result = await db.execute(query)
    rows = result.all()

    # Populate the response with ISO 8601 formatting
    creates_map = {}
    redirects_map = {}

    for event_date, event_type, count in rows:
        day_str = event_date.isoformat()
        if event_type == links_models.LinkEventType.CREATE:
            creates_map[day_str] = count
        elif event_type == links_models.LinkEventType.REDIRECT:
            redirects_map[day_str] = count

    return LinkAnalyticsResponse(
        short_ref_code=short_referrer_code,
        from_date=from_date,
        to_date=to_date,
        creates=dict(creates_map),
        redirects=dict(redirects_map),
    )