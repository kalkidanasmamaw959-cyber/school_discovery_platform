import hashlib
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import event, inspect, or_, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

try:
    from .models import (
        AuthToken,
        Post,
        Review,
        School,
        User,
        VerificationRecord,
        db,
        utcnow,
    )
except ImportError: 
    from models import ( 
        AuthToken,
        Post,
        Review,
        School,
        User,
        VerificationRecord,
        db,
        utcnow,
    )


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR
DEFAULT_DATABASE_PATH = BASE_DIR / "instance" / "educonnect.db"
DEFAULT_PORT = 5000

load_dotenv(BASE_DIR / ".env")

CITIES = ["Addis Ababa", "Bahir Dar", "Hawassa", "Adama"]
LEVELS = [
    "Kindergarten",
    "Primary",
    "Secondary",
    "Primary & Secondary",
    "Kindergarten, Primary & Secondary",
]
ROLES = {"school", "admin"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,24}$")

DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5001,http://localhost:5001,"
    "http://127.0.0.1:5000,http://localhost:5000,"
    "http://127.0.0.1:5500,http://localhost:5500,"
    "http://127.0.0.1:5501,http://localhost:5501,"
    "http://127.0.0.1:5502,http://localhost:5502,"
    "http://127.0.0.1:5503,http://localhost:5503,"
    "http://127.0.0.1:5504,http://localhost:5504,"
    "http://127.0.0.1:5505,http://localhost:5505,"
    "http://127.0.0.1:8000,http://localhost:8000,"
    "http://127.0.0.1:8080,http://localhost:8080"
)

RECOMMENDATION_WEIGHTS = {
    "city": 30,
    "level": 20,
    "facilities": 20,
    "programs": 10,
    "verification": 10,
    "contact": 5,
    "community": 5,
}

FRONTEND_FILES = {
    "index.html",
    "school-login.html",
    "school-register.html",
    "dashboard.html",
    "admin.html",
    "style.css",
    "script.js",
    "login.js",
    "registration.js",
    "dashboard.js",
    "admin.js",
    "api-config.js",
}

LOGIN_FAILURES = {}
LOGIN_LOCK = threading.Lock()
LOGIN_WINDOW_SECONDS = 600
LOGIN_MAX_FAILURES = 10


class ApiError(Exception):
    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def _iso(value):
    return value.isoformat() + "Z" if value else None


def _json_error(message, status=400, details=None):
    payload = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _clean_text(value, field, min_len=0, max_len=255, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(f"{field} must be text.")
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value).strip()
    if required and len(value) < min_len:
        raise ApiError(
            f"{field} must be at least {min_len} characters."
        )
    if len(value) > max_len:
        raise ApiError(f"{field} must be at most {max_len} characters.")
    return value


def _validate_email(value, field="Email"):
    email = _clean_text(value, field, 3, 150, required=True).lower()
    if not EMAIL_RE.match(email):
        raise ApiError(f"Enter a valid {field.lower()} address.")
    return email


def _validate_phone(value, field="Phone number", required=True):
    phone = _clean_text(value, field, 7, 30, required=required)
    if phone and not PHONE_RE.match(phone):
        raise ApiError(f"Enter a valid {field.lower()}.")
    return phone


def _validate_url(value, field, required=False):
    url = _clean_text(value, field, 0, 500, required=required)
    if not url:
        return ""
    if not re.match(r"^https?://[^\s]+$", url, re.IGNORECASE):
        raise ApiError(f"{field} must start with http:// or https://.")
    return url


def _canonical_city(value, field="City", required=True):
    city = _clean_text(value, field, 2, 100, required=required)
    if not city:
        return ""
    for allowed in CITIES:
        if allowed.lower() == city.lower():
            return allowed
    raise ApiError(
        f"{field} must be one of: {', '.join(CITIES)}."
    )


def _canonical_level(value, field="School level", required=True):
    level = _clean_text(value, field, 0, 100, required=required)
    if not level:
        return ""
    for allowed in LEVELS:
        if allowed.lower() == level.lower():
            return allowed
    raise ApiError(f"Choose a valid {field.lower()}.")


def _validate_username(value):
    username = _clean_text(
        value, "Username", 3, 30, required=True
    )
    if not USERNAME_RE.match(username):
        raise ApiError(
            "Username must be 3-30 characters using letters, numbers, "
            "dots, underscores or hyphens."
        )
    return username


def _validate_password(value, field="Password"):
    if not isinstance(value, str):
        raise ApiError(f"{field} must be text.")
    if len(value) < 8:
        raise ApiError(f"{field} must be at least 8 characters.")
    if len(value) > 128:
        raise ApiError(f"{field} must be at most 128 characters.")
    if not value.strip():
        raise ApiError(f"{field} cannot be only spaces.")
    return value


def _parse_list(value, field, max_items=20, max_len=60):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ApiError(f"{field} must be a list or comma-separated text.")

    items = []
    seen = set()
    for raw in raw_items:
        item = _clean_text(raw, field, 0, max_len)
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            items.append(item)
    if len(items) > max_items:
        raise ApiError(f"{field} can contain at most {max_items} items.")
    return items


def _validate_rating(value):
    if isinstance(value, bool):
        raise ApiError("Rating must be a whole number from 1 to 5.")
    if isinstance(value, float) and not value.is_integer():
        raise ApiError("Rating must be a whole number from 1 to 5.")
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise ApiError("Rating must be a whole number from 1 to 5.")
    if rating < 1 or rating > 5:
        raise ApiError("Rating must be between 1 and 5.")
    return rating


def _get_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Send a JSON request body.")
    return data


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_token(user, remember=False):
    raw_token = secrets.token_urlsafe(40)
    days = 30 if remember else 7
    token = AuthToken(
        token_hash=_token_hash(raw_token),
        user_id=user.id,
        expires_at=utcnow() + timedelta(days=days),
    )
    AuthToken.query.filter(
        AuthToken.user_id == user.id,
        AuthToken.expires_at < utcnow(),
    ).delete(synchronize_session=False)
    db.session.add(token)
    user.last_login_at = utcnow()
    db.session.commit()
    return raw_token


def _public_post(post):
    return {
        "id": post.id,
        "title": post.title,
        "text": post.content,
        "content": post.content,
        "date": (
            post.created_at.strftime("%Y-%m-%d")
            if post.created_at
            else ""
        ),
        "created_at": _iso(post.created_at),
        "is_hidden": bool(post.is_hidden),
    }


def _public_review(review):
    return {
        "id": review.id,
        "name": review.reviewer_name,
        "rating": review.rating,
        "comment": review.comment or "",
        "date": (
            review.created_at.strftime("%Y-%m-%d")
            if review.created_at
            else ""
        ),
        "created_at": _iso(review.created_at),
        "is_hidden": bool(review.is_hidden),
    }


