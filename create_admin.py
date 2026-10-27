import argparse
import getpass
import os
import sys
from pathlib import Path

try:
    from .app import (
        _validate_email,
        _validate_password,
        _validate_username,
        create_app,
    )
    from .models import AuthToken, User, db
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.app import (  
        _validate_email,
        _validate_password,
        _validate_username,
        create_app,
    )
    from backend.models import AuthToken, User, db  


def read_password():
    password = os.environ.get("ADMIN_PASSWORD")
    if password:
        return _validate_password(password)
    first = getpass.getpass("Admin password (min 8 characters): ")
    second = getpass.getpass("Repeat admin password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    return _validate_password(first)


def main():
    parser = argparse.ArgumentParser(
        description="Create or promote an EduConnect administrator."
    )
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", help="Required when creating a new admin.")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promote an existing user instead of creating a new one.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Also reset the password of an existing/promoted user.",
    )
    args = parser.parse_args()

    username = _validate_username(args.username)
    app = create_app()

    with app.app_context():
        user = User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()

        if user:
            if not args.promote and not args.reset_password:
                raise SystemExit(
                    "That user already exists. Re-run with --promote to make "
                    "them an administrator or --reset-password to reset the "
                    "password only."
                )
            if args.reset_password:
                user.set_password(read_password())
                AuthToken.query.filter_by(user_id=user.id).delete(
                    synchronize_session=False
                )
            if args.promote:
                user.role = "admin"
                user.school_id = None
            user.is_active = True
            db.session.commit()
            if args.promote:
                print(
                    f"Promoted existing user '{user.username}' to "
                    "administrator."
                )
            if args.reset_password:
                print(f"Reset the password for '{user.username}'.")
            print("Sign in at /app/school-login.html with the normal login form.")
            return

        if not args.email:
            raise SystemExit("--email is required when creating a new admin.")
        email = _validate_email(args.email, "Admin email")
        duplicate_email = User.query.filter(
            db.func.lower(User.email) == email.lower()
        ).first()
        if duplicate_email:
            raise SystemExit("That email is already used by another account.")

        password = read_password()
        admin = User(
            username=username,
            email=email,
            role="admin",
            school_id=None,
            is_active=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created administrator '{admin.username}'.")
        print("Sign in at /app/school-login.html with the normal login form.")


if __name__ == "__main__":
    main()
