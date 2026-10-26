"""End-to-end API tests for EduConnect Ethiopia.

Run from the project root:

    python -m pytest -q
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.app import create_app
from backend.models import AuthToken, Post, School, User, db


@pytest.fixture()
def app(tmp_path):
    database = tmp_path / "test_educonnect.db"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        }
    )
    with application.app_context():
        schools = [
            School(
                name="Test Bahir Dar School",
                city="Bahir Dar",
                level="Primary & Secondary",
                location="Kebele 1, Bahir Dar",
                description="A test school.",
                phone="+251582200000",
                email="bd@test.example",
                website="https://bd.test.example",
                programs='["Primary Education", "Secondary Education"]',
                facilities='["Library", "Computer Lab"]',
                verification_status="verified",
                certification_number="MOE-001",
                certification_issuer="Ministry of Education",
            ),
            School(
                name="Test Addis School",
                city="Addis Ababa",
                level="Secondary",
                location="Bole, Addis Ababa",
                phone="+251911000000",
                email="aa@test.example",
                programs='["Secondary Education"]',
                facilities='["Science Lab"]',
                verification_status="pending",
            ),
            School(
                name="Rejected School",
                city="Hawassa",
                level="Primary",
                verification_status="rejected",
            ),
        ]
        admin = User(
            username="admin",
            email="admin@test.example",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123")
        db.session.add_all(schools + [admin])
        db.session.commit()
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def register(
    client,
    username="schoolone",
    school_name="New School",
    password="StrongPass123",
    city="Adama",
):
    response = client.post(
        "/api/auth/register",
        json={
            "school_name": school_name,
            "city": city,
            "level": "Primary",
            "location": "Adama, Ethiopia",
            "school_email": f"{username}@school.example",
            "phone": "+251911222333",
            "website": "https://school.example",
            "telegram": "https://t.me/school",
            "username": username,
            "password": password,
            "confirm_password": password,
            "certification_number": "MOE-TEST-123",
            "certification_issuer": "Ministry of Education",
            "certification_url": "https://moe.example/certificate",
        },
    )
    return response


def login(client, identifier, password):
    return client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_and_school_filters(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["database"] == "connected"

    schools = client.get("/api/schools").get_json()
    assert len(schools) == 2
    assert not any(item["name"] == "Rejected School" for item in schools)

    bahir = client.get("/api/schools?city=Bahir%20Dar").get_json()
    assert len(bahir) == 1
    assert bahir[0]["name"] == "Test Bahir Dar School"

    search = client.get("/api/schools?search=Addis").get_json()
    assert len(search) == 1
    assert search[0]["name"] == "Test Addis School"

    level = client.get("/api/schools?level=Secondary").get_json()
    assert {item["name"] for item in level} == {
        "Test Bahir Dar School",
        "Test Addis School",
    }

    verified = client.get("/api/schools?verified=true").get_json()
    assert [item["name"] for item in verified] == ["Test Bahir Dar School"]

    missing = client.get("/api/schools/9999")
    assert missing.status_code == 404


def test_public_school_does_not_expose_certification_or_users(client):
    school = client.get("/api/schools?city=Bahir%20Dar").get_json()[0]
    assert "certification_number" not in school
    assert "users" not in school
    assert school["verified"] is True
    assert school["programs"] == [
        "Primary Education",
        "Secondary Education",
    ]
    assert school["facilities"] == ["Library", "Computer Lab"]


def test_registration_validation_and_success(app, client):
    bad = register(client, password="short")
    assert bad.status_code == 400

    mismatch = client.post(
        "/api/auth/register",
        json={
            "school_name": "Mismatch School",
            "city": "Adama",
            "level": "Primary",
            "location": "Adama",
            "school_email": "mismatch@test.example",
            "phone": "+251911222333",
            "username": "mismatch",
            "password": "StrongPass123",
            "confirm_password": "DifferentPass123",
            "certification_number": "MOE-999",
        },
    )
    assert mismatch.status_code == 400

    response = register(client)
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["school"]["verification_status"] == "pending"
    assert payload["school"]["verified"] is False
    assert "certification_number" in payload["school"]
    assert "password" not in payload["user"]
    assert "password_hash" not in payload["user"]
    assert payload["token"]

    with app.app_context():
        user = User.query.filter_by(username="schoolone").first()
        assert user is not None
        assert user.password_hash != "StrongPass123"
        assert user.check_password("StrongPass123")
        school = db.session.get(School, user.school_id)
        assert school.verification_status == "pending"
        assert school.certification_number == "MOE-TEST-123"

    duplicate_username = register(client, username="schoolone")
    assert duplicate_username.status_code == 409

    duplicate_school = register(
        client, username="schooltwo", school_name="New School"
    )
    assert duplicate_school.status_code == 409


def test_registration_can_claim_seeded_school_once(client):
    first = register(
        client,
        username="claimer",
        school_name="Test Addis School",
        city="Addis Ababa",
    )
    assert first.status_code == 201
    assert first.get_json()["school"]["city"] == "Addis Ababa"

    second = register(
        client,
        username="claimer2",
        school_name="Test Addis School",
        city="Addis Ababa",
    )
    assert second.status_code == 409


def test_login_me_logout(app, client):
    wrong = login(client, "admin", "wrong")
    assert wrong.status_code == 401

    success = login(client, "admin@test.example", "AdminPass123")
    assert success.status_code == 200
    token = success.get_json()["token"]
    assert success.get_json()["user"]["role"] == "admin"
    assert success.get_json()["redirect"] == "admin.html"
    assert "password_hash" not in success.get_json()["user"]

    me = client.get("/api/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "admin"

    logout = client.post("/api/auth/logout", headers=bearer(token))
    assert logout.status_code == 200
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401

    with app.app_context():
        assert AuthToken.query.count() == 0


def test_school_ownership_profile_posts_and_reviews(app, client):
    first = register(
        client, username="ownerone", school_name="Owner One School"
    ).get_json()
    second = register(
        client, username="ownertwo", school_name="Owner Two School"
    ).get_json()

    first_headers = bearer(first["token"])
    second_headers = bearer(second["token"])
    first_school_id = first["school"]["id"]

    profile = client.put(
        "/api/school/me",
        json={
            "name": "Owner One School",
            "city": "Adama",
            "level": "Primary & Secondary",
            "location": "Adama",
            "email": "ownerone@school.example",
            "phone": "+251911222333",
            "website": "",
            "telegram": "",
            "description": "Updated description",
            "programs": ["Primary Education", "Secondary Education"],
            "facilities": ["Library", "Playground"],
        },
        headers=first_headers,
    )
    assert profile.status_code == 200
    assert profile.get_json()["school"]["facilities"] == [
        "Library",
        "Playground",
    ]
    assert profile.get_json()["school"]["verification_status"] == "pending"

    forbidden_post = client.post(
        f"/api/schools/{first_school_id}/posts",
        json={"title": "Not mine", "content": "Blocked"},
        headers=second_headers,
    )
    assert forbidden_post.status_code == 403

    created_post = client.post(
        f"/api/schools/{first_school_id}/posts",
        json={"title": "Open day", "content": "Visit us on Saturday."},
        headers=first_headers,
    )
    assert created_post.status_code == 201
    post_id = created_post.get_json()["post"]["id"]

    public_posts = client.get(
        f"/api/schools/{first_school_id}/posts"
    ).get_json()
    assert public_posts[0]["title"] == "Open day"

    other_delete = client.delete(
        f"/api/posts/{post_id}", headers=second_headers
    )
    assert other_delete.status_code == 403

    review = client.post(
        f"/api/schools/{first_school_id}/reviews",
        json={"name": "Parent", "rating": 5, "comment": "Very helpful."},
    )
    assert review.status_code == 201

    invalid_rating = client.post(
        f"/api/schools/{first_school_id}/reviews",
        json={"name": "Parent", "rating": 9, "comment": "Bad input."},
    )
    assert invalid_rating.status_code == 400

    detail = client.get(f"/api/schools/{first_school_id}").get_json()
    assert detail["review_count"] == 1
    assert detail["average_rating"] == 5.0

    own_posts = client.get("/api/school/posts", headers=first_headers).get_json()
    assert len(own_posts) == 1

    assert (
        client.get("/api/school/me", headers=first_headers).status_code
        == 200
    )
    assert (
        client.get("/api/admin/stats", headers=first_headers).status_code
        == 403
    )


def test_admin_verification_and_moderation(app, client):
    school_registration = register(
        client, username="moderated", school_name="Moderated School"
    ).get_json()
    school_id = school_registration["school"]["id"]
    school_headers = bearer(school_registration["token"])

    admin_token = login(
        client, "admin", "AdminPass123"
    ).get_json()["token"]
    admin_headers = bearer(admin_token)

    assert (
        client.get("/api/admin/schools", headers=school_headers).status_code
        == 403
    )
    admin_schools = client.get(
        "/api/admin/schools?status=pending", headers=admin_headers
    )
    assert admin_schools.status_code == 200
    assert any(
        item["id"] == school_id for item in admin_schools.get_json()
    )

    verified = client.post(
        f"/api/admin/schools/{school_id}/verify",
        json={"notes": "Certificate checked against submitted reference."},
        headers=admin_headers,
    )
    assert verified.status_code == 200
    verified_school = verified.get_json()["school"]
    assert verified_school["verification_status"] == "verified"
    assert verified_school["verified"] is True
    assert verified_school["verification_records"][0]["status"] == "verified"

    rejected = client.post(
        f"/api/admin/schools/{school_id}/reject",
        json={"notes": "Certificate could not be confirmed."},
        headers=admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.get_json()["school"]["verification_status"] == "rejected"
    assert client.get(f"/api/schools/{school_id}").status_code == 404

    resubmitted = client.post(
        "/api/school/verification",
        json={
            "certification_number": "MOE-TEST-456",
            "certification_issuer": "Ministry of Education",
            "certification_url": "https://moe.example/new-certificate",
            "notes": "A clearer certificate copy was requested.",
        },
        headers=school_headers,
    )
    assert resubmitted.status_code == 200
    assert resubmitted.get_json()["school"]["verification_status"] == "pending"

    post = client.post(
        f"/api/schools/{school_id}/posts",
        json={"title": "News", "content": "A public announcement."},
        headers=school_headers,
    ).get_json()["post"]
    hidden_post = client.patch(
        f"/api/admin/posts/{post['id']}",
        json={"is_hidden": True},
        headers=admin_headers,
    )
    assert hidden_post.status_code == 200
    assert client.get(f"/api/schools/{school_id}/posts").get_json() == []

    review = client.post(
        f"/api/schools/{school_id}/reviews",
        json={"name": "Family", "rating": 4, "comment": "Good."},
    ).get_json()["review"]
    hidden_review = client.patch(
        f"/api/admin/reviews/{review['id']}",
        json={"is_hidden": True},
        headers=admin_headers,
    )
    assert hidden_review.status_code == 200
    detail = client.get(f"/api/schools/{school_id}").get_json()
    assert detail["reviews"] == []
    assert detail["review_count"] == 0

    users = client.get("/api/admin/users", headers=admin_headers).get_json()
    school_user = next(
        user for user in users if user["username"] == "moderated"
    )
    disabled = client.patch(
        f"/api/admin/users/{school_user['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert disabled.status_code == 200
    assert (
        client.get("/api/auth/me", headers=school_headers).status_code == 401
    )


def test_admin_cannot_disable_self(client):
    admin_token = login(
        client, "admin", "AdminPass123"
    ).get_json()["token"]
    admin_headers = bearer(admin_token)
    me = client.get("/api/auth/me", headers=admin_headers).get_json()
    response = client.patch(
        f"/api/admin/users/{me['user']['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_recommendations_are_explainable_and_honest(client):
    response = client.post(
        "/api/recommendations",
        json={
            "city": "Bahir Dar",
            "level": "Primary",
            "facilities": ["Library"],
            "programs": ["Primary"],
            "limit": 5,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["fees_considered"] is False
    assert payload["ai"]["generated_by_ai"] is False
    assert payload["recommendations"]

    top = payload["recommendations"][0]
    assert top["school"]["name"] == "Test Bahir Dar School"
    assert 0 <= top["score"] <= 100
    assert top["reasons"]
    assert any(
        reason["factor"] == "city" and reason["status"] == "matched"
        for reason in top["reasons"]
    )
    assert any(
        reason["factor"] == "verification"
        for reason in top["reasons"]
    )

    verified_only = client.post(
        "/api/recommendations",
        json={"verified_only": True, "limit": 10},
    ).get_json()
    assert all(
        item["school"]["verified"]
        for item in verified_only["recommendations"]
    )

    invalid = client.post(
        "/api/recommendations",
        json={"city": "Not A City"},
    )
    assert invalid.status_code == 400

    missing_data = client.post(
        "/api/recommendations",
        json={
            "city": "Addis Ababa",
            "level": "Secondary",
            "facilities": ["Library"],
        },
    ).get_json()
    addis = next(
        item
        for item in missing_data["recommendations"]
        if item["school"]["name"] == "Test Addis School"
    )
    facility_reason = next(
        reason
        for reason in addis["reasons"]
        if reason["factor"] == "facilities"
    )
    assert facility_reason["status"] == "unmatched"
    assert "website" in addis["missing_information"]
    assert "reviews" in addis["missing_information"]


def test_legacy_database_is_migrated_without_losing_rows(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE school (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            city VARCHAR(100) NOT NULL,
            level VARCHAR(100),
            location VARCHAR(255),
            description TEXT,
            phone VARCHAR(30),
            email VARCHAR(150),
            website VARCHAR(255),
            telegram VARCHAR(255),
            verification_status VARCHAR(20) NOT NULL
        );
        CREATE TABLE user (
            id INTEGER NOT NULL PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            school_id INTEGER,
            FOREIGN KEY (school_id) REFERENCES school (id)
        );
        CREATE TABLE post (
            id INTEGER NOT NULL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME,
            school_id INTEGER NOT NULL,
            FOREIGN KEY (school_id) REFERENCES school (id)
        );
        CREATE TABLE review (
            id INTEGER NOT NULL PRIMARY KEY,
            reviewer_name VARCHAR(100) NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at DATETIME,
            school_id INTEGER NOT NULL,
            FOREIGN KEY (school_id) REFERENCES school (id)
        );
        INSERT INTO school (
            id, name, city, level, location, verification_status
        ) VALUES (
            1, 'Legacy School', 'Adama', 'Primary', 'Old address', 'pending'
        );
        INSERT INTO post (
            id, title, content, school_id
        ) VALUES (1, 'Old post', 'Existing content', 1);
        """
    )
    connection.commit()
    connection.close()

    migrated_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "legacy-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        }
    )
    with migrated_app.app_context():
        assert School.query.count() == 1
        school = School.query.first()
        assert school.name == "Legacy School"
        assert school.location == "Old address"
        assert school.programs_list == []
        assert Post.query.count() == 1
        columns = {
            row[1]
            for row in db.session.execute(
                text("PRAGMA table_info(school)")
            ).fetchall()
        }
        assert {"programs", "facilities", "certification_number"} <= columns

    response = migrated_app.test_client().get("/api/schools")
    assert response.status_code == 200
    assert response.get_json()[0]["name"] == "Legacy School"


