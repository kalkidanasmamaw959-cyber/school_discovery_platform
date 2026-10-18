from backend.app import app
from backend.models import db, School


schools_to_add = [
    # Bahir Dar
    {"name": "SOS School", "city": "Bahir Dar",
     "location": "Kebele 13, Bahir Dar"},
    {"name": "Bahir Dar Academy", "city": "Bahir Dar",
     "location": "Kebele 16, Bahir Dar"},
    {"name": "Catholic School", "city": "Bahir Dar",
     "location": ""},
    {"name": "Eshet School", "city": "Bahir Dar",
     "location": "Kebele 16, Bahir Dar"},
    {"name": "Abune Gorgorios School", "city": "Bahir Dar",
     "location": ""},

    # Addis Ababa
    {"name": "Abune Gorgorios School", "city": "Addis Ababa",
     "location": ""},
    {"name": "Cathedral School", "city": "Addis Ababa",
     "location": ""},
    {"name": "Safari School", "city": "Addis Ababa",
     "location": ""},
    {"name": "Green School", "city": "Addis Ababa",
     "location": ""},
    {"name": "Ethio Excellence Academy", "city": "Addis Ababa",
     "location": ""},

    # Hawassa
    {"name": "Union SOS", "city": "Hawassa",
     "location": ""},
    {"name": "EPS", "city": "Hawassa",
     "location": ""},
    {"name": "Comboni School", "city": "Hawassa",
     "location": ""},
    {"name": "Kdus Gebrel School", "city": "Hawassa",
     "location": ""},

    # Adama
    {"name": "Makko Billi School", "city": "Adama",
     "location": ""},
]


def seed_schools():
    added = 0
    skipped = 0

    with app.app_context():
        for school_data in schools_to_add:
            existing_school = School.query.filter_by(
                name=school_data["name"],
                city=school_data["city"]
            ).first()

            if existing_school:
                skipped += 1
                continue

            school = School(
                name=school_data["name"],
                city=school_data["city"],
                location=school_data["location"],
                verification_status="pending"
            )

            db.session.add(school)
            added += 1

        db.session.commit()

    print(f"Schools added: {added}")
    print(f"Existing schools skipped: {skipped}")


def check_database():
    with app.app_context():
        print("DATABASE LOCATION:", db.engine.url.database)
        print("SCHOOLS IN DATABASE:", School.query.count())


if __name__ == "__main__":
    check_database()
