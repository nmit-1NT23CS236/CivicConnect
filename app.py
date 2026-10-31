
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from functools import wraps
from datetime import datetime
import os
import re
import uuid

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError("Set SECRET_KEY to a random value of at least 32 bytes.")

ADMIN_EMAIL = "admin@civicconnect.com"
ADMIN_INITIAL_PASSWORD = os.environ.get("ADMIN_INITIAL_PASSWORD")
if ADMIN_INITIAL_PASSWORD and len(ADMIN_INITIAL_PASSWORD) < 12:
    raise RuntimeError("ADMIN_INITIAL_PASSWORD must contain at least 12 characters.")

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE + 64 * 1024

db = SQLAlchemy(app)


# ==========================================
# DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(300), nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="complaints")

    status_history = db.relationship(
        "ComplaintStatusHistory",
        back_populates="complaint",
        order_by="ComplaintStatusHistory.created_at",
        cascade="all, delete-orphan"
    )


class ComplaintStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    complaint_id = db.Column(
        db.Integer,
        db.ForeignKey("complaint.id"),
        nullable=False
    )

    status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text)
    updated_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    complaint = db.relationship(
        "Complaint",
        back_populates="status_history"
    )


# ==========================================
# AUTHENTICATION DECORATORS
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("user_dashboard"))

        return f(*args, **kwargs)

    return decorated


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("user_dashboard"))

    return redirect(url_for("login"))


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirmPassword", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role="user"
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        admin_password_configured = (
            user
            and user.role == "admin"
            and user.email == ADMIN_EMAIL
            and ADMIN_INITIAL_PASSWORD
        )
        valid_password = user and check_password_hash(user.password, password)

        if admin_password_configured:
            valid_password = (
                valid_password
                and check_password_hash(user.password, ADMIN_INITIAL_PASSWORD)
            )

        if valid_password:

            session.clear()
            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("user_dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("login"))


# ==========================================
# CITIZEN DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def user_dashboard():

    complaints = Complaint.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Complaint.created_at.desc()).all()

    total = len(complaints)

    pending = sum(
        c.status == "Pending" for c in complaints
    )

    resolved = sum(
        c.status == "Resolved" for c in complaints
    )

    return render_template(
        "user_dashboard.html",
        complaints=complaints,
        total=total,
        pending=pending,
        resolved=resolved
    )


@app.route("/track", methods=["GET", "POST"])
def track_complaint():
    reference_id = ""
    complaint = None
    error_message = None

    if request.method == "POST":
        reference_id = request.form.get("complaint_id", "").strip().upper()

        if not reference_id:
            error_message = "Enter a complaint reference ID to track its progress."
        elif not re.fullmatch(r"CC-[A-Z0-9]{8}", reference_id):
            error_message = "Enter a valid reference ID, such as CC-1234ABCD."
        else:
            try:
                complaint = Complaint.query.filter_by(
                    complaint_id=reference_id
                ).options(
                    selectinload(Complaint.status_history)
                ).first()
                if complaint is None:
                    error_message = "We couldn't find a complaint with that reference ID."
            except SQLAlchemyError:
                db.session.rollback()
                app.logger.exception("Unable to retrieve a complaint for public tracking.")
                error_message = (
                    "Complaint tracking is temporarily unavailable. "
                    "Please try again later."
                )

    return render_template(
        "track_complaint.html",
        reference_id=reference_id,
        complaint=complaint,
        error_message=error_message,
        hide_account_identity=True
    )


# ==========================================
# SUBMIT COMPLAINT
# ==========================================

