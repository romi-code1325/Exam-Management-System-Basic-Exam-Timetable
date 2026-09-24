"""
Optional helper: seeds a couple of sample students and exams so you can
try the API immediately after setup, without registering/creating data
by hand first.

Usage: python seed.py
"""
from database import init_db
from models.exam import create_exam
from models.student import create_student, get_student_by_email

init_db()

if not get_student_by_email("asha@example.com"):
    create_student(
        name="Asha Verma",
        email="asha@example.com",
        password="student123",
        academic_year="2nd Year",
        section="A",
    )
    print("Seeded student: asha@example.com / student123 (2nd Year - A)")

if not get_student_by_email("rohan@example.com"):
    create_student(
        name="Rohan Patil",
        email="rohan@example.com",
        password="student123",
        academic_year="2nd Year",
        section="B",
    )
    print("Seeded student: rohan@example.com / student123 (2nd Year - B)")

create_exam({
    "subject": "Data Structures",
    "academic_year": "2nd Year",
    "section": "A",
    "exam_date": "2026-11-10",
    "start_time": "10:00",
    "end_time": "12:00",
})
create_exam({
    "subject": "Operating Systems",
    "academic_year": "2nd Year",
    "section": "B",
    "exam_date": "2026-11-11",
    "start_time": "10:00",
    "end_time": "12:00",
})
print("Seeded 2 exams (2nd Year - A, 2nd Year - B).")
print("Log in as asha@example.com to confirm she only sees the Section A exam.")
