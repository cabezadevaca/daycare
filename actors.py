"""
Backward-compatible aliases for the DB-backed model classes.

All other modules can keep doing:
    from actors import DayCare, Family, Parent, Child
"""

from database import DayCareDB as DayCare
from database import FamilyDB as Family
from database import ParentDB as Parent
from database import ChildDB as Child