def validate_complaint_image(upload):
    safe_original_name = secure_filename(upload.filename)
    extension = os.path.splitext(safe_original_name)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    if not safe_original_name or extension not in allowed_extensions:
        return None, "Please upload a JPG, JPEG, PNG, or WEBP image."

    upload.stream.seek(0, os.SEEK_END)
    upload_size = upload.stream.tell()
    upload.stream.seek(0)

    if upload_size > MAX_UPLOAD_SIZE:
        return None, "Photo uploads must be 5 MB or smaller."

    signature = upload.stream.read(12)
    upload.stream.seek(0)

    is_valid_image = (
        (extension in {".jpg", ".jpeg"} and signature.startswith(b"\xff\xd8\xff"))
        or (
            extension == ".png"
            and signature.startswith(b"\x89PNG\r\n\x1a\n")
        )
        or (
            extension == ".webp"
            and signature.startswith(b"RIFF")
            and signature[8:12] == b"WEBP"
        )
    )

    if not is_valid_image:
        return None, "The image contents do not match the selected file type."

    return f"{uuid.uuid4().hex}_{safe_original_name}", None


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit_complaint():

    if request.method == "POST":

        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()

        allowed_categories = [
            "Road", "Water", "Electricity", "Garbage", "Other"
        ]

        if category not in allowed_categories or not description:
            flash("Please enter valid complaint details.", "error")
            return redirect(url_for("submit_complaint"))

        if len(location) > 300:
            flash("Location must be 300 characters or fewer.", "error")
            return redirect(url_for("submit_complaint"))

        upload = request.files.get("photo")
        image_filename = None

        if upload and upload.filename:
            image_filename, validation_error = validate_complaint_image(upload)
            if validation_error:
                flash(validation_error, "error")
                return redirect(url_for("submit_complaint"))

        complaint = Complaint(
            complaint_id="CC-" + uuid.uuid4().hex[:8].upper(),
            user_id=session["user_id"],
            category=category,
            description=description,
            location=location or None,
            status="Pending"
        )

        image_path = None
        try:
            db.session.add(complaint)
            db.session.flush()

            # Record the initial complaint status
            history = ComplaintStatusHistory(
                complaint_id=complaint.id,
                status="Pending",
                note="Complaint submitted successfully.",
                updated_by=session.get("name", "Citizen")
            )
            db.session.add(history)

            if image_filename:
                upload_directory = os.path.join(app.static_folder, "uploads")
                image_path = os.path.join(upload_directory, image_filename)
                os.makedirs(upload_directory, exist_ok=True)
                upload.save(image_path)
                complaint.image_filename = image_filename

            db.session.commit()
        except OSError:
            db.session.rollback()
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    app.logger.exception("Unable to remove an unsaved complaint photo.")
            app.logger.exception("Unable to save complaint photo.")
            flash("The photo could not be saved. Please try again.", "error")
            return redirect(url_for("submit_complaint"))
        except SQLAlchemyError:
            db.session.rollback()
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    app.logger.exception("Unable to remove an uncommitted complaint photo.")
            app.logger.exception("Unable to save complaint submission.")
            flash("Your complaint could not be saved. Please try again.", "error")
            return redirect(url_for("submit_complaint"))

        flash(
            f"Complaint submitted! Your ID is {complaint.complaint_id}",
            "success"
        )

        return redirect(url_for("user_dashboard"))

    return render_template("submit_complaint.html")


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error):
    if request.endpoint == "submit_complaint":
        flash("Photo uploads must be 5 MB or smaller.", "error")
        return redirect(url_for("submit_complaint"))

    return error


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    complaints = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).all()

    total = Complaint.query.count()

    pending = Complaint.query.filter_by(
        status="Pending"
    ).count()

    in_progress = Complaint.query.filter_by(
        status="In Progress"
    ).count()

    resolved = Complaint.query.filter_by(
        status="Resolved"
    ).count()

    total_users = User.query.filter_by(
        role="user"
    ).count()

    category_stats = (
        db.session.query(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .order_by(Complaint.category)
        .all()
    )

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        total_users=total_users,
        category_labels=[category for category, _ in category_stats],
        category_counts=[count for _, count in category_stats]
    )


# ==========================================
# UPDATE COMPLAINT STATUS
# ==========================================

@app.route("/update_status/<int:complaint_id>", methods=["POST"])
@admin_required
def update_status(complaint_id):

    complaint = db.session.get(Complaint, complaint_id)

    if not complaint:
        flash("Complaint not found.", "error")
        return redirect(url_for("admin_dashboard"))

    new_status = request.form.get("status", "").strip()
    note = request.form.get("note", "").strip()

    allowed_statuses = [
        "Pending", "In Progress", "Resolved"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid status.", "error")
        return redirect(url_for("admin_dashboard"))

    if len(note) > 500:
        flash("Remarks must be 500 characters or fewer.", "error")
        return redirect(url_for("admin_dashboard"))

    if new_status == complaint.status and not note:
        flash("No changes were made.", "info")
        return redirect(url_for("admin_dashboard"))

    complaint.status = new_status

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=new_status,
        note=note or f"Status updated to {new_status}.",
        updated_by=session.get("name", "Administrator")
    )

    db.session.add(history)
    db.session.commit()

    flash("Complaint status and history updated successfully.", "success")

    return redirect(url_for("admin_dashboard"))


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def initialize_database():

    with app.app_context():

        db.create_all()

        complaint_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("complaint")
        }

        with db.engine.begin() as connection:
            if "location" not in complaint_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE complaint ADD COLUMN location VARCHAR(300)"
                )
            if "image_filename" not in complaint_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE complaint ADD COLUMN image_filename VARCHAR(255)"
                )

        # Add history for older complaints created before
        # the status-history feature was introduced.
        existing_complaints = Complaint.query.all()

        for complaint in existing_complaints:

            if not complaint.status_history:

                history = ComplaintStatusHistory(
                    complaint_id=complaint.id,
                    status=complaint.status,
                    note="Existing complaint record.",
                    updated_by="System",
                    created_at=complaint.created_at
                )

                db.session.add(history)

        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if admin and not ADMIN_INITIAL_PASSWORD:
            raise RuntimeError(
                "Set ADMIN_INITIAL_PASSWORD to rotate the existing "
                "administrator password before starting the application."
            )

        if ADMIN_INITIAL_PASSWORD:
            if admin:
                admin.password = generate_password_hash(ADMIN_INITIAL_PASSWORD)
            else:
                admin = User(
                    name="Administrator",
                    email=ADMIN_EMAIL,
                    password=generate_password_hash(ADMIN_INITIAL_PASSWORD),
                    role="admin"
                )
                db.session.add(admin)

        db.session.commit()


if __name__ == "__main__":

    initialize_database()

    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