def test_remaining_routes_json_errors_and_cors_rejection(client):
    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert "Addis Ababa" in meta.get_json()["cities"]
    assert meta.get_json()["fees_available"] is False

    owner = register(
        client, username="routeowner", school_name="Route School"
    ).get_json()
    owner_headers = bearer(owner["token"])
    school_id = owner["school"]["id"]

    created = client.post(
        f"/api/schools/{school_id}/posts",
        json={"title": "Initial title", "content": "Initial content."},
        headers=owner_headers,
    ).get_json()["post"]
    updated = client.put(
        f"/api/posts/{created['id']}",
        json={"title": "Updated title", "content": "Updated content."},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["post"]["title"] == "Updated title"

    review = client.post(
        f"/api/schools/{school_id}/reviews",
        json={"name": "Route Parent", "rating": 4, "comment": "Useful."},
    ).get_json()["review"]

    admin_headers = bearer(
        login(client, "admin", "AdminPass123").get_json()["token"]
    )
    detail = client.get(
        f"/api/admin/schools/{school_id}", headers=admin_headers
    )
    assert detail.status_code == 200
    assert detail.get_json()["users"][0]["username"] == "routeowner"
    assert client.get(
        "/api/admin/posts", headers=admin_headers
    ).status_code == 200
    admin_reviews = client.get(
        "/api/admin/reviews", headers=admin_headers
    ).get_json()
    assert any(item["id"] == review["id"] for item in admin_reviews)

    deleted_review = client.delete(
        f"/api/admin/reviews/{review['id']}", headers=admin_headers
    )
    assert deleted_review.status_code == 200
    assert (
        client.get(f"/api/schools/{school_id}").get_json()["review_count"]
        == 0
    )

    second = register(
        client, username="deletable", school_name="Deletable School"
    ).get_json()
    second_headers = bearer(second["token"])
    second_id = second["user"]["id"]
    assert client.delete(
        f"/api/admin/users/{second_id}", headers=admin_headers
    ).status_code == 200
    assert client.get("/api/auth/me", headers=second_headers).status_code == 401

    own_delete = client.delete(
        f"/api/posts/{created['id']}", headers=owner_headers
    )
    assert own_delete.status_code == 200
    assert client.get(f"/api/schools/{school_id}/posts").get_json() == []

    method_error = client.post("/api/schools/1")
    assert method_error.status_code == 405
    assert method_error.is_json
    missing_error = client.get("/api/does-not-exist")
    assert missing_error.status_code == 404
    assert missing_error.is_json

    rejected_origin = client.get(
        "/api/schools", headers={"Origin": "http://evil.example"}
    )
    assert rejected_origin.headers.get("Access-Control-Allow-Origin") is None


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://127.0.0.1:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5502",
        "http://localhost:5502",
    ],
)
def test_cors_preflight_allows_local_frontend(client, origin):
    response = client.options(
        "/api/schools",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("Access-Control-Allow-Origin") == origin


def test_cors_preflight_allows_authorization_header_for_live_server(client):
    response = client.options(
        "/api/school/me",
        headers={
            "Origin": "http://127.0.0.1:5502",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code in (200, 204)
    assert (
        response.headers.get("Access-Control-Allow-Origin")
        == "http://127.0.0.1:5502"
    )
    allowed = response.headers.get(
        "Access-Control-Allow-Headers", ""
    ).lower()
    assert "authorization" in allowed or "*" in allowed


def test_frontend_pages_and_api_config_are_served(client):
    pages = [
        "/app/",
        "/app/index.html",
        "/app/school-login.html",
        "/app/school-register.html",
        "/app/dashboard.html",
        "/app/admin.html",
    ]
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, path

    config = client.get("/app/api-config.js")
    assert config.status_code == 200
    assert b"EDUCONNECT_API_BASE" in config.data
    assert b'"5000"' in config.data
    assert b'"5001"' in config.data


def test_relative_database_path_resolves_from_project_root(
    tmp_path, monkeypatch
):
    from backend import app as app_module

    (tmp_path / "instance").mkdir()
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setenv("DATABASE_PATH", "instance/portable.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path.parent)

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "portable-path-test-secret",
        }
    )
    with application.app_context():
        actual = Path(db.engine.url.database).resolve()

    assert actual == (tmp_path / "instance" / "portable.db").resolve()
