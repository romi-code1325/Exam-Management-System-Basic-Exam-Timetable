"""
Validation & error-handling helpers.

Centralizes every business rule from the spec so both the exam CRUD routes
and any future callers apply identical checks:
  - subject / academic_year / section / exam_date / start_time / end_time
    are all mandatory
  - end_time must be strictly after start_time
  - dates and times must be well-formed
"""
from datetime import datetime


class ValidationError(Exception):
    """Raised when incoming data fails a business rule; carries field errors."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


REQUIRED_EXAM_FIELDS = [
    "subject",
    "academic_year",
    "section",
    "exam_date",
    "start_time",
    "end_time",
]


def _parse_time(value: str):
    return datetime.strptime(value, "%H:%M")


def validate_exam_payload(data: dict, partial: bool = False) -> dict:
    """
    Validate an incoming exam create/update payload.

    partial=True allows PATCH-style updates where only some fields are
    present; each field that *is* present is still fully validated.
    Returns a cleaned dict of the fields that were present and valid.
    Raises ValidationError with a dict of field -> message on failure.
    """
    errors: dict = {}
    cleaned: dict = {}

    for field in REQUIRED_EXAM_FIELDS:
        if field in data:
            value = data.get(field)
            if value is None or str(value).strip() == "":
                errors[field] = f"{field} cannot be empty."
            else:
                cleaned[field] = str(value).strip()
        elif not partial:
            errors[field] = f"{field} is required."

    if "exam_date" in cleaned:
        try:
            datetime.strptime(cleaned["exam_date"], "%Y-%m-%d")
        except ValueError:
            errors["exam_date"] = "exam_date must be in YYYY-MM-DD format."

    start = cleaned.get("start_time")
    end = cleaned.get("end_time")

    if start is not None:
        try:
            _parse_time(start)
        except ValueError:
            errors["start_time"] = "start_time must be in HH:MM (24h) format."

    if end is not None:
        try:
            _parse_time(end)
        except ValueError:
            errors["end_time"] = "end_time must be in HH:MM (24h) format."

    # Only compare ordering if both times are present in *this* payload and
    # both parsed successfully. For partial updates where only one of the
    # two times changes, the route layer re-validates against the merged
    # (existing + new) record -- see exams.py.
    if (
        start is not None
        and end is not None
        and "start_time" not in errors
        and "end_time" not in errors
    ):
        if _parse_time(end) <= _parse_time(start):
            errors["end_time"] = "end_time must be strictly after start_time."

    if errors:
        raise ValidationError(errors)

    return cleaned


def validate_time_order(start_time: str, end_time: str) -> None:
    """Standalone check used after merging partial updates with existing data."""
    if _parse_time(end_time) <= _parse_time(start_time):
        raise ValidationError(
            {"end_time": "end_time must be strictly after start_time."}
        )
