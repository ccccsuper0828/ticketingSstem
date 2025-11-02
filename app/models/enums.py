from enum import Enum


class UserRole(str, Enum):
    customer = "customer"
    admin = "admin"


class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"


class SeatStatus(str, Enum):
    available = "available"
    locked = "locked"
    sold = "sold"
    disabled = "disabled"


class TicketStatus(str, Enum):
    pending = "pending"
    active = "active"
    used = "used"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentMethod(str, Enum):
    credit = "credit"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class RefundStatus(str, Enum):
    requested = "requested"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


