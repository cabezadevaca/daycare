"""
Flask web application for the daycare billing admin dashboard.
Served over HTTPS with a self-signed certificate.
"""

import os
import ssl
import calendar
from functools import wraps
from datetime import datetime, date

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, jsonify
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload

from database import (
    init_db, DayCareDB, FamilyDB, ParentDB, ChildDB,
    PublicHolidayDB, InvoiceDB, InvoiceLineItemDB,
    FamilyHistoryDB, ParentHistoryDB, ChildHistoryDB,
    UserDB,
)
from invoice import Invoice, save_family_pdf
from timetable import PublicHolidays

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-to-a-random-secret-key")

# ---------------------------------------------------------------------------
# Database session management
# ---------------------------------------------------------------------------

_engine, _session = init_db()


def get_session():
    return _session


# ---------------------------------------------------------------------------
# Flask-Login setup
# ---------------------------------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


class AuthUser(UserMixin):
    """Wrapper so Flask-Login can work with the SQLAlchemy UserDB model."""

    def __init__(self, user_db):
        self.id = user_db.id
        self.username = user_db.username
        self.role = user_db.role
        self.family_id = user_db.family_id

    @property
    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    session = get_session()
    user_db = session.query(UserDB).get(int(user_id))
    if user_db is None:
        return None
    return AuthUser(user_db)


