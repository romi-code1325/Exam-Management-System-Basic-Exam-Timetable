"""Student profile and filtered timetable routes."""
from flask import Blueprint, g, jsonify, request

from auth import require_auth
from models.exam import list_exams_for_year_section
from models.student import get_student_by_id, public_profile

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


@student_bp.get("/me")
@require_auth("student")
def get_profile():
    student = get_student_by_id(int(g.current_user["sub"]))
    if not student:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(public_profile(student))


@student_bp.get("/timetable")
@require_auth("student")
def get_timetable():
    """
    Returns only exams matching the *authenticated* student's own
    academic_year and section, taken from their JWT/profile -- never
    from client-supplied query parameters. Any ?academic_year=... or
    ?section=... query params sent by the client are deliberately
    ignored, which is what stops a student from manipulating API
    parameters to view another section's exams.
    """
    student = get_student_by_id(int(g.current_user["sub"]))
    if not student:
        return jsonify({"error": "Student not found."}), 404

    academic_year = student.get("academic_year")
    section = student.get("section")
    if not academic_year or not section:
        # Edge case: student profile missing academic year or section.
        return jsonify({
            "error": "Your profile is missing academic_year or section. "
                     "Contact an administrator."
        }), 422

    exams = list_exams_for_year_section(academic_year, section)
    # Edge case: querying when no exams exist for a particular section
    # simply returns an empty list with count 0, not an error.
    return jsonify({
        "academic_year": academic_year,
        "section": section,
        "exams": exams,
        "count": len(exams),
    })
