# =============================================================================
# app.py — Flask REST API
#
# Provides three endpoints:
#   GET  /ping   → health check (used by Docker and Jenkins to know the app is up)
#   GET  /user   → return all users from the database as JSON
#   POST /user   → validate and insert a new user, return the created record
#
# Database connection details are read from environment variables so the same
# code works in any environment (local Docker, CI, production RDS) without changes.
# =============================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS           # allows cross-origin requests (needed in dev)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os
import re

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)

# CORS lets browsers on a different origin call the API directly.
# In production the Nginx proxy means the browser is on the same origin,
# but CORS is kept here so the API can also be tested standalone (port 8080).
CORS(app)

# ── Database configuration ────────────────────────────────────────────────────
# os.environ.get(KEY, DEFAULT) reads from the environment variable, falling
# back to the default value if the variable is not set.
# In docker-compose.yml these are set under the "environment:" block.

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "backend_db")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = os.environ.get("DB_PASSWORD", "password")

# Build the SQLAlchemy connection string.
# Format: dialect+driver://username:password@host:port/database
# "mysql+pymysql" means: use the MySQL dialect with the PyMySQL driver.
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Disable the SQLAlchemy event system — we don't use it and it saves memory.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialise SQLAlchemy and bind it to our Flask app.
db = SQLAlchemy(app)


# ── Database model ────────────────────────────────────────────────────────────

class UserEntity(db.Model):
    """
    Maps to the "user_entity" table in MySQL.
    SQLAlchemy auto-creates this table on startup if it doesn't exist (db.create_all below).
    """
    __tablename__ = "user_entity"

    id           = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    full_name    = db.Column(db.String(255), nullable=False)
    email        = db.Column(db.String(255), nullable=False, unique=True)  # unique = no duplicates
    phone_number = db.Column(db.String(20),  nullable=False)

    def to_dict(self):
        """Return a plain dict so Flask can serialise it to JSON."""
        return {
            "id":           self.id,
            "full_name":    self.full_name,
            "email":        self.email,
            "phone_number": self.phone_number,
        }


# ── Validation helper ─────────────────────────────────────────────────────────

def validate_user(data):
    """
    Check the POST body for missing or malformed fields.
    Returns a list of error strings. An empty list means the data is valid.
    """
    errors = []

    # full_name must be present and not just whitespace
    if not data.get("full_name", "").strip():
        errors.append("full_name must not be blank")

    # email must be present and match a basic email pattern
    if not data.get("email", "").strip():
        errors.append("email must not be blank")
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["email"]):
        errors.append("email must be a valid email address")

    # phone_number must be exactly 10 digits
    phone = data.get("phone_number", "").strip()
    if not phone:
        errors.append("phone_number must not be blank")
    elif not re.match(r"^\d{10}$", phone):
        errors.append("phone_number must be exactly 10 digits")

    return errors


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/ping", methods=["GET"])
def ping():
    """
    Health check endpoint.
    Docker Compose and Jenkins curl this to decide whether the container is ready.
    Returns HTTP 200 so "curl -f" exits 0 (success).
    """
    return jsonify({"message": "pong"}), 200


@app.route("/user", methods=["GET"])
def get_users():
    """
    Return all rows from user_entity as a JSON array.
    Returns an empty array [] if the table is empty (not a 404).
    """
    users = UserEntity.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@app.route("/user", methods=["POST"])
def create_user():
    """
    Create a new user from a JSON request body.
    Validates the input, inserts the row, and returns the created record.
    Handles duplicate email with a 409 Conflict instead of a 500 crash.
    """
    # get_json(silent=True) returns None instead of raising an exception
    # if the body is missing or not valid JSON.
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"type": "INVALID_REQUEST", "error": ["Request body must be JSON"]}), 400

    # Validate the fields before touching the database
    errors = validate_user(data)
    if errors:
        return jsonify({"type": "VALIDATION_ERROR", "error": errors}), 400

    try:
        user = UserEntity(
            full_name=data["full_name"].strip(),
            email=data["email"].strip(),
            phone_number=data["phone_number"].strip(),
        )
        db.session.add(user)    # stage the INSERT
        db.session.commit()     # execute the INSERT and get the auto-generated id
        return jsonify(user.to_dict()), 201   # 201 Created

    except IntegrityError:
        # Raised when the UNIQUE constraint on "email" is violated.
        db.session.rollback()   # undo the failed transaction so the session stays usable
        return jsonify({"type": "CONFLICT", "error": ["A user with this email already exists"]}), 409


# ── Database initialisation ───────────────────────────────────────────────────
# db.create_all() creates any tables that don't exist yet.
# It runs once when the container starts. Existing tables (with data) are left untouched.
# app_context() is required because SQLAlchemy needs to know which Flask app to use.
with app.app_context():
    db.create_all()


# ── Entry point ───────────────────────────────────────────────────────────────
# This block only runs when you execute "python app.py" directly.
# In the Docker container, Gunicorn starts the app instead (see backend.Dockerfile CMD).
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
