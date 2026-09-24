"""Authentication routes: admin login, student register + login."""
from flask import Blueprint, jsonify, request

from auth import issue_token
from config import Config
from models.student import authenticate_student, create_student, \
    get_student_by_email, public_profile

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/admin/login")
def admin_login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))

    if email == Config.ADMIN_EMAIL.lower() and password == Config.ADMIN_PASSWORD:
        token = issue_token(subject=email, role="admin")
        return jsonify({"token": token, "role": "admin", "email": email})

    return jsonify({"error": "Invalid admin credentials."}), 401


@auth_bp.post("/student/register")
def student_register():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", ""))
    academic_year = str(body.get("academic_year", "")).strip()
    section = str(body.get("section", "")).strip()

    errors = {}
    if not name:
        errors["name"] = "name is required."
    if not email:
        errors["email"] = "email is required."
    if not password or len(password) < 6:
        errors["password"] = "password must be at least 6 characters."
    if not academic_year:
        errors["academic_year"] = "academic_year is required."
    if not section:
        errors["section"] = "section is required."

    if errors:
        return jsonify({"errors": errors}), 400

    if get_student_by_email(email):
        return jsonify({"errors": {"email": "email is already registered."}}), 409

    student = create_student(name, email, password, academic_year, section)
    token = issue_token(
        subject=str(student["id"]),
        role="student",
        extra={
            "academic_year": student["academic_year"],
            "section": student["section"],
        },
    )
    return jsonify({"token": token, "student": public_profile(student)}), 201


@auth_bp.post("/student/login")
def student_login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", ""))

    if not email or not password:
        return jsonify({"error": "email and password are required."}), 400

    student = authenticate_student(email, password)
    if not student:
        return jsonify({"error": "Invalid email or password."}), 401

    if not student.get("academic_year") or not student.get("section"):
        # Edge case: student profile missing academic year or section.
        return jsonify({
            "error": "Student profile is incomplete (missing academic_year "
                     "or section). Contact an administrator."
        }), 422

    token = issue_token(
        subject=str(student["id"]),
        role="student",
        extra={
            "academic_year": student["academic_year"],
            "section": student["section"],
        },
    )
    return jsonify({"token": token, "student": public_profile(student)})
