"""
Automated tests for the Exam Timetable Management System.

Run with:  python -m pytest tests/ -v
(or, without pytest installed:  python -m unittest tests.test_app -v)

Uses a fresh temporary SQLite file per test run so tests never touch a
real/dev database.
"""
import os
import tempfile
import unittest

os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "admin123"
os.environ["JWT_SECRET"] = "test-secret"

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


class ExamTimetableTestCase(unittest.TestCase):
    def setUp(self):
        # Fresh SQLite file per test so records from one test never leak
        # into another (Config.DATABASE_PATH is read at connection time,
        # so reassigning it here is enough -- no need to reload modules).
        Config.DATABASE_PATH = tempfile.mktemp(suffix=".db")
        self.app = create_app()
        self.client = self.app.test_client()
        self.admin_token = self._admin_login()

    def tearDown(self):
        if os.path.exists(Config.DATABASE_PATH):
            os.remove(Config.DATABASE_PATH)

    # ---- helpers -------------------------------------------------------

    def _admin_login(self):
        resp = self.client.post(
            "/api/auth/admin/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["token"]

    def _admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def _register_student(self, email, academic_year, section,
                           name="Test Student", password="secret123"):
        resp = self.client.post(
            "/api/auth/student/register",
            json={
                "name": name,
                "email": email,
                "password": password,
                "academic_year": academic_year,
                "section": section,
            },
        )
        return resp

    def _create_exam(self, **overrides):
        payload = {
            "subject": "Mathematics",
            "academic_year": "2nd Year",
            "section": "A",
            "exam_date": "2026-12-01",
            "start_time": "09:00",
            "end_time": "11:00",
        }
        payload.update(overrides)
        return self.client.post(
            "/api/admin/exams", json=payload, headers=self._admin_headers()
        )

    # ---- admin auth ------------------------------------------------------

    def test_admin_login_rejects_wrong_password(self):
        resp = self.client.post(
            "/api/auth/admin/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_exam_routes_reject_missing_token(self):
        resp = self.client.get("/api/admin/exams")
        self.assertEqual(resp.status_code, 401)

    def test_student_cannot_call_admin_routes(self):
        self._register_student("stu1@example.com", "2nd Year", "A")
        login = self.client.post(
            "/api/auth/student/login",
            json={"email": "stu1@example.com", "password": "secret123"},
        )
        student_token = login.get_json()["token"]
        resp = self.client.get(
            "/api/admin/exams",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        self.assertEqual(resp.status_code, 403)

    # ---- exam creation & validation --------------------------------------

    def test_create_exam_success(self):
        resp = self._create_exam()
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["subject"], "Mathematics")
        self.assertEqual(body["is_cancelled"], 0)

    def test_create_exam_missing_required_field(self):
        resp = self._create_exam(subject="")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("subject", resp.get_json()["errors"])

    def test_create_exam_missing_date_field_entirely(self):
        payload = {
            "subject": "Physics",
            "academic_year": "2nd Year",
            "section": "A",
            "start_time": "09:00",
            "end_time": "11:00",
        }
        resp = self.client.post(
            "/api/admin/exams", json=payload, headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("exam_date", resp.get_json()["errors"])

    def test_end_time_before_start_time_rejected(self):
        resp = self._create_exam(start_time="11:00", end_time="09:00")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("end_time", resp.get_json()["errors"])

    def test_end_time_equal_start_time_rejected(self):
        resp = self._create_exam(start_time="09:00", end_time="09:00")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("end_time", resp.get_json()["errors"])

    def test_update_exam_partial_time_change_revalidated(self):
        created = self._create_exam(start_time="09:00", end_time="11:00")
        exam_id = created.get_json()["id"]
        # Only sending a new start_time that is now *after* the existing
        # end_time must still be rejected.
        resp = self.client.put(
            f"/api/admin/exams/{exam_id}",
            json={"start_time": "12:00"},
            headers=self._admin_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("end_time", resp.get_json()["errors"])

    def test_update_exam_success(self):
        created = self._create_exam()
        exam_id = created.get_json()["id"]
        resp = self.client.put(
            f"/api/admin/exams/{exam_id}",
            json={"subject": "Advanced Mathematics"},
            headers=self._admin_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["subject"], "Advanced Mathematics")

    def test_cancel_exam(self):
        created = self._create_exam()
        exam_id = created.get_json()["id"]
        resp = self.client.delete(
            f"/api/admin/exams/{exam_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["exam"]["is_cancelled"], 1)

    def test_cancel_nonexistent_exam_returns_404(self):
        resp = self.client.delete(
            "/api/admin/exams/99999", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 404)

    # ---- student registration & profile -----------------------------------

    def test_student_registration_missing_fields(self):
        resp = self.client.post(
            "/api/auth/student/register",
            json={"name": "", "email": "", "password": "", "academic_year": "",
                  "section": ""},
        )
        self.assertEqual(resp.status_code, 400)
        errors = resp.get_json()["errors"]
        for field in ["name", "email", "password", "academic_year", "section"]:
            self.assertIn(field, errors)

    def test_duplicate_student_email_rejected(self):
        self._register_student("dupe@example.com", "1st Year", "A")
        resp = self._register_student("dupe@example.com", "1st Year", "A")
        self.assertEqual(resp.status_code, 409)

    # ---- the core isolation rule: students only see their own year+section --

    def test_student_sees_only_own_year_and_section(self):
        # Two exams in different sections.
        self._create_exam(section="A", subject="Section A Exam")
        self._create_exam(section="B", subject="Section B Exam")

        self._register_student("secA@example.com", "2nd Year", "A")
        login = self.client.post(
            "/api/auth/student/login",
            json={"email": "secA@example.com", "password": "secret123"},
        )
        token = login.get_json()["token"]

        resp = self.client.get(
            "/api/student/timetable",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["exams"][0]["subject"], "Section A Exam")

    def test_student_cannot_override_section_via_query_params(self):
        """
        Edge case: a student attempts to manipulate API parameters to view
        another section's exams. The endpoint must ignore any such
        parameters and always filter by the authenticated profile only.
        """
        self._create_exam(section="A", subject="Section A Exam")
        self._create_exam(section="B", subject="Section B Exam")

        self._register_student("secA2@example.com", "2nd Year", "A")
        login = self.client.post(
            "/api/auth/student/login",
            json={"email": "secA2@example.com", "password": "secret123"},
        )
        token = login.get_json()["token"]

        resp = self.client.get(
            "/api/student/timetable?academic_year=2nd Year&section=B",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = resp.get_json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["exams"][0]["subject"], "Section A Exam")

    def test_no_exams_for_section_returns_empty_list_not_error(self):
        self._register_student("lonely@example.com", "3rd Year", "Z")
        login = self.client.post(
            "/api/auth/student/login",
            json={"email": "lonely@example.com", "password": "secret123"},
        )
        token = login.get_json()["token"]

        resp = self.client.get(
            "/api/student/timetable",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["count"], 0)
        self.assertEqual(resp.get_json()["exams"], [])

    def test_cancelled_exams_excluded_from_student_timetable(self):
        created = self._create_exam(section="A", subject="Cancel Me")
        exam_id = created.get_json()["id"]
        self.client.delete(
            f"/api/admin/exams/{exam_id}", headers=self._admin_headers()
        )

        self._register_student("secA3@example.com", "2nd Year", "A")
        login = self.client.post(
            "/api/auth/student/login",
            json={"email": "secA3@example.com", "password": "secret123"},
        )
        token = login.get_json()["token"]
        resp = self.client.get(
            "/api/student/timetable",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.get_json()["count"], 0)


if __name__ == "__main__":
    unittest.main()
