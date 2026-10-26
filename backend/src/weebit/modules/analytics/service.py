from datetime import date, datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func, case

from weebit.modules.analytics import schemas as analytics_schemas
from weebit.modules.analytics.schemas import LinkAnalyticsResponse
from weebit.modules.links import models as links_models

from weebit.exceptions import LinkNotFoundProblem
from weebit.modules.links.service import validate_short_code

async def get_analytics(
    short_referrer_code: str,
    from_date: date,
    to_date: date,
    db: AsyncSession
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

    validate_short_code(short_referrer_code)

    # Verify the link object exists
    link_exists_stmt = select(links_models.Link.id, links_models.Link.normalised_url).where(links_models.Link.short_ref_code == short_referrer_code)
    link_result = (await db.execute(link_exists_stmt)).first()

    if link_result is None:
        raise LinkNotFoundProblem(short_ref_code=short_referrer_code)
    link_id, normalised_url = link_result

    # Needs to be timezone-aware (UTC) to be passed to the DB
    utc_start = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    utc_end = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

    # Filter by link id and slice a time period, then group by date and event type.
    query = (
        select(
            func.date(links_models.Analytic.timestamp).label("event_date"),
            links_models.Analytic.event_type,
            func.count().label("count"),
            # Unique visitors by browser_fingerprint
            func.count(
                func.distinct(
                    case(
                        (links_models.Analytic.event_type == links_models.LinkEventType.REDIRECT,
                         links_models.Analytic.browser_fingerprint),
                        else_=None
                    )
                )
            ).label("unique_count")
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
    unique_visitors_map = {}

    for event_date, event_type, count, unique_visitors_count in rows:
        day_str = event_date.isoformat()
        if event_type == links_models.LinkEventType.CREATE:
            creates_map[day_str] = count
        elif event_type == links_models.LinkEventType.REDIRECT:
            redirects_map[day_str] = count

            # Only doing this for redirects as a create/recreate is a good proxy for unique visitor counts anyway
            unique_visitors_map[day_str] = unique_visitors_count

    return LinkAnalyticsResponse(
        short_ref_code=short_referrer_code,
        normalised_url=normalised_url,
        from_date=from_date,
        to_date=to_date,
        creates=dict(creates_map),
        redirects=dict(redirects_map),
        unique_visitors=dict(unique_visitors_map),
    )