def _public_school(school):
    reviews = sorted(
        [review for review in school.reviews if not review.is_hidden],
        key=lambda item: item.created_at or datetime.min,
        reverse=True,
    )
    posts = sorted(
        [post for post in school.posts if not post.is_hidden],
        key=lambda item: item.created_at or datetime.min,
        reverse=True,
    )
    average = (
        round(sum(review.rating for review in reviews) / len(reviews), 1)
        if reviews
        else None
    )
    missing = []
    for field in ("location", "phone", "email", "website"):
        if not getattr(school, field):
            missing.append(field)
    if not school.programs_list:
        missing.append("programs")
    if not school.facilities_list:
        missing.append("facilities")

    return {
        "id": school.id,
        "name": school.name,
        "city": school.city,
        "level": school.level or "",
        "location": school.location or "",
        "description": school.description or "",
        "programs": school.programs_list,
        "facilities": school.facilities_list,
        "phone": school.phone or "",
        "email": school.email or "",
        "website": school.website or "",
        "telegram": school.telegram or "",
        "verification_status": school.verification_status,
        "verified": school.is_verified,
        "verification_label": (
            "Verified by EduConnect administrator"
            if school.is_verified
            else "Unverified profile"
        ),
        "average_rating": average,
        "review_count": len(reviews),
        "posts": [_public_post(post) for post in posts],
        "reviews": [_public_review(review) for review in reviews],
        "missing_information": missing,
        "created_at": _iso(school.created_at),
        "updated_at": _iso(school.updated_at),
    }


def _verification_record(record, admin_view=False):
    data = {
        "id": record.id,
        "status": record.status,
        "certification_number": record.certification_number or "",
        "certification_issuer": record.certification_issuer or "",
        "certification_url": record.certification_url or "",
        "notes": record.notes or "",
        "submitted_at": _iso(record.submitted_at),
        "reviewed_at": _iso(record.reviewed_at),
        "reviewed_by": record.reviewed_by or "",
    }
    if admin_view:
        data["admin_notes"] = record.admin_notes or ""
    return data


def _owner_school(school):
    data = _public_school(school)
    data.update(
        {
            "certification_number": school.certification_number or "",
            "certification_issuer": school.certification_issuer or "",
            "certification_url": school.certification_url or "",
            "verification_notes": school.verification_notes or "",
            "verified_at": _iso(school.verified_at),
            "verified_by": school.verified_by or "",
            "verification_records": [
                _verification_record(record)
                for record in school.verification_records
            ],
        }
    )
    return data


def _admin_school(school):
    data = _owner_school(school)
    data["users"] = [
        _safe_user(user) for user in school.users
    ]
    data["hidden_post_count"] = sum(
        1 for post in school.posts if post.is_hidden
    )
    data["hidden_review_count"] = sum(
        1 for review in school.reviews if review.is_hidden
    )
    data["verification_records"] = [
        _verification_record(record, admin_view=True)
        for record in school.verification_records
    ]
    return data


def _safe_user(user, include_school=False):
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": bool(user.is_active),
        "school_id": user.school_id,
        "created_at": _iso(user.created_at),
        "last_login_at": _iso(user.last_login_at),
    }
    if include_school and user.school:
        data["school_name"] = user.school.name
    return data


