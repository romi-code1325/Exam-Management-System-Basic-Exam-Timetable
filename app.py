"""
Exam Timetable Management System -- Flask application entrypoint.

Run directly with `python app.py`, or serve with a WSGI server such as
`gunicorn app:app` in production (see README.md).
"""
from flask import Flask, jsonify

from config import Config
from database import init_db
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
