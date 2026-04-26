from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os
import re

app = Flask(__name__)
CORS(app)

# Database configuration — reads from environment variables
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "backend_db")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = os.environ.get("DB_PASSWORD", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class UserEntity(db.Model):
    __tablename__ = "user_entity"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone_number = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone_number": self.phone_number,
        }


def validate_user(data):
    errors = []
    if not data.get("full_name", "").strip():
        errors.append("full_name must not be blank")
    if not data.get("email", "").strip():
        errors.append("email must not be blank")
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["email"]):
        errors.append("email must be a valid email address")
    phone = data.get("phone_number", "").strip()
    if not phone:
        errors.append("phone_number must not be blank")
    elif not re.match(r"^\d{10}$", phone):
        errors.append("phone_number must be exactly 10 digits")
    return errors


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "pong"}), 200


@app.route("/user", methods=["GET"])
def get_users():
    users = UserEntity.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@app.route("/user", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"type": "INVALID_REQUEST", "error": ["Request body must be JSON"]}), 400

    errors = validate_user(data)
    if errors:
        return jsonify({"type": "VALIDATION_ERROR", "error": errors}), 400

    try:
        user = UserEntity(
            full_name=data["full_name"].strip(),
            email=data["email"].strip(),
            phone_number=data["phone_number"].strip(),
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"type": "CONFLICT", "error": ["A user with this email already exists"]}), 409


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
