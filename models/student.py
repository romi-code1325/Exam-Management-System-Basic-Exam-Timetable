"""Student model & profile data-access functions."""
import hashlib
import hmac
import os

from database import db_cursor


def _hash_password(password: str, salt: bytes | None = None) -> str:
    """PBKDF2-SHA256 password hashing (stdlib only, no extra dependency)."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(expected.hex(), digest_hex)


def create_student(name: str, email: str, password: str, academic_year: str,
                    section: str) -> dict:
    password_hash = _hash_password(password)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO students (name, email, password_hash, academic_year,
                                   section)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email.lower().strip(), password_hash, academic_year,
             section),
        )
        student_id = cur.lastrowid
    return get_student_by_id(student_id)


def get_student_by_id(student_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_student_by_email(email: str) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM students WHERE email = ?", (email.lower().strip(),)
        )
        row = cur.fetchone()
    return dict(row) if row else None


def authenticate_student(email: str, password: str) -> dict | None:
    student = get_student_by_email(email)
    if student and _verify_password(password, student["password_hash"]):
        return student
    return None


def public_profile(student: dict) -> dict:
    """Strip the password hash before returning a student to the client."""
    return {
        "id": student["id"],
        "name": student["name"],
        "email": student["email"],
        "academic_year": student["academic_year"],
        "section": student["section"],
    }
