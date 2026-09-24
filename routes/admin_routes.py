"""Admin exam timetable management routes (create/view/edit/cancel)."""
from flask import Blueprint, jsonify, request

from auth import require_auth
from models.exam import (
    cancel_exam,
    create_exam,
    delete_exam,
    get_exam_by_id,
    list_all_exams,
    update_exam,
)
from validators import ValidationError, validate_exam_payload, validate_time_order

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin/exams")


@admin_bp.post("")
@require_auth("admin")
def create_exam_route():
    body = request.get_json(silent=True) or {}
    try:
        cleaned = validate_exam_payload(body, partial=False)
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400

    exam = create_exam(cleaned)
    return jsonify(exam), 201


@admin_bp.get("")
@require_auth("admin")
def list_exams_route():
    include_cancelled = request.args.get("include_cancelled", "true").lower() != "false"
    exams = list_all_exams(include_cancelled=include_cancelled)
    return jsonify({"exams": exams, "count": len(exams)})


@admin_bp.get("/<int:exam_id>")
@require_auth("admin")
def get_exam_route(exam_id: int):
    exam = get_exam_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found."}), 404
    return jsonify(exam)


@admin_bp.put("/<int:exam_id>")
@require_auth("admin")
def update_exam_route(exam_id: int):
    existing = get_exam_by_id(exam_id)
    if not existing:
        return jsonify({"error": "Exam not found."}), 404

    body = request.get_json(silent=True) or {}
    try:
        cleaned = validate_exam_payload(body, partial=True)
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400

    if not cleaned:
        return jsonify({"error": "No valid fields supplied to update."}), 400

    # Re-validate start/end ordering against the *merged* record, so a
    # partial update that only changes one of the two times is still
    # checked against the other's existing value.
    merged_start = cleaned.get("start_time", existing["start_time"])
    merged_end = cleaned.get("end_time", existing["end_time"])
    try:
        validate_time_order(merged_start, merged_end)
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400

    exam = update_exam(exam_id, cleaned)
    return jsonify(exam)


@admin_bp.delete("/<int:exam_id>")
@require_auth("admin")
def cancel_exam_route(exam_id: int):
    """
    Cancels (soft-deletes) an exam by default, matching the spec's
    'cancel exam records' language. Pass ?hard=true to permanently
    remove the row instead.
    """
    existing = get_exam_by_id(exam_id)
    if not existing:
        return jsonify({"error": "Exam not found."}), 404

    if request.args.get("hard", "false").lower() == "true":
        delete_exam(exam_id)
        return jsonify({"message": f"Exam {exam_id} permanently deleted."})

    exam = cancel_exam(exam_id)
    return jsonify({"message": f"Exam {exam_id} cancelled.", "exam": exam})
