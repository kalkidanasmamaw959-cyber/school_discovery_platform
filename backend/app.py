import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from .models import db, School, User, Post, Review

app = Flask(__name__)

# SQLite database configuration
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATABASE_PATH = os.path.join(
    BASE_DIR, "instance", "educonnect.db"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH.replace("\\", "/")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect SQLAlchemy to Flask
db.init_app(app)


@app.route("/")
def home():
    return jsonify({
        "message": "Welcome to EduConnect Ethiopia API!",
        "status": "running"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "database": "configured"
    })


@app.route("/api/schools")
def get_schools():
    city = request.args.get("city", "").strip()

    query = School.query

    if city:
        query = query.filter(
            db.func.lower(School.city) == city.lower()
        )

    schools = query.order_by(School.name).all()

    return jsonify([
        {
            "id": school.id,
            "name": school.name,
            "city": school.city,
            "level": school.level,
            "location": school.location,
            "description": school.description,
            "phone": school.phone,
            "email": school.email,
            "website": school.website,
            "telegram": school.telegram,
            "verification_status": school.verification_status
        }
        for school in schools
    ])

# Create the database tables
with app.app_context():
    db.create_all()

    print("DATABASE LOCATION:", db.engine.url.database)
    print("SCHOOLS IN DATABASE:", School.query.count())


if __name__ == "__main__":
    app.run(debug=True)
