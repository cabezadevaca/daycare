#!/usr/bin/env python3
"""
CLI utility to manage daycare user accounts.

Usage:
    python3 manage_users.py add-admin <username> <password>
    python3 manage_users.py add-parent <username> <password> <family_id>
    python3 manage_users.py list
    python3 manage_users.py delete <username>
"""

import sys

from werkzeug.security import generate_password_hash
from database import init_db, UserDB


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    engine, session = init_db()
    cmd = sys.argv[1]

    if cmd == "add-admin":
        if len(sys.argv) != 4:
            print("Usage: manage_users.py add-admin <username> <password>")
            sys.exit(1)
        username, password = sys.argv[2], sys.argv[3]
        if session.query(UserDB).filter_by(username=username).first():
            print(f"Error: username '{username}' already exists.")
            sys.exit(1)
        user = UserDB(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin",
        )
        session.add(user)
        session.commit()
        print(f"Admin user '{username}' created (id={user.id}).")

    elif cmd == "add-parent":
        if len(sys.argv) != 5:
            print("Usage: manage_users.py add-parent <username> <password> <family_id>")
            sys.exit(1)
        username, password, family_id = sys.argv[2], sys.argv[3], int(sys.argv[4])
        if session.query(UserDB).filter_by(username=username).first():
            print(f"Error: username '{username}' already exists.")
            sys.exit(1)
        user = UserDB(
            username=username,
            password_hash=generate_password_hash(password),
            role="parent",
            family_id=family_id,
        )
        session.add(user)
        session.commit()
        print(f"Parent user '{username}' created (id={user.id}, family={family_id}).")

    elif cmd == "list":
        users = session.query(UserDB).all()
        if not users:
            print("No users found.")
        for u in users:
            fam = f", family_id={u.family_id}" if u.family_id else ""
            print(f"  id={u.id}  username={u.username!r}  role={u.role}{fam}")

    elif cmd == "delete":
        if len(sys.argv) != 3:
            print("Usage: manage_users.py delete <username>")
            sys.exit(1)
        username = sys.argv[2]
        user = session.query(UserDB).filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)
        session.delete(user)
        session.commit()
        print(f"User '{username}' deleted.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
