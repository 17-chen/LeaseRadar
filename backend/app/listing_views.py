"""Read-only workbench views over already-authorized listing search results."""
from datetime import datetime, timedelta, timezone

from .domain import aware_time

TERMINAL_STATES = {'closed', 'failed', 'sold', 'withdrawn'}


def in_quick_view(row: dict, view: str, at: datetime | None = None) -> bool:
    """Keep quick views separate from saved subscription rules."""
    at = at or datetime.now(timezone.utc)
    if view == 'all':
        return True
    if view == 'recent':
        created = aware_time(row.get('created_at'))
        return created is not None and at - timedelta(days=7) <= created <= at
    if view == 'deadline':
        cutoff = aware_time(row.get('registration_deadline'))
        return (row.get('status') not in TERMINAL_STATES and cutoff is not None
                and at < cutoff <= at + timedelta(days=7))
    if view == 'review':
        cutoff = aware_time(row.get('registration_deadline'))
        if row.get('status') in TERMINAL_STATES or (cutoff is not None and cutoff <= at):
            return False
        return (row.get('match', {}).get('verdict') == 'unknown'
                or bool(row.get('review_conflicts') or row.get('source_conflicts'))
                or row.get('status') in (None, '', 'unknown')
                or row.get('area_m2') is None
                or row.get('registration_deadline') is None
                or row.get('raw_amount') is None
                or row.get('period_basis') not in ('first_year', 'monthly'))
    raise ValueError('未知快捷视图')
