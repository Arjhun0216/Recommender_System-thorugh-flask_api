# app/portal.py
import os
import pandas as pd
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from flask_login import (login_user, logout_user,
                         login_required, current_user)
from werkzeug.utils import secure_filename
from app import db, bcrypt
from app.models import Developer, Item

portal = Blueprint("portal", __name__)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "ods"}
UPLOAD_FOLDER      = "uploads"


def allowed_file(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)


def read_file(filepath, ext):
    """Read CSV, Excel, or ODS into a pandas DataFrame."""
    if ext == "csv":
        return pd.read_csv(filepath)
    elif ext == "xlsx":
        return pd.read_excel(filepath, engine="openpyxl")
    elif ext == "ods":
        return pd.read_excel(filepath, engine="odf")
    return None


# ─────────────────────────────────────────
# LANDING PAGE
# GET /
# ─────────────────────────────────────────
@portal.route("/")
def landing():
    return render_template("landing.html")


# ─────────────────────────────────────────
# REGISTER
# GET/POST /register
# ─────────────────────────────────────────
@portal.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("portal.dashboard"))

    if request.method == "POST":
        name     = request.form.get("name",     "").strip()
        email    = request.form.get("email",    "").strip()
        app_name = request.form.get("app_name", "").strip()
        password = request.form.get("password", "").strip()

        # Validate
        if not all([name, email, app_name, password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        if Developer.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("register.html")

        # Create developer
        developer = Developer(
            name          = name,
            email         = email,
            app_name      = app_name,
            password_hash = bcrypt.generate_password_hash(
                                password).decode("utf-8")
        )
        db.session.add(developer)
        db.session.commit()

        # Store API key in session to show once on dashboard
        session["new_api_key"] = developer.api_key

        login_user(developer)
        flash("Account created successfully!", "success")
        return redirect(url_for("portal.dashboard"))

    return render_template("register.html")


# ─────────────────────────────────────────
# LOGIN
# GET/POST /login
# ─────────────────────────────────────────
@portal.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("portal.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "").strip()

        developer = Developer.query.filter_by(email=email).first()

        if not developer or not bcrypt.check_password_hash(
                developer.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        login_user(developer)
        return redirect(url_for("portal.dashboard"))

    return render_template("login.html")


# ─────────────────────────────────────────
# LOGOUT
# GET /logout
# ─────────────────────────────────────────
@portal.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("portal.login"))


# ─────────────────────────────────────────
# DASHBOARD
# GET /dashboard
# ─────────────────────────────────────────
@portal.route("/dashboard")
@login_required
def dashboard():
    # Pop new_api_key from session — shown only once
    new_key = session.pop("new_api_key", None)
    return render_template("dashboard.html",
                           developer=current_user,
                           new_key=new_key)


# ─────────────────────────────────────────
# UPLOAD PRODUCTS
# GET/POST /upload
# ─────────────────────────────────────────
@portal.route("/upload", methods=["GET", "POST"])
@login_required
def upload():

    if request.method == "GET":
        return render_template("upload.html",
                               columns=None,
                               filename=None)

    # ── STEP 1 — File uploaded, read columns ──
    if "file" in request.files:
        file = request.files["file"]

        if not file or not allowed_file(file.filename):
            flash("Please upload a CSV, XLSX, or ODS file.", "error")
            return render_template("upload.html",
                                   columns=None,
                                   filename=None)

        filename = secure_filename(file.filename)
        ext      = filename.rsplit(".", 1)[1].lower()

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Read just the headers
        df      = read_file(filepath, ext)
        columns = list(df.columns)

        # Pass columns to template for mapping dropdowns
        return render_template("upload.html",
                               columns=columns,
                               filename=filename)

    # ── STEP 2 — Column mapping submitted, import data ──
    if request.form.get("filename"):
        filename    = secure_filename(request.form["filename"])
        ext         = filename.rsplit(".", 1)[1].lower()
        filepath    = os.path.join(UPLOAD_FOLDER, filename)
        id_col      = request.form.get("id_col")
        cat_col     = request.form.get("cat_col")
        region_col  = request.form.get("region_col", "")

        if not id_col or not cat_col:
            flash("Please select Product ID and Category columns.", "error")
            return redirect(url_for("portal.upload"))

        df = read_file(filepath, ext)

        # ── Batch processing — insert 500 rows at a time ──
        api_key  = current_user.api_key
        inserted = 0
        skipped  = 0
        batch    = []

        # Hash Set — track IDs seen in this upload O(1)
        seen_in_file = set()

        for _, row in df.iterrows():
            item_id  = str(row[id_col]).strip()
            category = str(row[cat_col]).strip()
            region   = str(row[region_col]).strip() if region_col else None

            # Skip empty or duplicate rows in this file
            if not item_id or item_id in seen_in_file:
                skipped += 1
                continue

            seen_in_file.add(item_id)

            # Skip if item already exists in database
            exists = Item.query.filter_by(
                api_key=api_key, item_id=item_id
            ).first()
            if exists:
                skipped += 1
                continue

            batch.append(Item(
                api_key=api_key,
                item_id=item_id,
                category=category,
                region=region
            ))
            inserted += 1

            # ── Flush batch every 500 rows ──
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []

        # Insert remaining rows
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()

        # Clean up uploaded file
        os.remove(filepath)

        flash(
            f"{inserted} products imported, {skipped} skipped.",
            "success"
        )
        return redirect(url_for("portal.dashboard"))

    flash("Something went wrong. Please try again.", "error")
    return redirect(url_for("portal.upload"))


# ─────────────────────────────────────────
# DOCS PAGE
# GET /docs
# ─────────────────────────────────────────
@portal.route("/docs")
@login_required
def docs():
    return render_template("docs.html",
                           developer=current_user,
                           api_key=current_user.api_key)