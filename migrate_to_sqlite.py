"""
One-time migration script: imports existing JSON config files into the SQLite database.

Usage:
    python migrate_to_sqlite.py [--families families.json] [--daycare daycare.json] [--db daycare.db]
"""

import argparse
import json
import os
from datetime import datetime, date

from database import (
    init_db, DayCareDB, FamilyDB, ParentDB, ChildDB, PublicHolidayDB
)


def load_daycare_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_families_json(path):
    with open(path, "r") as f:
        return json.load(f)


def migrate_daycare(session, data):
    """Insert daycare business record from daycare.json."""
    dc = DayCareDB(
        name=data["name"],
        address=data.get("address", ""),
        town_state_zip=data.get("zip", ""),
        phone=data.get("phone", ""),
        ein=data.get("ein", ""),
        logo=data.get("letterhead", ""),
        email=data.get("email", ""),
        invoice_prefix=data.get("invoice_prefix", ""),
        sender_through=data.get("sender_through", ""),
        sender_email=data.get("sender_email", ""),
        sender_password=data.get("sender_password", ""),
    )
    session.add(dc)
    session.flush()
    print(f"  Imported daycare: {dc.name} (id={dc.id})")
    return dc


def migrate_families(session, data, daycare_id=None):
    """Insert families, parents, and children from families.json."""
    for i, fam_data in enumerate(data.get("families", [])):
        family = FamilyDB(daycare_id=daycare_id)
        session.add(family)
        session.flush()

        for p_data in fam_data.get("parents", []):
            parent = ParentDB(
                family_id=family.id,
                name=p_data["name"],
                email=p_data.get("email", ""),
            )
            session.add(parent)

        for k_data in fam_data.get("kids", []):
            dob = None
            if k_data.get("dob"):
                dob = datetime.strptime(k_data["dob"], "%Y-%m-%d").date()

            child = ChildDB(
                family_id=family.id,
                name=k_data["name"],
                dob=dob,
                schedule=k_data.get("attendance", [0, 1, 2, 3, 4]),
                day_rate=k_data.get("fee", 0.0),
            )
            session.add(child)

        session.flush()
        parents_str = ", ".join(p["name"] for p in fam_data.get("parents", []))
        kids_str = ", ".join(k["name"] for k in fam_data.get("kids", []))
        print(f"  Family {family.id}: parents=[{parents_str}], children=[{kids_str}]")


def migrate_holidays(session, holidays):
    """Insert public holidays. Accepts list of date strings (YYYY-MM-DD)."""
    for h in holidays:
        d = datetime.strptime(h, "%Y-%m-%d").date()
        existing = session.query(PublicHolidayDB).filter_by(date=d).first()
        if not existing:
            session.add(PublicHolidayDB(date=d))
    session.flush()
    print(f"  Imported {len(holidays)} public holidays")


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to SQLite")
    parser.add_argument("--families", default="families.json", help="Path to families JSON file")
    parser.add_argument("--daycare", default="daycare.json", help="Path to daycare JSON config file")
    parser.add_argument("--db", default="daycare.db", help="SQLite database path")
    args = parser.parse_args()

    # Remove old DB if it exists so we get a clean migration
    if os.path.exists(args.db):
        backup = args.db + ".bak"
        os.rename(args.db, backup)
        print(f"Backed up existing DB to {backup}")

    engine, session = init_db(args.db)

    try:
        # Migrate daycare config
        daycare_id = None
        if os.path.exists(args.daycare):
            print(f"Migrating daycare config from {args.daycare}...")
            dc_data = load_daycare_json(args.daycare)
            dc = migrate_daycare(session, dc_data)
            daycare_id = dc.id
        else:
            print(f"Warning: {args.daycare} not found, skipping daycare config")

        # Migrate families
        if os.path.exists(args.families):
            print(f"Migrating families from {args.families}...")
            fam_data = load_families_json(args.families)
            migrate_families(session, fam_data, daycare_id)
        else:
            print(f"Warning: {args.families} not found, skipping families")

        # Migrate public holidays (hardcoded from daycare.py for now)
        print("Migrating public holidays...")
        holidays = [
            "2024-09-02",
            "2024-11-28",
            "2024-11-29",
            "2024-12-25",
            "2024-12-30",
            "2024-12-31",
            "2025-01-01",
            "2025-02-17",
            "2025-02-18",
            "2025-02-19",
            "2025-02-20",
            "2025-02-21",
        ]
        migrate_holidays(session, holidays)

        session.commit()
        print(f"\nMigration complete! Database: {args.db}")

    except Exception as e:
        session.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
