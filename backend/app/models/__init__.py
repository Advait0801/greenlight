"""Database tables (PROJECT_CONTEXT section 5). Importing this package registers them all.

Money is stored as whole cents (integers), never as floats.
Traveller details (names, dates of birth, IDs) are never stored: the money check only
confirms that the fields are present (PROJECT_CONTEXT section 9).
"""

from app.models.audit import AuditLog
from app.models.clubs import Club, User
from app.models.documents import Document, LineItem
from app.models.findings import Finding, FundingOption
from app.models.plans import Event, Obligation, YearPlan
from app.models.rules import RuleVersion

__all__ = [
    "AuditLog",
    "Club",
    "Document",
    "Event",
    "Finding",
    "FundingOption",
    "LineItem",
    "Obligation",
    "RuleVersion",
    "User",
    "YearPlan",
]
