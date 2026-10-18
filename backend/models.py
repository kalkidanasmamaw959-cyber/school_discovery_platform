
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(100))
    location = db.Column(db.String(255))
    description = db.Column(db.Text)

    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    website = db.Column(db.String(255))
    telegram = db.Column(db.String(255))

    verification_status = db.Column(
        db.String(20), default="pending", nullable=False
    )

    posts = db.relationship(
        "Post", backref="school", cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        "Review", backref="school", cascade="all, delete-orphan"
    )


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="school", nullable=False)

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=True
    )


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=False
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=False
    )
