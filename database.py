"""
SQLAlchemy ORM models for the daycare billing application.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    ForeignKey, JSON, Text, event
)
from sqlalchemy.orm import (
    declarative_base, relationship, sessionmaker, Session, reconstructor
)


Base = declarative_base()


class UserDB(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="parent")  # 'admin' or 'parent'
    family_id = Column(Integer, ForeignKey("family.id"), nullable=True)

    family = relationship("FamilyDB", backref="users")

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"User(id={self.id}, username={self.username!r}, role={self.role!r})"


class DayCareDB(Base):
    __tablename__ = "daycare"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    address = Column(String)
    town_state_zip = Column(String)
    phone = Column(String)
    ein = Column(String)
    logo = Column(String)
    email = Column(String)
    invoice_prefix = Column(String)
    sender_through = Column(String)
    sender_email = Column(String)
    sender_password = Column(String)

    families = relationship("FamilyDB", back_populates="daycare", cascade="all, delete-orphan")

    @staticmethod
    def load_from_db(session):
        """Load the first (and typically only) daycare record."""
        return session.query(DayCareDB).first()

    def add_family(self, family):
        if family not in self.families:
            self.families.append(family)

    def add_child(self, child):
        pass

    @property
    def _parents(self):
        parents = set()
        for fam in self.families:
            for p in fam.parents:
                parents.add(p)
        return parents

    def __repr__(self):
        return f"DayCare(id={self.id}, name={self.name!r})"


class FamilyDB(Base):
    __tablename__ = "family"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daycare_id = Column(Integer, ForeignKey("daycare.id"), nullable=True)

    daycare = relationship("DayCareDB", back_populates="families")
    parents = relationship("ParentDB", back_populates="family", cascade="all, delete-orphan")
    children = relationship("ChildDB", back_populates="family", cascade="all, delete-orphan")
    invoices = relationship("InvoiceDB", back_populates="family", cascade="all, delete-orphan")

    def add_parent(self, parent):
        if parent not in self.parents:
            self.parents.append(parent)

    def add_child(self, child):
        if child not in self.children:
            self.children.append(child)

    def __repr__(self):
        return f"Family(id={self.id})"


class ParentDB(Base):
    __tablename__ = "parent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)

    family = relationship("FamilyDB", back_populates="parents")

    def __repr__(self):
        return self.name


class ChildDB(Base):
    __tablename__ = "child"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    name = Column(String, nullable=False)
    dob = Column(Date, nullable=True)
    # Schedule stored as JSON list of weekday ints, e.g. [0,1,2,3,4]
    schedule = Column(JSON, nullable=False, default=list)
    day_rate = Column(Float, nullable=False, default=0.0)

    family = relationship("FamilyDB", back_populates="children")
    line_items = relationship("InvoiceLineItemDB", back_populates="child", cascade="all, delete-orphan")

    @property
    def child_schedule(self):
        """Alias for schedule — used by timetable.py / invoice.py."""
        return self.schedule

    @child_schedule.setter
    def child_schedule(self, value):
        self.schedule = value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_runtime_fields()

    @reconstructor
    def _init_on_load(self):
        self._init_runtime_fields()

    def _init_runtime_fields(self):
        # Runtime fields used during invoice generation (not persisted)
        self.current_month = None
        self.current_fee = 0
        self.current_attendance_dates = []

    def __repr__(self):
        return f"Child(id={self.id}, name={self.name!r})"


class PublicHolidayDB(Base):
    __tablename__ = "public_holiday"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    label = Column(String, nullable=True)

    def __repr__(self):
        return f"PublicHoliday({self.date}, {self.label!r})"


class InvoiceDB(Base):
    __tablename__ = "invoice"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    total_fee = Column(Float, nullable=False, default=0.0)
    total_days = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, nullable=False, default=datetime.now)
    pdf_path = Column(String, nullable=True)

    family = relationship("FamilyDB", back_populates="invoices")
    line_items = relationship("InvoiceLineItemDB", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Invoice(id={self.id}, family={self.family_id}, {self.month}/{self.year}, ${self.total_fee:.2f})"


class InvoiceLineItemDB(Base):
    __tablename__ = "invoice_line_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoice.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("child.id"), nullable=False)
    days_count = Column(Integer, nullable=False, default=0)
    # Attendance dates stored as JSON list of day-of-month strings, e.g. ["01","02","05"]
    attendance_dates = Column(JSON, nullable=True)
    day_rate = Column(Float, nullable=False, default=0.0)
    fee = Column(Float, nullable=False, default=0.0)

    invoice = relationship("InvoiceDB", back_populates="line_items")
    child = relationship("ChildDB", back_populates="line_items")

    def __repr__(self):
        return f"LineItem(child={self.child_id}, days={self.days_count}, fee=${self.fee:.2f})"


# ---------------------------------------------------------------------------
# History / audit tables
# ---------------------------------------------------------------------------

class FamilyHistoryDB(Base):
    __tablename__ = "family_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)  # 'insert', 'update', 'delete'
    changed_at = Column(DateTime, nullable=False, default=datetime.now)

    family_id = Column(Integer, nullable=False)
    daycare_id = Column(Integer, nullable=True)

    def __repr__(self):
        return (f"FamilyHistory(id={self.id}, change={self.change_id!r}, "
                f"op={self.operation!r}, family={self.family_id})")


class ParentHistoryDB(Base):
    __tablename__ = "parent_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.now)

    parent_id = Column(Integer, nullable=False)
    family_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)

    def __repr__(self):
        return (f"ParentHistory(id={self.id}, change={self.change_id!r}, "
                f"op={self.operation!r}, parent={self.parent_id}, name={self.name!r})")


class ChildHistoryDB(Base):
    __tablename__ = "child_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.now)

    child_id = Column(Integer, nullable=False)
    family_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    dob = Column(Date, nullable=True)
    schedule = Column(JSON, nullable=True)
    day_rate = Column(Float, nullable=True)

    def __repr__(self):
        return (f"ChildHistory(id={self.id}, change={self.change_id!r}, "
                f"op={self.operation!r}, child={self.child_id}, name={self.name!r})")


# ---------------------------------------------------------------------------
# Auto-snapshot logic  (connection-level inserts, safe during flush)
# ---------------------------------------------------------------------------

_TRACKED_CLASSES = (FamilyDB, ParentDB, ChildDB)
_fam_hist = FamilyHistoryDB.__table__
_par_hist = ParentHistoryDB.__table__
_chi_hist = ChildHistoryDB.__table__


def _make_change_id():
    return str(uuid.uuid4())


def _conn_insert_family_hist(conn, change_id, op, now, fam):
    conn.execute(_fam_hist.insert().values(
        change_id=change_id, operation=op, changed_at=now,
        family_id=fam.id, daycare_id=fam.daycare_id,
    ))


def _conn_insert_parent_hist(conn, change_id, op, now, p):
    conn.execute(_par_hist.insert().values(
        change_id=change_id, operation=op, changed_at=now,
        parent_id=p.id, family_id=p.family_id,
        name=p.name, email=p.email,
    ))


def _conn_insert_child_hist(conn, change_id, op, now, c):
    import json as _json
    sched = _json.dumps(c.schedule) if c.schedule is not None else None
    conn.execute(_chi_hist.insert().values(
        change_id=change_id, operation=op, changed_at=now,
        child_id=c.id, family_id=c.family_id,
        name=c.name, dob=c.dob,
        schedule=sched, day_rate=c.day_rate,
    ))


def _snapshot_family_members(conn, change_id, now, family):
    """Write snapshot rows for every parent and child in the family."""
    for p in family.parents:
        _conn_insert_parent_hist(conn, change_id, "snapshot", now, p)
    for c in family.children:
        _conn_insert_child_hist(conn, change_id, "snapshot", now, c)


def _after_flush(session, flush_context):
    """Inspect what changed during this flush and write history rows."""
    conn = session.connection()
    now = datetime.now()

    # Collect the family ids that need a full snapshot
    affected_families = {}  # family_id -> FamilyDB object (if available)

    # --- new objects ---
    for obj in list(session.new):
        if not isinstance(obj, _TRACKED_CLASSES):
            continue
        change_id = _make_change_id()

        if isinstance(obj, FamilyDB):
            _conn_insert_family_hist(conn, change_id, "insert", now, obj)
            _snapshot_family_members(conn, change_id, now, obj)
        elif isinstance(obj, ParentDB):
            _conn_insert_parent_hist(conn, change_id, "insert", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)
        elif isinstance(obj, ChildDB):
            _conn_insert_child_hist(conn, change_id, "insert", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)

    # --- dirty (updated) objects ---
    for obj in list(session.dirty):
        if not isinstance(obj, _TRACKED_CLASSES):
            continue
        if not session.is_modified(obj):
            continue
        change_id = _make_change_id()

        if isinstance(obj, FamilyDB):
            _conn_insert_family_hist(conn, change_id, "update", now, obj)
            _snapshot_family_members(conn, change_id, now, obj)
        elif isinstance(obj, ParentDB):
            _conn_insert_parent_hist(conn, change_id, "update", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)
        elif isinstance(obj, ChildDB):
            _conn_insert_child_hist(conn, change_id, "update", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)

    # --- deleted objects ---
    for obj in list(session.deleted):
        if not isinstance(obj, _TRACKED_CLASSES):
            continue
        change_id = _make_change_id()

        if isinstance(obj, FamilyDB):
            _conn_insert_family_hist(conn, change_id, "delete", now, obj)
        elif isinstance(obj, ParentDB):
            _conn_insert_parent_hist(conn, change_id, "delete", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)
        elif isinstance(obj, ChildDB):
            _conn_insert_child_hist(conn, change_id, "delete", now, obj)
            if obj.family_id not in affected_families and obj.family is not None:
                affected_families[obj.family_id] = (obj.family, change_id)

    # --- full family snapshots for parent/child-level changes ---
    for family_id, (family, change_id) in affected_families.items():
        _conn_insert_family_hist(conn, change_id, "snapshot", now, family)
        _snapshot_family_members(conn, change_id, now, family)


event.listen(Session, "after_flush", _after_flush)


# ---------------------------------------------------------------------------
# Engine / session helpers
# ---------------------------------------------------------------------------

DB_PATH = "daycare.db"


def get_engine(db_path=None):
    path = db_path or DB_PATH
    engine = create_engine(f"sqlite:///{path}", echo=False)
    # Enable SQLite foreign key enforcement
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return engine


def create_tables(engine):
    Base.metadata.create_all(engine)


def get_session(engine) -> Session:
    return sessionmaker(bind=engine)()


def init_db(db_path=None):
    """Create engine, ensure tables exist, return (engine, session)."""
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session(engine)
    return engine, session
