from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CENTRAL_TEAM = "CENTRAL_TEAM"
    PROCESS_OWNER = "PROCESS_OWNER"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


class Region(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    CENTRAL = "CENTRAL"


class AuditSegment(str, Enum):
    BRANCH_AUDIT = "BRANCH_AUDIT"
    SHARIAH = "SHARIAH"
    MANAGEMENT = "MANAGEMENT"
    OTHER = "OTHER"


class ObservationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class ObservationSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResponseType(str, Enum):
    RESOLVED = "RESOLVED"
    NEED_MORE_TIME = "NEED_MORE_TIME"
    COMMITTED_TIMELINE = "COMMITTED_TIMELINE"