def admin_required(f):
    """Decorator: logged-in user must have the admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def family_access_required(f):
    """Decorator for routes that take a family_id parameter.

    Admins pass through.  Parent users may only access their own family.
    """
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            fid = kwargs.get("family_id")
            if fid is not None and fid != current_user.family_id:
                flash("You do not have access to that family.", "danger")
                return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        session = get_session()
        user_db = session.query(UserDB).filter_by(username=username).first()
        if user_db and check_password_hash(user_db.password_hash, password):
            login_user(AuthUser(user_db))
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_public_holidays(session):
    rows = session.query(PublicHolidayDB).all()
    date_strings = [row.date.strftime("%Y-%m-%d") for row in rows]
    return PublicHolidays(date_strings)


def get_or_create_daycare(session):
    """Return the daycare record, creating a default one if none exists."""
    daycare = DayCareDB.load_from_db(session)
    if daycare is None:
        daycare = DayCareDB(name="My Daycare")
        session.add(daycare)
        session.commit()
    return daycare


WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# PWA: serve service worker from root scope
# ---------------------------------------------------------------------------

@app.route("/sw.js")
def service_worker():
    return app.send_static_file("sw.js"), 200, {"Content-Type": "application/javascript"}


@app.context_processor
def inject_globals():
    return dict(weekday_names=WEEKDAY_NAMES, now=datetime.now)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    session = get_session()
    daycare = get_or_create_daycare(session)
    if current_user.is_admin:
        families = session.query(FamilyDB).all()
        children = session.query(ChildDB).all()
        parents = session.query(ParentDB).all()
        invoices = session.query(InvoiceDB).order_by(InvoiceDB.generated_at.desc()).limit(10).all()
    else:
        families = session.query(FamilyDB).filter_by(id=current_user.family_id).all()
        children = session.query(ChildDB).filter_by(family_id=current_user.family_id).all()
        parents = session.query(ParentDB).filter_by(family_id=current_user.family_id).all()
        invoices = session.query(InvoiceDB).filter_by(family_id=current_user.family_id).order_by(InvoiceDB.generated_at.desc()).limit(10).all()
    holidays = session.query(PublicHolidayDB).order_by(PublicHolidayDB.date).all()
    return render_template(
        "dashboard.html",
        daycare=daycare,
        families=families,
        children=children,
        parents=parents,
        invoices=invoices,
        holidays=holidays,
    )


# ---------------------------------------------------------------------------
# Daycare Settings
# ---------------------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    session = get_session()
    daycare = get_or_create_daycare(session)
    if request.method == "POST":
        daycare.name = request.form.get("name", daycare.name)
        daycare.address = request.form.get("address", daycare.address)
        daycare.town_state_zip = request.form.get("town_state_zip", daycare.town_state_zip)
        daycare.phone = request.form.get("phone", daycare.phone)
        daycare.ein = request.form.get("ein", daycare.ein)
        daycare.logo = request.form.get("logo", daycare.logo)
        daycare.email = request.form.get("email", daycare.email)
        daycare.invoice_prefix = request.form.get("invoice_prefix", daycare.invoice_prefix)
        daycare.sender_through = request.form.get("sender_through", daycare.sender_through)
        daycare.sender_email = request.form.get("sender_email", daycare.sender_email)
        # Only update password if provided
        pwd = request.form.get("sender_password", "")
        if pwd:
            daycare.sender_password = pwd
        session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", daycare=daycare)


# ---------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------

@app.route("/families")
@login_required
def families_list():
    session = get_session()
    daycare = get_or_create_daycare(session)
    if current_user.is_admin:
        families = session.query(FamilyDB).options(
            joinedload(FamilyDB.parents),
            joinedload(FamilyDB.children),
        ).all()
    else:
        families = session.query(FamilyDB).filter_by(id=current_user.family_id).options(
            joinedload(FamilyDB.parents),
            joinedload(FamilyDB.children),
        ).all()
    return render_template("families.html", families=families, daycare=daycare)


@app.route("/families/add", methods=["POST"])
@admin_required
def family_add():
    session = get_session()
    daycare = get_or_create_daycare(session)
    fam = FamilyDB(daycare_id=daycare.id)
    session.add(fam)
    session.commit()
    flash("New family created.", "success")
    return redirect(url_for("family_detail", family_id=fam.id))


@app.route("/families/<int:family_id>")
@family_access_required
def family_detail(family_id):
    session = get_session()
    family = session.query(FamilyDB).get(family_id)
    if not family:
        flash("Family not found.", "danger")
        return redirect(url_for("families_list"))
    invoices = session.query(InvoiceDB).filter_by(family_id=family_id).order_by(
        InvoiceDB.year.desc(), InvoiceDB.month.desc()
    ).all()
    return render_template("family_detail.html", family=family, invoices=invoices)


@app.route("/families/<int:family_id>/delete", methods=["POST"])
@admin_required
def family_delete(family_id):
    session = get_session()
    family = session.query(FamilyDB).get(family_id)
    if family:
        session.delete(family)
        session.commit()
        flash("Family deleted.", "success")
    return redirect(url_for("families_list"))


# ---------------------------------------------------------------------------
# Parents
# ---------------------------------------------------------------------------

@app.route("/families/<int:family_id>/parents/add", methods=["POST"])
@admin_required
def parent_add(family_id):
    session = get_session()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if not name:
        flash("Parent name is required.", "danger")
        return redirect(url_for("family_detail", family_id=family_id))
    parent = ParentDB(family_id=family_id, name=name, email=email)
    session.add(parent)
    session.commit()
    flash(f"Parent '{name}' added.", "success")
    return redirect(url_for("family_detail", family_id=family_id))


@app.route("/parents/<int:parent_id>/edit", methods=["POST"])
@admin_required
def parent_edit(parent_id):
    session = get_session()
    parent = session.query(ParentDB).get(parent_id)
    if not parent:
        flash("Parent not found.", "danger")
        return redirect(url_for("families_list"))
    parent.name = request.form.get("name", parent.name)
    parent.email = request.form.get("email", parent.email)
    session.commit()
    flash("Parent updated.", "success")
    return redirect(url_for("family_detail", family_id=parent.family_id))


@app.route("/parents/<int:parent_id>/delete", methods=["POST"])
@admin_required
def parent_delete(parent_id):
    session = get_session()
    parent = session.query(ParentDB).get(parent_id)
    if not parent:
        flash("Parent not found.", "danger")
        return redirect(url_for("families_list"))
    family_id = parent.family_id
    session.delete(parent)
    session.commit()
    flash("Parent deleted.", "success")
    return redirect(url_for("family_detail", family_id=family_id))


# ---------------------------------------------------------------------------
# Children
# ---------------------------------------------------------------------------

@app.route("/families/<int:family_id>/children/add", methods=["POST"])
@admin_required
def child_add(family_id):
    session = get_session()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Child name is required.", "danger")
        return redirect(url_for("family_detail", family_id=family_id))

    dob_str = request.form.get("dob", "")
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None

    day_rate = float(request.form.get("day_rate", 0))

    schedule_days = request.form.getlist("schedule")
    schedule = [int(d) for d in schedule_days]

    child = ChildDB(
        family_id=family_id, name=name, dob=dob,
        day_rate=day_rate, schedule=schedule,
    )
    session.add(child)
    session.commit()
    flash(f"Child '{name}' added.", "success")
    return redirect(url_for("family_detail", family_id=family_id))


@app.route("/children/<int:child_id>/edit", methods=["POST"])
@admin_required
def child_edit(child_id):
    session = get_session()
    child = session.query(ChildDB).get(child_id)
    if not child:
        flash("Child not found.", "danger")
        return redirect(url_for("families_list"))

    child.name = request.form.get("name", child.name)
    dob_str = request.form.get("dob", "")
    child.dob = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else child.dob
    child.day_rate = float(request.form.get("day_rate", child.day_rate))

    schedule_days = request.form.getlist("schedule")
    child.schedule = [int(d) for d in schedule_days]

    session.commit()
    flash("Child updated.", "success")
    return redirect(url_for("family_detail", family_id=child.family_id))


@app.route("/children/<int:child_id>/delete", methods=["POST"])
@admin_required
def child_delete(child_id):
    session = get_session()
    child = session.query(ChildDB).get(child_id)
    if not child:
        flash("Child not found.", "danger")
        return redirect(url_for("families_list"))
    family_id = child.family_id
    session.delete(child)
    session.commit()
    flash("Child deleted.", "success")
    return redirect(url_for("family_detail", family_id=family_id))


# ---------------------------------------------------------------------------
# Public Holidays
# ---------------------------------------------------------------------------

@app.route("/holidays")
@admin_required
def holidays_list():
    session = get_session()
    holidays = session.query(PublicHolidayDB).order_by(PublicHolidayDB.date).all()
    return render_template("holidays.html", holidays=holidays)


@app.route("/holidays/add", methods=["POST"])
@admin_required
def holiday_add():
    session = get_session()
    date_str = request.form.get("date", "")
    label = request.form.get("label", "").strip()
    if not date_str:
        flash("Date is required.", "danger")
        return redirect(url_for("holidays_list"))
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    existing = session.query(PublicHolidayDB).filter_by(date=d).first()
    if existing:
        flash("That date is already a public holiday.", "warning")
        return redirect(url_for("holidays_list"))
    holiday = PublicHolidayDB(date=d, label=label or None)
    session.add(holiday)
    session.commit()
    flash("Holiday added.", "success")
    return redirect(url_for("holidays_list"))


@app.route("/holidays/<int:holiday_id>/delete", methods=["POST"])
@admin_required
def holiday_delete(holiday_id):
    session = get_session()
    holiday = session.query(PublicHolidayDB).get(holiday_id)
    if holiday:
        session.delete(holiday)
        session.commit()
        flash("Holiday deleted.", "success")
    return redirect(url_for("holidays_list"))


# ---------------------------------------------------------------------------
# Family History
# ---------------------------------------------------------------------------

@app.route("/history")
@admin_required
def history():
    session = get_session()
    today = date.today()

    # Default date range: first and last day of current month
    default_start = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    default_end = date(today.year, today.month, last_day)

    start_str = request.args.get("start", default_start.isoformat())
    end_str = request.args.get("end", default_end.isoformat())
    family_id = request.args.get("family_id", "")

    start_date = datetime.strptime(start_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59
    )

    # Query each history table for the date range
    fam_q = session.query(FamilyHistoryDB).filter(
        FamilyHistoryDB.changed_at.between(start_date, end_date)
    )
    par_q = session.query(ParentHistoryDB).filter(
        ParentHistoryDB.changed_at.between(start_date, end_date)
    )
    chi_q = session.query(ChildHistoryDB).filter(
        ChildHistoryDB.changed_at.between(start_date, end_date)
    )

    if family_id:
        fid = int(family_id)
        fam_q = fam_q.filter(FamilyHistoryDB.family_id == fid)
        par_q = par_q.filter(ParentHistoryDB.family_id == fid)
        chi_q = chi_q.filter(ChildHistoryDB.family_id == fid)

    # Merge into a single timeline, sorted newest-first
    events = []
    for h in fam_q.all():
        events.append({
            "time": h.changed_at, "type": "Family", "operation": h.operation,
            "change_id": h.change_id, "family_id": h.family_id,
            "detail": f"Family #{h.family_id}",
        })
    for h in par_q.all():
        events.append({
            "time": h.changed_at, "type": "Parent", "operation": h.operation,
            "change_id": h.change_id, "family_id": h.family_id,
            "detail": f"{h.name} (email: {h.email or '—'})",
        })
    for h in chi_q.all():
        sched = ""
        if h.schedule:
            import json as _json
            raw = h.schedule
            days = _json.loads(raw) if isinstance(raw, str) else raw
            sched = ", ".join(WEEKDAY_NAMES[d] for d in days)
        events.append({
            "time": h.changed_at, "type": "Child", "operation": h.operation,
            "change_id": h.change_id, "family_id": h.family_id,
            "detail": f"{h.name} | DOB: {h.dob or '—'} | Rate: ${h.day_rate or 0:.2f} | Schedule: {sched or '—'}",
        })

    events.sort(key=lambda e: e["time"], reverse=True)

    # --- Attendance & Rate snapshot view ---
    show = request.args.get("show", "")
    attendance_data = []
    if show == "attendance":
        import json as _json
        # Derive year/month from the start date for invoice lookup
        s_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_str, "%Y-%m-%d").date()

        # Get invoices that fall within the selected date range
        inv_q = session.query(InvoiceDB).filter(
            InvoiceDB.generated_at.between(start_date, end_date)
        )
        if family_id:
            inv_q = inv_q.filter(InvoiceDB.family_id == int(family_id))
        invoices_in_range = inv_q.options(
            joinedload(InvoiceDB.line_items).joinedload(InvoiceLineItemDB.child),
            joinedload(InvoiceDB.family).joinedload(FamilyDB.parents),
        ).order_by(InvoiceDB.year.desc(), InvoiceDB.month.desc()).all()

        for inv in invoices_in_range:
            fam_label = ", ".join(p.name for p in inv.family.parents) if inv.family and inv.family.parents else f"Family #{inv.family_id}"
            for item in inv.line_items:
                # Look up the closest child history snapshot for rate/schedule context
                snap = session.query(ChildHistoryDB).filter(
                    ChildHistoryDB.child_id == item.child_id,
                    ChildHistoryDB.changed_at <= end_date,
                ).order_by(ChildHistoryDB.changed_at.desc()).first()

                sched_str = "—"
                if snap and snap.schedule:
                    raw = snap.schedule
                    days = _json.loads(raw) if isinstance(raw, str) else raw
                    sched_str = ", ".join(WEEKDAY_NAMES[d] for d in days)

                dates_str = ", ".join(str(d) for d in item.attendance_dates) if item.attendance_dates else "—"
                attendance_data.append({
                    "family": fam_label,
                    "family_id": inv.family_id,
                    "period": f"{inv.month}/{inv.year}",
                    "child": item.child.name if item.child else f"Child #{item.child_id}",
                    "schedule": sched_str,
                    "rate": item.day_rate,
                    "days_count": item.days_count,
                    "attendance": dates_str,
                    "fee": item.fee,
                })

    # For the family filter dropdown
    families = session.query(FamilyDB).options(joinedload(FamilyDB.parents)).all()

    # Prev / next month boundaries for quick navigation
    s = datetime.strptime(start_str, "%Y-%m-%d").date()
    if s.month == 1:
        prev_start = date(s.year - 1, 12, 1)
    else:
        prev_start = date(s.year, s.month - 1, 1)
    prev_end = date(prev_start.year, prev_start.month,
                    calendar.monthrange(prev_start.year, prev_start.month)[1])

    if s.month == 12:
        next_start = date(s.year + 1, 1, 1)
    else:
        next_start = date(s.year, s.month + 1, 1)
    next_end = date(next_start.year, next_start.month,
                    calendar.monthrange(next_start.year, next_start.month)[1])

    return render_template(
        "history.html",
        events=events,
        families=families,
        start=start_str,
        end=end_str,
        family_id=family_id,
        show=show,
        attendance_data=attendance_data,
        prev_month_start=prev_start.isoformat(),
        prev_month_end=prev_end.isoformat(),
        next_month_start=next_start.isoformat(),
        next_month_end=next_end.isoformat(),
    )


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@app.route("/invoices")
@login_required
def invoices_list():
    session = get_session()
    q = session.query(InvoiceDB).options(
        joinedload(InvoiceDB.family).joinedload(FamilyDB.parents),
        joinedload(InvoiceDB.line_items),
    )
    if not current_user.is_admin:
        q = q.filter(InvoiceDB.family_id == current_user.family_id)
    invoices = q.order_by(InvoiceDB.year.desc(), InvoiceDB.month.desc()).all()
    return render_template("invoices.html", invoices=invoices)


@app.route("/invoices/generate", methods=["GET", "POST"])
@admin_required
def invoice_generate():
    session = get_session()
    daycare = get_or_create_daycare(session)
    families = session.query(FamilyDB).options(
        joinedload(FamilyDB.parents),
        joinedload(FamilyDB.children),
    ).all()

    if request.method == "POST":
        year = int(request.form.get("year", datetime.now().year))
        month = int(request.form.get("month", datetime.now().month))
        family_ids = request.form.getlist("family_ids")
        public_holidays = load_public_holidays(session)

        invoices_dir = os.path.join(
            os.path.dirname(__file__), "invoices", f"{month}-{year}"
        )
        os.makedirs(invoices_dir, exist_ok=True)

        generated = 0
        for fid in family_ids:
            fam = session.query(FamilyDB).get(int(fid))
            if not fam or not fam.children:
                continue
            invoice = Invoice.generate_family_invoice(year, month, fam, public_holidays)
            pdf_path = save_family_pdf(invoice, daycare, invoices_dir)
            invoice.save_to_db(session, pdf_path=pdf_path)
            generated += 1

        session.commit()
        flash(f"Generated {generated} invoice(s) for {month}/{year}.", "success")
        return redirect(url_for("invoices_list"))

    return render_template(
        "invoice_generate.html",
        families=families,
        current_year=datetime.now().year,
        current_month=datetime.now().month,
    )


@app.route("/invoices/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    session = get_session()
    invoice = session.query(InvoiceDB).options(
        joinedload(InvoiceDB.family).joinedload(FamilyDB.parents),
        joinedload(InvoiceDB.line_items).joinedload(InvoiceLineItemDB.child),
    ).get(invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("invoices_list"))
    if not current_user.is_admin and invoice.family_id != current_user.family_id:
        flash("You do not have access to that invoice.", "danger")
        return redirect(url_for("invoices_list"))
    return render_template("invoice_detail.html", invoice=invoice)


@app.route("/invoices/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    session = get_session()
    invoice = session.query(InvoiceDB).get(invoice_id)
    if not invoice or not invoice.pdf_path:
        flash("PDF not available.", "warning")
        return redirect(url_for("invoices_list"))
    if not current_user.is_admin and invoice.family_id != current_user.family_id:
        flash("You do not have access to that invoice.", "danger")
        return redirect(url_for("invoices_list"))
    if os.path.isfile(invoice.pdf_path):
        return send_file(invoice.pdf_path, as_attachment=True)
    flash("PDF file not found on disk.", "danger")
    return redirect(url_for("invoices_list"))


@app.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
@admin_required
def invoice_delete(invoice_id):
    session = get_session()
    invoice = session.query(InvoiceDB).get(invoice_id)
    if invoice:
        session.delete(invoice)
        session.commit()
        flash("Invoice deleted.", "success")
    return redirect(url_for("invoices_list"))


# ---------------------------------------------------------------------------
# User Management (admin only)
# ---------------------------------------------------------------------------

@app.route("/users")
@admin_required
def user_management():
    session = get_session()
    users = session.query(UserDB).all()
    families = session.query(FamilyDB).options(joinedload(FamilyDB.parents)).all()
    return render_template("users.html", users=users, families=families)


@app.route("/users/add", methods=["POST"])
@admin_required
def user_add():
    session = get_session()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "parent")
    family_id = request.form.get("family_id", "")

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("user_management"))

    if session.query(UserDB).filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for("user_management"))

    user = UserDB(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
        family_id=int(family_id) if family_id else None,
    )
    session.add(user)
    session.commit()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("user_management"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    session = get_session()
    user = session.query(UserDB).get(user_id)
    if user:
        if user.id == current_user.id:
            flash("You cannot delete your own account.", "warning")
        else:
            session.delete(user)
            session.commit()
            flash("User deleted.", "success")
    return redirect(url_for("user_management"))


# ---------------------------------------------------------------------------
# Run with HTTPS
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cert_dir = os.path.join(os.path.dirname(__file__), "certs")
    certfile = os.path.join(cert_dir, "cert.pem")
    keyfile = os.path.join(cert_dir, "key.pem")

    port = int(os.environ.get("PORT", 5443))

    if not os.path.isfile(certfile) or not os.path.isfile(keyfile):
        print("SSL certificates not found. Generate them with:")
        print("  cd certs && ./generate_cert.sh")
        print(f"Falling back to HTTP on port {port}...")
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        print(f"Starting HTTPS server on https://localhost:{port}")
        app.run(host="0.0.0.0", port=port, debug=True, ssl_context=context)