def _auth_required(roles=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            parts = header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return _json_error("Authentication required.", 401)

            token = AuthToken.query.filter_by(
                token_hash=_token_hash(parts[1])
            ).first()
            if (
                not token
                or token.expires_at < utcnow()
                or not token.user.is_active
            ):
                if token:
                    db.session.delete(token)
                    db.session.commit()
                return _json_error(
                    "Your session is invalid or has expired. Sign in again.",
                    401,
                )

            token.last_used_at = utcnow()
            db.session.commit()
            g.current_user = token.user
            g.auth_token = token

            if roles and token.user.role not in roles:
                return _json_error(
                    "You do not have permission to perform this action.",
                    403,
                )
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _level_matches(school_level, wanted):
    if not school_level:
        return None
    return wanted.lower() in school_level.lower()


def _program_matches(school, wanted):
    wanted_lower = wanted.lower()
    for program in school.programs_list:
        if wanted_lower in program.lower():
            return True, "school_programs"
    if school.level and wanted_lower in school.level.lower():
        return True, "stated_level"
    return False, "missing"


def _missing_contact_fields(school):
    return [
        label
        for label, value in (
            ("location", school.location),
            ("phone", school.phone),
            ("email", school.email),
            ("website", school.website),
        )
        if not value
    ]


def _recommendation_for_school(school, preferences):
    city = preferences.get("city")
    level = preferences.get("level")
    facilities = preferences.get("facilities", [])
    programs = preferences.get("programs", [])

    total = 0.0
    maximum = 0.0
    reasons = []
    missing = []

    if city:
        maximum += RECOMMENDATION_WEIGHTS["city"]
        if school.city.lower() == city.lower():
            total += RECOMMENDATION_WEIGHTS["city"]
            reasons.append(
                {
                    "factor": "city",
                    "label": "City",
                    "status": "matched",
                    "points": RECOMMENDATION_WEIGHTS["city"],
                    "max_points": RECOMMENDATION_WEIGHTS["city"],
                    "detail": f"Located in {school.city}, your chosen city.",
                }
            )
        else:
            reasons.append(
                {
                    "factor": "city",
                    "label": "City",
                    "status": "unmatched",
                    "points": 0,
                    "max_points": RECOMMENDATION_WEIGHTS["city"],
                    "detail": f"Located in {school.city}, not {city}.",
                }
            )

    if level:
        maximum += RECOMMENDATION_WEIGHTS["level"]
        matched = _level_matches(school.level, level)
        if matched:
            total += RECOMMENDATION_WEIGHTS["level"]
            reasons.append(
                {
                    "factor": "level",
                    "label": "Education level",
                    "status": "matched",
                    "points": RECOMMENDATION_WEIGHTS["level"],
                    "max_points": RECOMMENDATION_WEIGHTS["level"],
                    "detail": f"Offers {school.level}.",
                }
            )
        elif matched is None:
            missing.append("level")
            reasons.append(
                {
                    "factor": "level",
                    "label": "Education level",
                    "status": "missing",
                    "points": 0,
                    "max_points": RECOMMENDATION_WEIGHTS["level"],
                    "detail": "The school has not provided its education level.",
                }
            )
        else:
            reasons.append(
                {
                    "factor": "level",
                    "label": "Education level",
                    "status": "unmatched",
                    "points": 0,
                    "max_points": RECOMMENDATION_WEIGHTS["level"],
                    "detail": f"Listed as {school.level}, not {level}.",
                }
            )

    if facilities:
        maximum += RECOMMENDATION_WEIGHTS["facilities"]
        available = {item.lower(): item for item in school.facilities_list}
        if not available:
            missing.append("facilities")
            reasons.append(
                {
                    "factor": "facilities",
                    "label": "Facilities",
                    "status": "missing",
                    "points": 0,
                    "max_points": RECOMMENDATION_WEIGHTS["facilities"],
                    "detail": (
                        "Facility information is not available for this "
                        "school; no assumption was made."
                    ),
                }
            )
        else:
            matched = [
                wanted
                for wanted in facilities
                if any(wanted.lower() in key for key in available)
            ]
            points = (
                RECOMMENDATION_WEIGHTS["facilities"]
                * len(matched)
                / len(facilities)
            )
            total += points
            reasons.append(
                {
                    "factor": "facilities",
                    "label": "Facilities",
                    "status": "matched" if len(matched) == len(facilities) else (
                        "partial" if matched else "unmatched"
                    ),
                    "points": round(points, 1),
                    "max_points": RECOMMENDATION_WEIGHTS["facilities"],
                    "detail": (
                        f"Matched {len(matched)} of {len(facilities)} "
                        f"preferred facilities"
                        + (
                            f": {', '.join(matched)}."
                            if matched
                            else "; none are listed by the school."
                        )
                    ),
                }
            )

    if programs:
        maximum += RECOMMENDATION_WEIGHTS["programs"]
        matched = []
        sources = set()
        for wanted in programs:
            found, source = _program_matches(school, wanted)
            if found:
                matched.append(wanted)
                sources.add(source)
        if not school.programs_list and not school.level:
            missing.append("programs")
            reasons.append(
                {
                    "factor": "programs",
                    "label": "Programs",
                    "status": "missing",
                    "points": 0,
                    "max_points": RECOMMENDATION_WEIGHTS["programs"],
                    "detail": (
                        "Program information is not available; no assumption "
                        "was made."
                    ),
                }
            )
        else:
            points = (
                RECOMMENDATION_WEIGHTS["programs"]
                * len(matched)
                / len(programs)
            )
            total += points
            source_note = ""
            if "stated_level" in sources:
                source_note = (
                    " Some matches come from the school's stated level "
                    "because a detailed program list was not provided."
                )
            reasons.append(
                {
                    "factor": "programs",
                    "label": "Programs",
                    "status": "matched" if len(matched) == len(programs) else (
                        "partial" if matched else "unmatched"
                    ),
                    "points": round(points, 1),
                    "max_points": RECOMMENDATION_WEIGHTS["programs"],
                    "detail": (
                        f"Matched {len(matched)} of {len(programs)} preferred "
                        f"programs" + (f": {', '.join(matched)}." if matched else ".")
                        + source_note
                    ),
                }
            )

    maximum += RECOMMENDATION_WEIGHTS["verification"]
    if school.is_verified:
        total += RECOMMENDATION_WEIGHTS["verification"]
        reasons.append(
            {
                "factor": "verification",
                "label": "Verification",
                "status": "matched",
                "points": RECOMMENDATION_WEIGHTS["verification"],
                "max_points": RECOMMENDATION_WEIGHTS["verification"],
                "detail": (
                    "Certification details were reviewed and approved by an "
                    "EduConnect administrator."
                ),
            }
        )
    else:
        reasons.append(
            {
                "factor": "verification",
                "label": "Verification",
                "status": "unverified",
                "points": 0,
                "max_points": RECOMMENDATION_WEIGHTS["verification"],
                "detail": (
                    "This profile is not verified. Its information should be "
                    "confirmed directly with the school."
                ),
            }
        )

    maximum += RECOMMENDATION_WEIGHTS["contact"]
    contact_fields = _missing_contact_fields(school)
    contact_ratio = (4 - len(contact_fields)) / 4
    total += RECOMMENDATION_WEIGHTS["contact"] * contact_ratio
    reasons.append(
        {
            "factor": "contact",
            "label": "Contact information",
            "status": "matched" if not contact_fields else (
                "partial" if contact_ratio else "missing"
            ),
            "points": round(
                RECOMMENDATION_WEIGHTS["contact"] * contact_ratio, 1
            ),
            "max_points": RECOMMENDATION_WEIGHTS["contact"],
            "detail": (
                "Location, phone, email and website are all provided."
                if not contact_fields
                else "Missing: " + ", ".join(contact_fields) + "."
            ),
        }
    )
    if contact_fields:
        missing.extend(contact_fields)

    maximum += RECOMMENDATION_WEIGHTS["community"]
    visible_reviews = [
        review for review in school.reviews if not review.is_hidden
    ]
    if visible_reviews:
        average = sum(review.rating for review in visible_reviews) / len(
            visible_reviews
        )
        points = RECOMMENDATION_WEIGHTS["community"] * average / 5
        total += points
        reasons.append(
            {
                "factor": "community",
                "label": "Family reviews",
                "status": "matched",
                "points": round(points, 1),
                "max_points": RECOMMENDATION_WEIGHTS["community"],
                "detail": (
                    f"{len(visible_reviews)} published review(s) with an "
                    f"average rating of {average:.1f}/5."
                ),
            }
        )
    else:
        reasons.append(
            {
                "factor": "community",
                "label": "Family reviews",
                "status": "missing",
                "points": 0,
                "max_points": RECOMMENDATION_WEIGHTS["community"],
                "detail": "No published family reviews yet.",
            }
        )
        missing.append("reviews")

    score = round(total / maximum * 100, 1) if maximum else 0.0
    return {
        "score": score,
        "raw_score": round(total, 1),
        "max_score": maximum,
        "reasons": reasons,
        "missing_information": sorted(set(missing)),
        "school": _public_school(school),
    }


def _external_ai_summary(preferences, results):
    """Optional OpenAI-compatible summary.

    Only runs when explicitly enabled and configured. The rule-based scoring
    remains authoritative; the external text is explanatory only.
    """
    enabled = os.environ.get("EDUCONNECT_ENABLE_AI", "").lower() in {
        "1",
        "true",
        "yes",
    }
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not enabled or not api_key or not model:
        return None

    base_url = os.environ.get(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    ).rstrip("/")
    facts = [
        {
            "name": item["school"]["name"],
            "city": item["school"]["city"],
            "score": item["score"],
            "verified": item["school"]["verified"],
            "reasons": [
                reason["detail"] for reason in item["reasons"]
            ],
        }
        for item in results[:5]
    ]
    prompt = (
        "Write a short, neutral explanation (maximum 120 words) of these "
        "school recommendations for a family. Use ONLY the facts provided. "
        "Do not invent fees, facilities, accreditation, ratings or quality "
        "claims. Mention that pending profiles are unverified. Data: "
        + json.dumps({"preferences": preferences, "recommendations": facts})
    )
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You explain rankings. Never add facts that are not "
                        "in the user's data."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }
    ).encode("utf-8")
    req = urlrequest.Request(
        base_url + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        summary = body["choices"][0]["message"]["content"].strip()
        if not summary:
            return None
        return {"summary": summary[:1600], "model": model}
    except Exception:
        return None


def _login_rate_limited(ip):
    now = time.time()
    with LOGIN_LOCK:
        attempts = [
            stamp
            for stamp in LOGIN_FAILURES.get(ip, [])
            if now - stamp < LOGIN_WINDOW_SECONDS
        ]
        LOGIN_FAILURES[ip] = attempts
        return len(attempts) >= LOGIN_MAX_FAILURES


def _record_login_failure(ip):
    with LOGIN_LOCK:
        LOGIN_FAILURES.setdefault(ip, []).append(time.time())


def _clear_login_failures(ip):
    with LOGIN_LOCK:
        LOGIN_FAILURES.pop(ip, None)


COLUMN_MIGRATIONS = {
    "school": {
        "programs": "TEXT",
        "facilities": "TEXT",
        "verification_notes": "TEXT",
        "certification_number": "VARCHAR(120)",
        "certification_issuer": "VARCHAR(150)",
        "certification_url": "VARCHAR(500)",
        "verified_at": "DATETIME",
        "verified_by": "VARCHAR(150)",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "user": {
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "created_at": "DATETIME",
        "last_login_at": "DATETIME",
    },
    "post": {
        "updated_at": "DATETIME",
        "is_hidden": "BOOLEAN NOT NULL DEFAULT 0",
        "author_id": "INTEGER",
    },
    "review": {
        "is_hidden": "BOOLEAN NOT NULL DEFAULT 0",
        "moderated_at": "DATETIME",
        "moderated_by": "VARCHAR(150)",
    },
}


def ensure_schema():
    """Add new columns/tables to an existing SQLite database in place."""
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    for table_name, columns in COLUMN_MIGRATIONS.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }
        for column_name, ddl in columns.items():
            if column_name not in existing_columns:
                db.session.execute(
                    text(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {ddl}'
                    )
                )
    db.session.commit()

    backfills = [
        "UPDATE school SET created_at = CURRENT_TIMESTAMP "
        "WHERE created_at IS NULL",
        "UPDATE school SET updated_at = CURRENT_TIMESTAMP "
        "WHERE updated_at IS NULL",
        "UPDATE user SET created_at = CURRENT_TIMESTAMP "
        "WHERE created_at IS NULL",
        "UPDATE post SET updated_at = created_at "
        "WHERE updated_at IS NULL",
        "UPDATE post SET is_hidden = 0 WHERE is_hidden IS NULL",
        "UPDATE review SET is_hidden = 0 WHERE is_hidden IS NULL",
        "UPDATE user SET is_active = 1 WHERE is_active IS NULL",
    ]
    for statement in backfills:
        db.session.execute(text(statement))
    db.session.commit()

    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_post_school_id ON post (school_id)",
        "CREATE INDEX IF NOT EXISTS ix_review_school_id ON review (school_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_school_id ON user (school_id)",
        "CREATE INDEX IF NOT EXISTS ix_token_user_id ON auth_token (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_verification_school_id "
        "ON verification_record (school_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username_ci "
        "ON user (lower(username))",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email_ci "
        "ON user (lower(email))",
    ]
    for statement in indexes:
        try:
            db.session.execute(text(statement))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)

    configured_database_path = os.environ.get("DATABASE_PATH")
    database_path = Path(
        configured_database_path or DEFAULT_DATABASE_PATH
    ).expanduser()
    if not database_path.is_absolute():
        database_path = (BASE_DIR / database_path).resolve()
    database_uri = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + database_path.as_posix()
    )

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS", DEFAULT_CORS_ORIGINS
        ).split(",")
        if origin.strip()
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=600,
    )

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return _json_error(error.message, error.status, error.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            messages = {
                404: "The requested resource was not found.",
                405: "This method is not allowed for this endpoint.",
                413: "The request is too large.",
            }
            return _json_error(
                messages.get(error.code, error.description),
                error.code or 500,
            )
        return error

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        app.logger.exception("Unhandled error on %s", request.path)
        if request.path.startswith("/api/"):
            return _json_error(
                "An unexpected server error occurred. Please try again.",
                500,
            )
        return (
            "An unexpected server error occurred.",
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/")
    def home():
        return jsonify(
            {
                "message": "Welcome to the EduConnect Ethiopia API.",
                "status": "running",
                "frontend": "/app/",
                "health": "/api/health",
            }
        )

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(
                {
                    "status": "healthy",
                    "database": "connected",
                    "schools": School.query.count(),
                }
            )
        except Exception:
            app.logger.exception("Health check failed")
            return _json_error("Database connection failed.", 503)

    @app.get("/app/")
    def frontend_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/app/<path:filename>")
    def frontend_file(filename):
        if filename not in FRONTEND_FILES:
            return _json_error("The requested file was not found.", 404)
        return send_from_directory(FRONTEND_DIR, filename)

    @app.get("/api/meta")
    def meta():
        facilities = set()
        programs = set()
        for school in School.query.filter(
            School.verification_status != "rejected"
        ).all():
            facilities.update(school.facilities_list)
            programs.update(school.programs_list)
        return jsonify(
            {
                "cities": CITIES,
                "levels": LEVELS,
                "facilities": sorted(facilities),
                "programs": sorted(programs),
                "fees_available": False,
                "fees_note": (
                    "Reliable fee data is not collected, so cost is not "
                    "used in recommendations."
                ),
            }
        )

    @app.get("/api/schools")
    def get_schools():
        city = _clean_text(request.args.get("city", ""), "City", 0, 100)
        level = _clean_text(request.args.get("level", ""), "Level", 0, 100)
        search = _clean_text(
            request.args.get("search", ""), "Search", 0, 100
        )
        verified = request.args.get("verified", "").lower()

        query = School.query.filter(
            School.verification_status != "rejected"
        )
        if city:
            query = query.filter(db.func.lower(School.city) == city.lower())
        if level:
            query = query.filter(School.level.ilike(f"%{level}%"))
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    School.name.ilike(pattern),
                    School.city.ilike(pattern),
                    School.location.ilike(pattern),
                    School.description.ilike(pattern),
                )
            )
        if verified in {"1", "true", "yes"}:
            query = query.filter(School.verification_status == "verified")
        elif verified in {"0", "false", "no"}:
            query = query.filter(School.verification_status != "verified")

        schools = query.order_by(School.name.asc()).all()
        return jsonify([_public_school(school) for school in schools])

    @app.get("/api/schools/<int:school_id>")
    def get_school(school_id):
        school = db.session.get(School, school_id)
        if not school or school.verification_status == "rejected":
            return _json_error("School not found.", 404)
        return jsonify(_public_school(school))

    @app.get("/api/schools/<int:school_id>/posts")
    def get_school_posts(school_id):
        school = db.session.get(School, school_id)
        if not school or school.verification_status == "rejected":
            return _json_error("School not found.", 404)
        posts = sorted(
            [post for post in school.posts if not post.is_hidden],
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return jsonify([_public_post(post) for post in posts])

    @app.post("/api/schools/<int:school_id>/reviews")
    def create_review(school_id):
        school = db.session.get(School, school_id)
        if not school or school.verification_status == "rejected":
            return _json_error("School not found.", 404)
        data = _get_json()
        reviewer_name = _clean_text(
            data.get("name"), "Your name", 2, 100, required=True
        )
        rating = _validate_rating(data.get("rating"))
        comment = _clean_text(
            data.get("comment"), "Review", 3, 2000, required=True
        )

        review = Review(
            reviewer_name=reviewer_name,
            rating=rating,
            comment=comment,
            school_id=school.id,
        )
        db.session.add(review)
        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Thank you. Your review has been published.",
                    "review": _public_review(review),
                }
            ),
            201,
        )

    @app.post("/api/auth/register")
    def register():
        data = _get_json()
        school_name = _clean_text(
            data.get("school_name"), "School name", 2, 150, required=True
        )
        city = _canonical_city(data.get("city"))
        level = _canonical_level(data.get("level"))
        location = _clean_text(
            data.get("location"), "School address", 2, 255, required=True
        )
        school_email = _validate_email(
            data.get("school_email") or data.get("email"),
            "School email",
        )
        phone = _validate_phone(data.get("phone"))
        website = _validate_url(data.get("website"), "Website")
        telegram = _validate_url(data.get("telegram"), "Telegram link")
        description = _clean_text(
            data.get("description"), "Description", 0, 2000
        )
        username = _validate_username(data.get("username"))
        account_email = _validate_email(
            data.get("account_email") or school_email,
            "Account email",
        )
        password = _validate_password(data.get("password"))
        confirm = data.get("confirm_password")
        if confirm is not None and confirm != password:
            raise ApiError("Passwords do not match.")
        certification_number = _clean_text(
            data.get("certification_number"),
            "Certification number",
            3,
            120,
            required=True,
        )
        certification_issuer = _clean_text(
            data.get("certification_issuer") or "Ministry of Education",
            "Certification issuer",
            2,
            150,
            required=True,
        )
        certification_url = _validate_url(
            data.get("certification_url"), "Certification reference link"
        )

        if User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first():
            return _json_error("That username is already in use.", 409)
        if User.query.filter(
            db.func.lower(User.email) == account_email.lower()
        ).first():
            return _json_error("That email is already registered.", 409)

        school = School.query.filter(
            db.func.lower(School.name) == school_name.lower(),
            db.func.lower(School.city) == city.lower(),
        ).first()
        if school:
            if User.query.filter_by(school_id=school.id).first():
                return _json_error(
                    "An account already exists for this school. "
                    "Sign in or contact an administrator.",
                    409,
                )
            if school.verification_status == "rejected":
                school.verification_status = "pending"
        else:
            school = School(
                name=school_name,
                city=city,
                verification_status="pending",
            )
            db.session.add(school)
            db.session.flush()

        school.name = school_name
        school.city = city
        school.level = level
        school.location = location
        school.description = description
        school.phone = phone
        school.email = school_email
        school.website = website
        school.telegram = telegram
        school.verification_status = "pending"
        school.verification_notes = (
            "Certification submitted; awaiting administrator review."
        )
        school.certification_number = certification_number
        school.certification_issuer = certification_issuer
        school.certification_url = certification_url
        school.verified_at = None
        school.verified_by = None

        user = User(
            username=username,
            email=account_email,
            role="school",
            school_id=school.id,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        record = VerificationRecord(
            school_id=school.id,
            status="submitted",
            certification_number=certification_number,
            certification_issuer=certification_issuer,
            certification_url=certification_url,
            submitted_by_id=user.id,
            notes="Submitted during school registration.",
        )
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _json_error(
                "That username or email was just registered. Try again.",
                409,
            )

        token = _issue_token(user, remember=False)
        return (
            jsonify(
                {
                    "message": (
                        "School account created. Your certification is "
                        "pending administrator review."
                    ),
                    "token": token,
                    "user": _safe_user(user, include_school=True),
                    "school": _owner_school(school),
                    "redirect": "dashboard.html",
                }
            ),
            201,
        )

    @app.post("/api/auth/login")
    def login():
        ip = request.remote_addr or "unknown"
        if _login_rate_limited(ip):
            return _json_error(
                "Too many sign-in attempts. Please wait and try again.", 429
            )
        data = _get_json()
        identifier = _clean_text(
            data.get("identifier") or data.get("username") or data.get("email"),
            "Username or email",
            1,
            150,
            required=True,
        )
        password = data.get("password")
        if not isinstance(password, str) or not password:
            raise ApiError("Password is required.")

        user = User.query.filter(
            or_(
                db.func.lower(User.username) == identifier.lower(),
                db.func.lower(User.email) == identifier.lower(),
            )
        ).first()
        if not user or not user.check_password(password):
            _record_login_failure(ip)
            return _json_error("Invalid username/email or password.", 401)
        if not user.is_active:
            return _json_error(
                "This account has been disabled. Contact an administrator.",
                403,
            )

        _clear_login_failures(ip)
        token = _issue_token(user, remember=bool(data.get("remember")))
        return jsonify(
            {
                "message": "Signed in successfully.",
                "token": token,
                "user": _safe_user(user, include_school=True),
                "school": _owner_school(user.school) if user.school else None,
                "redirect": (
                    "admin.html" if user.role == "admin" else "dashboard.html"
                ),
            }
        )

    @app.post("/api/auth/logout")
    @_auth_required()
    def logout():
        db.session.delete(g.auth_token)
        db.session.commit()
        return jsonify({"message": "Signed out."})

    @app.get("/api/auth/me")
    @_auth_required()
    def me():
        user = g.current_user
        return jsonify(
            {
                "user": _safe_user(user, include_school=True),
                "school": _owner_school(user.school) if user.school else None,
            }
        )

    @app.get("/api/school/me")
    @_auth_required(roles={"school", "admin"})
    def get_own_school():
        if not g.current_user.school:
            return _json_error("No school is linked to this account.", 404)
        return jsonify(_owner_school(g.current_user.school))

    @app.put("/api/school/me")
    @_auth_required(roles={"school"})
    def update_own_school():
        school = g.current_user.school
        if not school:
            return _json_error("No school is linked to this account.", 404)
        data = _get_json()

        school_name = _clean_text(
            data.get("name", school.name), "School name", 2, 150,
            required=True,
        )
        city = _canonical_city(data.get("city", school.city))
        level = _canonical_level(data.get("level", school.level))
        location = _clean_text(
            data.get("location", school.location), "School address", 0, 255
        )
        email = _validate_email(
            data.get("email", school.email), "School email"
        )
        phone = _validate_phone(
            data.get("phone", school.phone), "Phone number", required=False
        )
        website = _validate_url(
            data.get("website", school.website), "Website"
        )
        telegram = _validate_url(
            data.get("telegram", school.telegram), "Telegram link"
        )
        description = _clean_text(
            data.get("description", school.description),
            "Description",
            0,
            2000,
        )
        programs = _parse_list(
            data.get("programs", school.programs_list), "Programs"
        )
        facilities = _parse_list(
            data.get("facilities", school.facilities_list), "Facilities"
        )

        identity_changed = (
            school.name != school_name or school.city != city
        )

        school.name = school_name
        school.city = city
        school.level = level
        school.location = location
        school.email = email
        school.phone = phone
        school.website = website
        school.telegram = telegram
        school.description = description
        school.programs_list = programs
        school.facilities_list = facilities

        reset_notice = ""
        if identity_changed and school.verification_status == "verified":
            school.verification_status = "pending"
            school.verified_at = None
            school.verified_by = None
            school.verification_notes = (
                "Identity details changed; administrator re-verification "
                "is required."
            )
            reset_notice = (
                " Your verification status was reset to pending because "
                "identity details changed."
            )
            db.session.add(
                VerificationRecord(
                    school_id=school.id,
                    status="resubmitted",
                    certification_number=school.certification_number,
                    certification_issuer=school.certification_issuer,
                    certification_url=school.certification_url,
                    submitted_by_id=g.current_user.id,
                    notes="Profile identity details changed.",
                )
            )

        db.session.commit()
        return jsonify(
            {
                "message": "School profile updated." + reset_notice,
                "school": _owner_school(school),
            }
        )

    @app.post("/api/school/verification")
    @_auth_required(roles={"school"})
    def resubmit_verification():
        school = g.current_user.school
        if not school:
            return _json_error("No school is linked to this account.", 404)
        data = _get_json()
        certification_number = _clean_text(
            data.get("certification_number"),
            "Certification number",
            3,
            120,
            required=True,
        )
        certification_issuer = _clean_text(
            data.get("certification_issuer") or "Ministry of Education",
            "Certification issuer",
            2,
            150,
            required=True,
        )
        certification_url = _validate_url(
            data.get("certification_url"), "Certification reference link"
        )
        notes = _clean_text(
            data.get("notes"), "Verification notes", 0, 1000
        )

        school.certification_number = certification_number
        school.certification_issuer = certification_issuer
        school.certification_url = certification_url
        school.verification_status = "pending"
        school.verification_notes = (
            "Certification resubmitted; awaiting administrator review."
        )
        school.verified_at = None
        school.verified_by = None
        db.session.add(
            VerificationRecord(
                school_id=school.id,
                status="submitted",
                certification_number=certification_number,
                certification_issuer=certification_issuer,
                certification_url=certification_url,
                submitted_by_id=g.current_user.id,
                notes=notes,
            )
        )
        db.session.commit()
        return jsonify(
            {
                "message": "Certification submitted for review.",
                "school": _owner_school(school),
            }
        )

    @app.get("/api/school/posts")
    @_auth_required(roles={"school", "admin"})
    def get_own_posts():
        if not g.current_user.school_id:
            return jsonify([])
        posts = Post.query.filter_by(
            school_id=g.current_user.school_id
        ).order_by(Post.created_at.desc()).all()
        return jsonify([_public_post(post) for post in posts])

    @app.get("/api/school/reviews")
    @_auth_required(roles={"school", "admin"})
    def get_own_reviews():
        if not g.current_user.school_id:
            return jsonify([])
        reviews = Review.query.filter_by(
            school_id=g.current_user.school_id
        ).order_by(Review.created_at.desc()).all()
        return jsonify([_public_review(review) for review in reviews])

    @app.post("/api/schools/<int:school_id>/posts")
    @_auth_required(roles={"school", "admin"})
    def create_post(school_id):
        school = db.session.get(School, school_id)
        if not school:
            return _json_error("School not found.", 404)
        if (
            g.current_user.role != "admin"
            and g.current_user.school_id != school.id
        ):
            return _json_error(
                "You can only manage posts for your own school.", 403
            )
        data = _get_json()
        title = _clean_text(
            data.get("title"), "Post title", 3, 200, required=True
        )
        content = _clean_text(
            data.get("content") or data.get("text"),
            "Post content",
            3,
            5000,
            required=True,
        )
        post = Post(
            title=title,
            content=content,
            school_id=school.id,
            author_id=g.current_user.id,
        )
        db.session.add(post)
        db.session.commit()
        return (
            jsonify(
                {"message": "Post published.", "post": _public_post(post)}
            ),
            201,
        )

    @app.put("/api/posts/<int:post_id>")
    @_auth_required(roles={"school", "admin"})
    def update_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            return _json_error("Post not found.", 404)
        if (
            g.current_user.role != "admin"
            and g.current_user.school_id != post.school_id
        ):
            return _json_error(
                "You can only manage posts for your own school.", 403
            )
        data = _get_json()
        if "title" in data:
            post.title = _clean_text(
                data.get("title"), "Post title", 3, 200, required=True
            )
        if "content" in data or "text" in data:
            post.content = _clean_text(
                data.get("content") or data.get("text"),
                "Post content",
                3,
                5000,
                required=True,
            )
        db.session.commit()
        return jsonify(
            {"message": "Post updated.", "post": _public_post(post)}
        )

    @app.delete("/api/posts/<int:post_id>")
    @_auth_required(roles={"school", "admin"})
    def delete_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            return _json_error("Post not found.", 404)
        if (
            g.current_user.role != "admin"
            and g.current_user.school_id != post.school_id
        ):
            return _json_error(
                "You can only manage posts for your own school.", 403
            )
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": "Post deleted."})

    @app.get("/api/admin/stats")
    @_auth_required(roles={"admin"})
    def admin_stats():
        return jsonify(
            {
                "schools": School.query.count(),
                "pending_schools": School.query.filter_by(
                    verification_status="pending"
                ).count(),
                "verified_schools": School.query.filter_by(
                    verification_status="verified"
                ).count(),
                "rejected_schools": School.query.filter_by(
                    verification_status="rejected"
                ).count(),
                "users": User.query.count(),
                "reviews": Review.query.count(),
                "hidden_reviews": Review.query.filter_by(is_hidden=True).count(),
                "posts": Post.query.count(),
                "hidden_posts": Post.query.filter_by(is_hidden=True).count(),
            }
        )

    @app.get("/api/admin/schools")
    @_auth_required(roles={"admin"})
    def admin_schools():
        status = _clean_text(
            request.args.get("status", ""), "Status", 0, 20
        )
        query = School.query
        if status:
            if status not in {"pending", "verified", "rejected"}:
                raise ApiError("Unknown verification status.")
            query = query.filter(School.verification_status == status)
        schools = query.order_by(School.created_at.desc()).all()
        return jsonify([_admin_school(school) for school in schools])

    @app.get("/api/admin/schools/<int:school_id>")
    @_auth_required(roles={"admin"})
    def admin_school_detail(school_id):
        school = db.session.get(School, school_id)
        if not school:
            return _json_error("School not found.", 404)
        return jsonify(_admin_school(school))

    def _review_school(school, admin, status, notes):
        school.verification_status = status
        school.verification_notes = notes
        if status == "verified":
            school.verified_at = utcnow()
            school.verified_by = admin.username
        else:
            school.verified_at = None
            school.verified_by = None

        record = (
            VerificationRecord.query.filter_by(school_id=school.id)
            .order_by(VerificationRecord.submitted_at.desc())
            .first()
        )
        if record and record.status in {"submitted", "resubmitted"}:
            record.status = status
            record.reviewed_at = utcnow()
            record.reviewed_by = admin.username
            record.admin_notes = notes
        else:
            db.session.add(
                VerificationRecord(
                    school_id=school.id,
                    status=status,
                    certification_number=school.certification_number,
                    certification_issuer=school.certification_issuer,
                    certification_url=school.certification_url,
                    reviewed_at=utcnow(),
                    reviewed_by=admin.username,
                    admin_notes=notes,
                )
            )
        db.session.commit()

    @app.post("/api/admin/schools/<int:school_id>/verify")
    @_auth_required(roles={"admin"})
    def admin_verify_school(school_id):
        school = db.session.get(School, school_id)
        if not school:
            return _json_error("School not found.", 404)
        data = _get_json() if request.data else {}
        notes = _clean_text(
            data.get("notes"),
            "Verification notes",
            0,
            1000,
        ) or ("Certification details reviewed by an administrator.")
        _review_school(school, g.current_user, "verified", notes)
        return jsonify(
            {
                "message": "School verified.",
                "school": _admin_school(school),
            }
        )

    @app.post("/api/admin/schools/<int:school_id>/reject")
    @_auth_required(roles={"admin"})
    def admin_reject_school(school_id):
        school = db.session.get(School, school_id)
        if not school:
            return _json_error("School not found.", 404)
        data = _get_json() if request.data else {}
        notes = _clean_text(
            data.get("notes"),
            "Rejection reason",
            3,
            1000,
            required=True,
        )
        _review_school(school, g.current_user, "rejected", notes)
        return jsonify(
            {
                "message": "School rejected.",
                "school": _admin_school(school),
            }
        )

    @app.get("/api/admin/users")
    @_auth_required(roles={"admin"})
    def admin_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify(
            [_safe_user(user, include_school=True) for user in users]
        )

    @app.patch("/api/admin/users/<int:user_id>")
    @_auth_required(roles={"admin"})
    def admin_update_user(user_id):
        user = db.session.get(User, user_id)
        if not user:
            return _json_error("User not found.", 404)
        if user.id == g.current_user.id:
            return _json_error(
                "You cannot disable your own administrator account.", 400
            )
        data = _get_json()
        if not isinstance(data.get("is_active"), bool):
            raise ApiError("Provide is_active as true or false.")
        user.is_active = data["is_active"]
        if not user.is_active:
            AuthToken.query.filter_by(user_id=user.id).delete(
                synchronize_session=False
            )
        db.session.commit()
        return jsonify(
            {
                "message": (
                    "User enabled." if user.is_active else "User disabled."
                ),
                "user": _safe_user(user, include_school=True),
            }
        )

    @app.delete("/api/admin/users/<int:user_id>")
    @_auth_required(roles={"admin"})
    def admin_delete_user(user_id):
        user = db.session.get(User, user_id)
        if not user:
            return _json_error("User not found.", 404)
        if user.id == g.current_user.id:
            return _json_error(
                "You cannot delete your own administrator account.", 400
            )
        if user.role == "admin":
            admin_count = User.query.filter_by(
                role="admin", is_active=True
            ).count()
            if admin_count <= 1:
                return _json_error(
                    "At least one active administrator must remain.", 400
                )
        AuthToken.query.filter_by(user_id=user.id).delete(
            synchronize_session=False
        )
        Post.query.filter_by(author_id=user.id).update(
            {"author_id": None}, synchronize_session=False
        )
        VerificationRecord.query.filter_by(
            submitted_by_id=user.id
        ).update({"submitted_by_id": None}, synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted."})

    @app.get("/api/admin/posts")
    @_auth_required(roles={"admin"})
    def admin_posts():
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return jsonify(
            [
                {
                    **_public_post(post),
                    "school_id": post.school_id,
                    "school_name": post.school.name if post.school else "",
                }
                for post in posts
            ]
        )

    @app.patch("/api/admin/posts/<int:post_id>")
    @_auth_required(roles={"admin"})
    def admin_moderate_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            return _json_error("Post not found.", 404)
        data = _get_json()
        if not isinstance(data.get("is_hidden"), bool):
            raise ApiError("Provide is_hidden as true or false.")
        post.is_hidden = data["is_hidden"]
        db.session.commit()
        return jsonify(
            {
                "message": (
                    "Post hidden from public view."
                    if post.is_hidden
                    else "Post restored."
                ),
                "post": {
                    **_public_post(post),
                    "school_id": post.school_id,
                    "school_name": post.school.name if post.school else "",
                },
            }
        )

    @app.get("/api/admin/reviews")
    @_auth_required(roles={"admin"})
    def admin_reviews():
        reviews = Review.query.order_by(Review.created_at.desc()).all()
        return jsonify(
            [
                {
                    **_public_review(review),
                    "school_id": review.school_id,
                    "school_name": review.school.name if review.school else "",
                    "moderated_at": _iso(review.moderated_at),
                    "moderated_by": review.moderated_by or "",
                }
                for review in reviews
            ]
        )

    @app.patch("/api/admin/reviews/<int:review_id>")
    @_auth_required(roles={"admin"})
    def admin_moderate_review(review_id):
        review = db.session.get(Review, review_id)
        if not review:
            return _json_error("Review not found.", 404)
        data = _get_json()
        if not isinstance(data.get("is_hidden"), bool):
            raise ApiError("Provide is_hidden as true or false.")
        review.is_hidden = data["is_hidden"]
        review.moderated_at = utcnow()
        review.moderated_by = g.current_user.username
        db.session.commit()
        return jsonify(
            {
                "message": (
                    "Review hidden from public view."
                    if review.is_hidden
                    else "Review restored."
                ),
                "review": _public_review(review),
            }
        )

    @app.delete("/api/admin/reviews/<int:review_id>")
    @_auth_required(roles={"admin"})
    def admin_delete_review(review_id):
        review = db.session.get(Review, review_id)
        if not review:
            return _json_error("Review not found.", 404)
        db.session.delete(review)
        db.session.commit()
        return jsonify({"message": "Review deleted."})

    @app.post("/api/recommendations")
    def recommendations():
        data = _get_json()
        city = (
            _canonical_city(data.get("city"), required=False)
            if data.get("city")
            else ""
        )
        level = (
            _canonical_level(data.get("level"), required=False)
            if data.get("level")
            else ""
        )
        facilities = _parse_list(
            data.get("facilities"), "Preferred facilities"
        )
        programs = _parse_list(
            data.get("programs"), "Preferred programs"
        )
        verified_only = bool(data.get("verified_only"))
        try:
            limit = int(data.get("limit", 6))
        except (TypeError, ValueError):
            raise ApiError("Limit must be a number from 1 to 10.")
        limit = max(1, min(limit, 10))

        query = School.query.filter(
            School.verification_status != "rejected"
        )
        if verified_only:
            query = query.filter(School.verification_status == "verified")
        schools = query.all()
        if not schools:
            return jsonify(
                {
                    "recommendations": [],
                    "count": 0,
                    "preferences": {
                        "city": city,
                        "level": level,
                        "facilities": facilities,
                        "programs": programs,
                        "verified_only": verified_only,
                    },
                    "fees_considered": False,
                    "fees_note": (
                        "Reliable fee data is not available, so cost was "
                        "not used."
                    ),
                    "ai": {
                        "generated_by_ai": False,
                        "provider": "rule-based",
                        "note": "No matching schools were available.",
                    },
                }
            )

        preferences = {
            "city": city,
            "level": level,
            "facilities": facilities,
            "programs": programs,
        }
        results = [
            _recommendation_for_school(school, preferences)
            for school in schools
        ]
        results.sort(
            key=lambda item: (
                item["score"],
                item["school"]["verified"],
                item["school"]["average_rating"] or 0,
                -item["school"]["id"],
            ),
            reverse=True,
        )
        results = results[:limit]

        ai_data = {
            "generated_by_ai": False,
            "provider": "rule-based",
            "note": (
                "Transparent weighted scoring using available school data. "
                "No external AI service was called."
            ),
        }
        external = _external_ai_summary(preferences, results)
        if external:
            ai_data = {
                "generated_by_ai": True,
                "provider": "openai-compatible",
                "model": external["model"],
                "summary": external["summary"],
                "note": (
                    "The summary was generated by the configured external "
                    "service; scores and reasons come from the local "
                    "rule-based algorithm."
                ),
            }
        else:
            ai_enabled = os.environ.get(
                "EDUCONNECT_ENABLE_AI", ""
            ).lower() in {"1", "true", "yes"}
            if (
                ai_enabled
                and os.environ.get("OPENAI_API_KEY")
                and os.environ.get("OPENAI_MODEL")
            ):
                ai_data["fallback_note"] = (
                    "An external AI service is configured but was "
                    "unavailable; the explainable local scoring was used."
                )

        return jsonify(
            {
                "recommendations": results,
                "count": len(results),
                "preferences": {
                    "city": city,
                    "level": level,
                    "facilities": facilities,
                    "programs": programs,
                    "verified_only": verified_only,
                },
                "fees_considered": False,
                "fees_note": (
                    "Reliable fee data is not available, so cost was not "
                    "used in these recommendations."
                ),
                "ai": ai_data,
            }
        )

    with app.app_context():
        db.create_all()
        ensure_schema()
    
            
        schools_to_add = [
            ("Abadir School", "Addis Ababa", "KG, Primary, Secondary"),
            ("St. John Baptist De La Salle Catholic School","Addis Ababa","Primary, Secondary",),
            ("Sandford International School","Addis Ababa","Primary, Secondary",),
            ("Saint Joseph Catholic School","Adama","Primary, Secondary",),
            ("Hawas Preparatory School", "Adama", "Preparatory"),
            ("Tana Haik Secondary School","Bahir Dar","Secondary, Preparatory",),
            ("Fasilo Secondary School", "Bahir Dar", "Secondary"),
            ("Bahir Dar Academy","Bahir Dar","KG, Primary, Secondary",),
            ("Saint Daniel Comboni School","Hawassa","Secondary, Preparatory",),
            ("Sankofa International School","Hawassa","Nursery, Primary, Secondary",),
        ]
    
        for name, city, level in schools_to_add:
            existing_school = School.query.filter(
                db.func.lower(School.name) == name.lower(),
                db.func.lower(School.city) == city.lower(),
            ).first()
    
            if existing_school is None:
                school = School(
                    name=name,
                    city=city,
                    level=level,
                    verification_status="pending",
                )
                db.session.add(school)
    
        db.session.commit()
    
        school_accounts = [
            {
                "school_name": "Abadir School",
                "username": "abadir_school",
                "email": "abadir.school@example.com",
                "password": "Abadir@2026!",
            },
            {
                "school_name": "St. John Baptist De La Salle Catholic School",
                "username": "st_john_school",
                "email": "st.john.school@example.com",
                "password": "StJohn@2026!",
            },
            {
                "school_name": "Sandford International School",
                "username": "sandford_school",
                "email": "sandford.school@example.com",
                "password": "Sandford@2026!",
            },
            {
                "school_name": "Saint Joseph Catholic School",
                "username": "saint_joseph_school",
                "email": "saint.joseph.school@example.com",
                "password": "Joseph@2026!",
            },
            {
                "school_name": "Hawas Preparatory School",
                "username": "hawas_school",
                "email": "hawas.school@example.com",
                "password": "Hawas@2026!",
            },
            {
                "school_name": "Tana Haik Secondary School",
                "username": "tana_haik_school",
                "email": "tana.haik.school@example.com",
                "password": "TanaHaik@2026!",
            },
            {
                "school_name": "Fasilo Secondary School",
                "username": "fasilo_school",
                "email": "fasilo.school@example.com",
                "password": "Fasilo@2026!",
            },
            {
                "school_name": "Bahir Dar Academy",
                "username": "bahir_dar_academy",
                "email": "bahirdar.academy@example.com",
                "password": "BahirDar@2026!",
            },
            {
                "school_name": "Saint Daniel Comboni School",
                "username": "comboni_school",
                "email": "comboni.school@example.com",
                "password": "Comboni@2026!",
            },
            {
                "school_name": "Sankofa International School",
                "username": "sankofa_school",
                "email": "sankofa.school@example.com",
                "password": "Sankofa@2026!",
            },
        ]
    
        for account in school_accounts:
            school = School.query.filter_by(
                name=account["school_name"]
            ).first()
    
            if school is None:
                app.logger.warning(
                    "School not found: %s",
                    account["school_name"],
                )
                continue
    
            existing_user = User.query.filter(
                db.or_(
                    User.username == account["username"],
                    User.email == account["email"],
                )
            ).first()
    
            if existing_user is None:
                user = User(
                    username=account["username"],
                    email=account["email"],
                    role="school",
                    school_id=school.id,
                    is_active=True,
                )
                user.set_password(account["password"])
                db.session.add(user)
    
            db.session.commit()
    
            app.logger.info(
            "School login accounts: %s",
            User.query.filter_by(role="school").count(),
        )
    
    
    
        app.logger.info(
            "EduConnect database: %s",
            db.engine.url.database,
        )
        app.logger.info(
            "Schools in database: %s",
            School.query.count(),
         )
    
        for name, city, level in schools_to_add:
            school = School.query.filter(
                db.func.lower(School.name) == name.lower(),
                db.func.lower(School.city) == city.lower(),
            ).first()
    
            if school:
                app.logger.info(
                    "School: %s | City: %s | Level: %s | Status: %s",
                    school.name,
                    school.city,
                    school.level,
                    school.verification_status,
                    )
    
    return app
       

if __name__ == "__main__":
    app = create_app()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", str(DEFAULT_PORT))),
        debug=os.environ.get("FLASK_DEBUG", "0").lower()
        in {"1", "true", "yes"},
    )
