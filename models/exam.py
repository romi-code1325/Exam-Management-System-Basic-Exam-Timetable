"""Exam model & CRUD data-access functions."""
from database import db_cursor


def create_exam(data: dict) -> dict:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO exams (subject, academic_year, section, exam_date,
                                start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["subject"],
                data["academic_year"],
                data["section"],
                data["exam_date"],
                data["start_time"],
                data["end_time"],
            ),
        )
        exam_id = cur.lastrowid
    return get_exam_by_id(exam_id)


def get_exam_by_id(exam_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def list_all_exams(include_cancelled: bool = True) -> list[dict]:
    query = "SELECT * FROM exams"
    if not include_cancelled:
        query += " WHERE is_cancelled = 0"
    query += " ORDER BY exam_date, start_time"
    with db_cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def list_exams_for_year_section(
    academic_year: str, section: str, include_cancelled: bool = False
) -> list[dict]:
    """
    The single source of truth for the "students only see their own
    year/section" rule (student.year === exam.year && student.section ===
    exam.section). Filtering happens here, in SQL, driven only by values
    taken from the authenticated student's own profile -- never from
    client-supplied query parameters -- so a student cannot manipulate
    request parameters to view another section's exams.
    """
    query = (
        "SELECT * FROM exams WHERE academic_year = ? AND section = ?"
    )
    params = [academic_year, section]
    if not include_cancelled:
        query += " AND is_cancelled = 0"
    query += " ORDER BY exam_date, start_time"
    with db_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_exam(exam_id: int, data: dict) -> dict | None:
    existing = get_exam_by_id(exam_id)
    if existing is None:
        return None

    merged = {**existing, **data}
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE exams
               SET subject = ?, academic_year = ?, section = ?,
                   exam_date = ?, start_time = ?, end_time = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (
                merged["subject"],
                merged["academic_year"],
                merged["section"],
                merged["exam_date"],
                merged["start_time"],
                merged["end_time"],
                exam_id,
            ),
        )
    return get_exam_by_id(exam_id)


def cancel_exam(exam_id: int) -> dict | None:
    """Soft-delete: mark as cancelled rather than physically deleting,
    matching the spec's wording of 'cancel' exam records."""
    existing = get_exam_by_id(exam_id)
    if existing is None:
        return None
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE exams SET is_cancelled = 1, updated_at = datetime('now') "
            "WHERE id = ?",
            (exam_id,),
        )
    return get_exam_by_id(exam_id)


def delete_exam(exam_id: int) -> bool:
    """Hard delete, exposed separately from cancel for admins who want it."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        return cur.rowcount > 0
