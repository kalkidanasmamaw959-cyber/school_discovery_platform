import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    """Return a naive UTC timestamp (SQLite-friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


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

    programs = db.Column(db.Text)
    facilities = db.Column(db.Text)

    verification_status = db.Column(
        db.String(20), default="pending", nullable=False
    )
    verification_notes = db.Column(db.Text)
    certification_number = db.Column(db.String(120))
    certification_issuer = db.Column(db.String(150))
    certification_url = db.Column(db.String(500))
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.String(150))

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    posts = db.relationship(
        "Post", back_populates="school", cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        "Review", back_populates="school", cascade="all, delete-orphan"
    )
    users = db.relationship("User", back_populates="school", lazy=True)
    verification_records = db.relationship(
        "VerificationRecord",
        back_populates="school",
        cascade="all, delete-orphan",
        order_by="VerificationRecord.submitted_at.desc()",
    )

    @property
    def programs_list(self):
        return _load_list(self.programs)

    @programs_list.setter
    def programs_list(self, values):
        self.programs = json.dumps(
            [str(value).strip() for value in values if str(value).strip()]
        )

    @property
    def facilities_list(self):
        return _load_list(self.facilities)

    @facilities_list.setter
    def facilities_list(self, values):
        self.facilities = json.dumps(
            [str(value).strip() for value in values if str(value).strip()]
        )

    @property
    def is_verified(self):
        return self.verification_status == "verified"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="school", nullable=False)

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=True
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    last_login_at = db.Column(db.DateTime)

    school = db.relationship("School", back_populates="users")
    tokens = db.relationship(
        "AuthToken", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=False
    )
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    school = db.relationship("School", back_populates="posts")


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    moderated_at = db.Column(db.DateTime)
    moderated_by = db.Column(db.String(150))

    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=False
    )

    school = db.relationship("School", back_populates="reviews")


class VerificationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer, db.ForeignKey("school.id"), nullable=False
    )
    status = db.Column(db.String(20), nullable=False)
    certification_number = db.Column(db.String(120))
    certification_issuer = db.Column(db.String(150))
    certification_url = db.Column(db.String(500))
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.String(150))

    school = db.relationship("School", back_populates="verification_records")


class AuthToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(
        db.String(64), unique=True, nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_used_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="tokens")
