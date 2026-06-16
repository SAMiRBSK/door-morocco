"""
Door Morocco — Main Application
=================================
Ultra-luxury tourism platform showcasing Morocco's finest cities.
"""

import os
import json
import uuid
import functools
import threading
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

try:
    from flask_mail import Mail, Message
    HAS_MAIL = True
except ImportError:
    HAS_MAIL = False

from flask import (
    Flask, render_template, g, jsonify,
    request, redirect, url_for, session, flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import config_by_name


# ── Factory ───────────────────────────────────────────────
def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Flask-Mail setup ─────────────────────────────────────
    mail = None
    if HAS_MAIL and app.config.get("MAIL_USERNAME"):
        mail = Mail(app)

    def send_admin_email(subject, body_html):
        """Send an email notification to the admin (non-blocking)."""
        if mail is None:
            return
        try:
            msg = Message(
                subject=subject,
                recipients=[app.config["ADMIN_EMAIL"]],
                html=body_html,
            )
            # Send in a background thread to avoid blocking
            def _send():
                with app.app_context():
                    try:
                        mail.send(msg)
                    except Exception as e:
                        app.logger.error(f"Mail send failed: {e}")
            threading.Thread(target=_send, daemon=True).start()
        except Exception as e:
            app.logger.error(f"Mail setup failed: {e}")

    # ── Utility helpers ──────────────────────────────────────
    def allowed_file(filename: str) -> bool:
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower()
            in app.config["ALLOWED_EXTENSIONS"]
        )

    # ── Database helpers ─────────────────────────────────────
    def get_db():
        """Open a new DB connection per request and cache it on `g`."""
        if not HAS_MYSQL:
            return None
        if "db" not in g:
            try:
                g.db = mysql.connector.connect(
                    host=app.config["MYSQL_HOST"],
                    port=app.config["MYSQL_PORT"],
                    user=app.config["MYSQL_USER"],
                    password=app.config["MYSQL_PASSWORD"],
                    database=app.config["MYSQL_DB"],
                    charset="utf8mb4",
                )
            except Exception:
                return None
        return g.db

    def get_cursor():
        """Return a dictionary cursor from the current connection."""
        db = get_db()
        if db is None:
            return None
        return db.cursor(dictionary=True)

    def create_notification(ntype, title, message="", ref_id=None):
        """Insert a notification into the DB."""
        cur = get_cursor()
        if cur is None:
            return
        try:
            cur.execute(
                """INSERT INTO notifications (type, title, message, ref_id)
                   VALUES (%s, %s, %s, %s)""",
                (ntype, title, message, ref_id),
            )
            get_db().commit()
        except Exception:
            pass

    @app.teardown_appcontext
    def close_db(exception):          # noqa: ARG001
        """Close the DB connection at the end of the request."""
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # ── Auth helpers ─────────────────────────────────────────
    def login_required(view):
        @functools.wraps(view)
        def wrapped(**kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return view(**kwargs)
        return wrapped

    def admin_required(view):
        @functools.wraps(view)
        def wrapped(**kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("user_role") != "admin":
                flash("Access denied.", "error")
                return redirect(url_for("index"))
            return view(**kwargs)
        return wrapped

    # ── Error handler for file-too-large ─────────────────────
    @app.errorhandler(413)
    def file_too_large(e):             # noqa: ARG001
        flash("File is too large. Maximum allowed size is 5 MB.", "error")
        return redirect(url_for("dashboard"))

    # ═════════════════════════════════════════════════════════
    #  PUBLIC ROUTES
    # ═════════════════════════════════════════════════════════
    @app.route("/")
    def index():
        cities = None
        cur = get_cursor()
        if cur is not None:
            try:
                cur.execute("SELECT id, name, description, image FROM cities ORDER BY id ASC")
                cities = cur.fetchall()
                cur.close()
            except Exception:
                cities = None
        if not cities:
            cities = [
                {"id": 1, "name": "Marrakech",   "description": "The Red City — a sensory journey through ancient medinas, palatial riads, and the majestic Atlas Mountains.", "image": "/static/images/marrakech.jpg"},
                {"id": 2, "name": "Chefchaouen", "description": "The Blue Pearl — an ethereal mountain village draped in every shade of cerulean and cobalt.",                   "image": "/static/images/chefchaouen.jpg"},
                {"id": 3, "name": "Fes",          "description": "The Spiritual Capital — a labyrinth of living history, world-class artisanship, and the oldest university on Earth.", "image": "/static/images/fes.jpg"},
                {"id": 4, "name": "Essaouira",    "description": "The Wind City — where Atlantic breezes meet Portuguese ramparts and a thriving art scene.",                       "image": "/static/images/essaouira.jpg"},
                {"id": 5, "name": "Merzouga",     "description": "Gateway to the Sahara — towering golden dunes, starlit desert camps, and timeless Berber hospitality.",          "image": "/static/images/merzouga.jpg"},
                {"id": 6, "name": "Tangier",      "description": "The Gateway to Africa — a cosmopolitan port city where Europe and Morocco share a single horizon.",             "image": "/static/images/tangier.jpg"},
            ]
        return render_template("index.html", cities=cities)

    # ── City View ────────────────────────────────────────────
    @app.route("/city/<int:city_id>")
    def city_view(city_id):
        """Public page showing all verified services for a specific city."""
        city = None
        services = []
        all_cities = []

        cur = get_cursor()
        if cur is not None:
            try:
                cur.execute("SELECT id, name, description, image FROM cities WHERE id = %s", (city_id,))
                city = cur.fetchone()

                if city:
                    cur.execute("""
                        SELECT s.id, s.title, s.category, s.description,
                               s.main_image, u.name AS partner_name
                        FROM services s
                        JOIN user u ON s.partner_id = u.id
                        WHERE s.city_id = %s AND s.verified_status = TRUE
                        ORDER BY s.category ASC, s.title ASC
                    """, (city_id,))
                    services = cur.fetchall()

                    # Fetch lowest price for each service
                    for svc in services:
                        cur.execute("""
                            SELECT MIN(price_mad) AS min_price
                            FROM affiliate_links WHERE service_id = %s
                        """, (svc["id"],))
                        row = cur.fetchone()
                        svc["min_price"] = row["min_price"] if row and row["min_price"] else None

                # Sidebar cities list
                cur.execute("SELECT id, name FROM cities ORDER BY name ASC")
                all_cities = cur.fetchall()
                cur.close()
            except Exception:
                pass

        # Demo fallback
        demo_cities_data = {
            1: {"id": 1, "name": "Marrakech",   "description": "The Red City — a sensory journey through ancient medinas, palatial riads, and the majestic Atlas Mountains.", "image": "/static/images/marrakech.jpg"},
            2: {"id": 2, "name": "Chefchaouen", "description": "The Blue Pearl — an ethereal mountain village draped in every shade of cerulean and cobalt.",                   "image": "/static/images/chefchaouen.jpg"},
            3: {"id": 3, "name": "Fes",          "description": "The Spiritual Capital — a labyrinth of living history, world-class artisanship, and the oldest university on Earth.", "image": "/static/images/fes.jpg"},
            4: {"id": 4, "name": "Essaouira",    "description": "The Wind City — where Atlantic breezes meet Portuguese ramparts and a thriving art scene.",                       "image": "/static/images/essaouira.jpg"},
            5: {"id": 5, "name": "Merzouga",     "description": "Gateway to the Sahara — towering golden dunes, starlit desert camps, and timeless Berber hospitality.",          "image": "/static/images/merzouga.jpg"},
            6: {"id": 6, "name": "Tangier",      "description": "The Gateway to Africa — a cosmopolitan port city where Europe and Morocco share a single horizon.",             "image": "/static/images/tangier.jpg"},
        }

        if not city:
            city = demo_cities_data.get(city_id)
        if not city:
            flash("City not found.", "error")
            return redirect(url_for("index"))

        if not all_cities:
            all_cities = [{"id": k, "name": v["name"]} for k, v in demo_cities_data.items()]

        hotels = [s for s in services if s["category"] == "hotel"]
        guides = [s for s in services if s["category"] == "guide"]

        return render_template(
            "city_view.html", city=city, services=services,
            hotels=hotels, guides=guides, all_cities=all_cities,
        )

    # ── Service Detail ───────────────────────────────────────
    @app.route("/service/<int:service_id>")
    def service_detail(service_id):
        """Public page showing full service details + affiliate comparison."""
        service = None
        links = []
        partner = None

        cur = get_cursor()
        if cur is not None:
            try:
                cur.execute("""
                    SELECT s.id, s.title, s.category, s.description,
                           s.main_image, s.verified_status, s.created_at,
                           c.id AS city_id, c.name AS city_name, c.image AS city_image,
                           u.id AS partner_id, u.name AS partner_name, u.email AS partner_email
                    FROM services s
                    JOIN cities c ON s.city_id = c.id
                    JOIN user u ON s.partner_id = u.id
                    WHERE s.id = %s AND s.verified_status = TRUE
                """, (service_id,))
                service = cur.fetchone()

                if service:
                    cur.execute("""
                        SELECT id, site_name, price_mad, url
                        FROM affiliate_links
                        WHERE service_id = %s
                        ORDER BY price_mad ASC
                    """, (service_id,))
                    links = cur.fetchall()

                cur.close()
            except Exception:
                pass

        if not service:
            flash("Service not found or not yet approved.", "warning")
            return redirect(url_for("index"))

        # Find cheapest link
        cheapest = links[0] if links else None

        return render_template(
            "service_detail.html", service=service, links=links,
            cheapest=cheapest,
        )

    # ── Registration ─────────────────────────────────────────
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name     = request.form.get("name", "").strip()
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm  = request.form.get("confirm_password", "")

            errors = []
            if not name or len(name) < 2:
                errors.append("Full name is required.")
            if not email or "@" not in email:
                errors.append("A valid email address is required.")
            if len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != confirm:
                errors.append("Passwords do not match.")

            if errors:
                for err in errors:
                    flash(err, "error")
                return render_template("register.html", name=name, email=email)

            cur = get_cursor()
            if cur is None:
                flash("Registration is temporarily unavailable.", "error")
                return render_template("register.html", name=name, email=email)

            try:
                cur.execute("SELECT id FROM user WHERE email = %s", (email,))
                if cur.fetchone():
                    flash("An account with this email already exists.", "error")
                    return render_template("register.html", name=name, email=email)
            except Exception:
                flash("Something went wrong. Please try again.", "error")
                return render_template("register.html", name=name, email=email)
            

            hashed = generate_password_hash(password)
            try:
        
                cur.execute("""
                            
    INSERT INTO user (name, email, password, role, status)
    VALUES (%s, %s, %s, 'partner', 'pending')""",
    (name, email, hashed),
)
                get_db().commit()
                new_id = cur.lastrowid
                cur.close()

                # ── Create notification for admin ────────────
                create_notification(
                    "new_partner",
                    f"New partner registration: {name}",
                    f"{name} ({email}) has registered and is awaiting approval.",
                    new_id,
                )

                # ── Send email to admin ──────────────────────
                send_admin_email(
                    subject=f"🚪 New Partner Registration — {name}",
                    body_html=f"""
                    <div style="font-family:Arial,sans-serif;background:#000;color:#F5F5F0;padding:40px;max-width:500px">
                      <h2 style="color:#D4AF37;margin-bottom:16px">New Partner Registration</h2>
                      <p><strong>Name:</strong> {name}</p>
                      <p><strong>Email:</strong> {email}</p>
                      <p style="margin-top:20px;color:#A9A9A0">
                        This partner is awaiting your approval. Log in to the Admin Panel to review.
                      </p>
                      <hr style="border-color:#D4AF37;opacity:0.3;margin:20px 0">
                      <p style="font-size:12px;color:#A9A9A0">Door Morocco — Luxury Tourism Platform</p>
                    </div>
                    """,
                )

                flash("Your account has been created and is pending review.", "success")
                return redirect(url_for("login"))
            except Exception:
                flash("Registration failed. Please try again.", "error")
                return render_template("register.html", name=name, email=email)

        return render_template("register.html")

    # ── Login ────────────────────────────────────────────────
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                flash("Email and password are required.", "error")
                return render_template("login.html", email=email)

            cur = get_cursor()
            if cur is None:
                flash("Login is temporarily unavailable.", "error")
                return render_template("login.html", email=email)

            try:
                cur.execute(
                    "SELECT id, name, email, password_hash, role, status FROM user WHERE email = %s",
                    (email,),
                )
                user = cur.fetchone()
                cur.close()
            except Exception:
                flash("Something went wrong. Please try again.", "error")
                return render_template("login.html", email=email)

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return render_template("login.html", email=email)

            if user["role"] == "partner" and user["status"] == "pending":
                return render_template("pending.html", user_name=user["name"])

            session.clear()
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been signed out.", "info")
        return redirect(url_for("index"))

    # ═════════════════════════════════════════════════════════
    #  PARTNER DASHBOARD
    # ═════════════════════════════════════════════════════════
    @app.route("/dashboard")
    @login_required
    def dashboard():
        partner_id = session["user_id"]
        services = []
        cities = []

        cur = get_cursor()
        if cur is not None:
            try:
                cur.execute("""
                    SELECT s.id, s.title, s.category, s.description,
                           s.main_image, s.verified_status,
                           c.name AS city_name, s.created_at
                    FROM services s
                    JOIN cities c ON s.city_id = c.id
                    WHERE s.partner_id = %s
                    ORDER BY s.created_at DESC
                """, (partner_id,))
                services = cur.fetchall()

                for svc in services:
                    cur.execute("""
                        SELECT id, site_name, price_mad, url
                        FROM affiliate_links
                        WHERE service_id = %s ORDER BY id ASC
                    """, (svc["id"],))
                    svc["links"] = cur.fetchall()

                cur.execute("SELECT id, name FROM cities ORDER BY name ASC")
                cities = cur.fetchall()
                cur.close()
            except Exception:
                services = []
                cities = []

        if not cities:
            cities = [
                {"id": 1, "name": "Marrakech"}, {"id": 2, "name": "Chefchaouen"},
                {"id": 3, "name": "Fes"}, {"id": 4, "name": "Essaouira"},
                {"id": 5, "name": "Merzouga"}, {"id": 6, "name": "Tangier"},
            ]

        return render_template(
            "dashboard.html", services=services, cities=cities,
            services_count=len(services),
            live_count=sum(1 for s in services if s.get("verified_status")),
        )

    @app.route("/dashboard/add-service", methods=["POST"])
    @login_required
    def add_service():
        partner_id = session["user_id"]
        title       = request.form.get("title", "").strip()
        category    = request.form.get("category", "")
        city_id     = request.form.get("city_id", "")
        description = request.form.get("description", "").strip()

        errors = []
        if not title or len(title) < 3:
            errors.append("Service title is required (min 3 characters).")
        if category not in ("hotel", "guide"):
            errors.append("Please select a valid category.")
        if not city_id:
            errors.append("Please select a city.")
        if not description or len(description) < 10:
            errors.append("Description must be at least 10 characters.")

        image_file = request.files.get("main_image")
        saved_path = None
        if image_file and image_file.filename:
            if not allowed_file(image_file.filename):
                errors.append("Only PNG, JPG, JPEG, and WEBP images are allowed.")
            else:
                image_file.seek(0, 2)
                if image_file.tell() > app.config["MAX_CONTENT_LENGTH"]:
                    errors.append("Image must be smaller than 5 MB.")
                image_file.seek(0)

        if errors:
            for err in errors:
                flash(err, "error")
            return redirect(url_for("dashboard"))

        if image_file and image_file.filename:
            ext = image_file.filename.rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
            saved_path = f"/static/uploads/{unique_name}"

        link_names  = request.form.getlist("link_site_name[]")
        link_prices = request.form.getlist("link_price[]")
        link_urls   = request.form.getlist("link_url[]")

        cur = get_cursor()
        if cur is None:
            flash("Database is temporarily unavailable.", "error")
            return redirect(url_for("dashboard"))

        try:
            cur.execute("""
                INSERT INTO services (city_id, partner_id, title, category, description, main_image, verified_status)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            """, (city_id, partner_id, title, category, description, saved_path))
            service_id = cur.lastrowid

            for i in range(len(link_names)):
                sn = link_names[i].strip() if i < len(link_names) else ""
                sp = link_prices[i].strip() if i < len(link_prices) else ""
                su = link_urls[i].strip() if i < len(link_urls) else ""
                if sn and sp and su:
                    try:
                        pv = float(sp)
                    except ValueError:
                        continue
                    cur.execute("""
                        INSERT INTO affiliate_links (service_id, site_name, price_mad, url)
                        VALUES (%s, %s, %s, %s)
                    """, (service_id, sn, pv, su))

            get_db().commit()
            cur.close()

            # Notification for admin
            create_notification(
                "new_service",
                f"New service submitted: {title}",
                f"Partner '{session.get('user_name')}' submitted '{title}' ({category}).",
                service_id,
            )

            flash("Service created successfully! It will be reviewed by our team.", "success")
        except Exception:
            flash("Failed to create service. Please try again.", "error")

        return redirect(url_for("dashboard"))

    @app.route("/dashboard/delete-service/<int:service_id>", methods=["POST"])
    @login_required
    def delete_service(service_id):
        partner_id = session["user_id"]
        cur = get_cursor()
        if cur is None:
            flash("Database unavailable.", "error")
            return redirect(url_for("dashboard"))
        try:
            cur.execute("DELETE FROM services WHERE id = %s AND partner_id = %s",
                        (service_id, partner_id))
            get_db().commit()
            cur.close()
            flash("Service has been removed.", "info")
        except Exception:
            flash("Could not delete service.", "error")
        return redirect(url_for("dashboard"))

    # ═════════════════════════════════════════════════════════
    #  ADMIN PANEL
    # ═════════════════════════════════════════════════════════
    @app.route("/admin_panel")
    @admin_required
    def admin_panel():
        """Admin panel — pending partners, pending services, notifications."""
        pending_partners = []
        pending_services = []
        notifications = []
        stats = {"partners": 0, "services": 0, "unread": 0}

        cur = get_cursor()
        if cur is not None:
            try:
                # Pending partners
                cur.execute("""
                    SELECT id, name, email, created_at
                    FROM user
                    WHERE role = 'partner' AND status = 'pending'
                    ORDER BY created_at DESC
                """)
                pending_partners = cur.fetchall()
                stats["partners"] = len(pending_partners)

                # Pending services
                cur.execute("""
                    SELECT s.id, s.title, s.category, s.main_image, s.created_at,
                           u.name AS partner_name, u.email AS partner_email,
                           c.name AS city_name
                    FROM services s
                    JOIN user u ON s.partner_id = u.id
                    JOIN cities c ON s.city_id = c.id
                    WHERE s.verified_status = FALSE
                    ORDER BY s.created_at DESC
                """)
                pending_services = cur.fetchall()
                stats["services"] = len(pending_services)

                # Recent notifications
                cur.execute("""
                    SELECT id, type, title, message, is_read, created_at
                    FROM notifications
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
                notifications = cur.fetchall()

                # Unread count
                cur.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE is_read = FALSE")
                row = cur.fetchone()
                stats["unread"] = row["cnt"] if row else 0

                cur.close()
            except Exception:
                pass

        return render_template(
            "admin_panel.html",
            pending_partners=pending_partners,
            pending_services=pending_services,
            notifications=notifications,
            stats=stats,
        )

    # ── Approve / Reject Partner ─────────────────────────────
    @app.route("/admin/partner/<int:user_id>/approve", methods=["POST"])
    @admin_required
    def approve_partner(user_id):
        cur = get_cursor()
        if cur is None:
            flash("Database unavailable.", "error")
            return redirect(url_for("admin_panel"))
        try:
            cur.execute("UPDATE user SET status = 'approved' WHERE id = %s AND role = 'partner'", (user_id,))
            cur.execute("SELECT name, email FROM user WHERE id = %s", (user_id,))
            u = cur.fetchone()
            get_db().commit()
            cur.close()
            if u:
                create_notification("partner_approved", f"Partner approved: {u['name']}",
                                    f"{u['name']} ({u['email']}) has been approved.", user_id)
            flash("Partner has been approved.", "success")
        except Exception:
            flash("Failed to approve partner.", "error")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/partner/<int:user_id>/reject", methods=["POST"])
    @admin_required
    def reject_partner(user_id):
        cur = get_cursor()
        if cur is None:
            flash("Database unavailable.", "error")
            return redirect(url_for("admin_panel"))
        try:
            cur.execute("DELETE FROM user WHERE id = %s AND role = 'partner' AND status = 'pending'", (user_id,))
            get_db().commit()
            cur.close()
            create_notification("partner_rejected", "Partner application rejected",
                                f"A pending partner application (ID: {user_id}) was rejected.", user_id)
            flash("Partner has been rejected and removed.", "info")
        except Exception:
            flash("Failed to reject partner.", "error")
        return redirect(url_for("admin_panel"))

    # ── Approve / Reject Service ─────────────────────────────
    @app.route("/admin/service/<int:service_id>/approve", methods=["POST"])
    @admin_required
    def approve_service(service_id):
        cur = get_cursor()
        if cur is None:
            flash("Database unavailable.", "error")
            return redirect(url_for("admin_panel"))
        try:
            cur.execute("UPDATE services SET verified_status = TRUE WHERE id = %s", (service_id,))
            cur.execute("SELECT title FROM services WHERE id = %s", (service_id,))
            s = cur.fetchone()
            get_db().commit()
            cur.close()
            if s:
                create_notification("service_approved", f"Service approved: {s['title']}",
                                    f"'{s['title']}' is now live on the platform.", service_id)
            flash("Service is now live.", "success")
        except Exception:
            flash("Failed to approve service.", "error")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/service/<int:service_id>/reject", methods=["POST"])
    @admin_required
    def reject_service(service_id):
        cur = get_cursor()
        if cur is None:
            flash("Database unavailable.", "error")
            return redirect(url_for("admin_panel"))
        try:
            cur.execute("SELECT title FROM services WHERE id = %s", (service_id,))
            s = cur.fetchone()
            cur.execute("DELETE FROM services WHERE id = %s", (service_id,))
            get_db().commit()
            cur.close()
            title = s["title"] if s else "Unknown"
            create_notification("service_rejected", f"Service rejected: {title}",
                                f"'{title}' has been rejected and removed.", service_id)
            flash("Service has been rejected and removed.", "info")
        except Exception:
            flash("Failed to reject service.", "error")
        return redirect(url_for("admin_panel"))

    # ── Mark notifications read ──────────────────────────────
    @app.route("/admin/notifications/mark-read", methods=["POST"])
    @admin_required
    def mark_notifications_read():
        cur = get_cursor()
        if cur is not None:
            try:
                cur.execute("UPDATE notifications SET is_read = TRUE WHERE is_read = FALSE")
                get_db().commit()
                cur.close()
            except Exception:
                pass
        return redirect(url_for("admin_panel"))

    # ── API ──────────────────────────────────────────────────
    @app.route("/api/cities")
    def api_cities():
        try:
            cur = get_cursor()
            if cur is None:
                return jsonify({"error": "Database unavailable"}), 503
            cur.execute("SELECT id, name, description, image FROM cities ORDER BY id ASC")
            cities = cur.fetchall()
            cur.close()
            return jsonify(cities)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/notifications/unread-count")
    @admin_required
    def api_unread_count():
        cur = get_cursor()
        if cur is None:
            return jsonify({"count": 0})
        try:
            cur.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE is_read = FALSE")
            row = cur.fetchone()
            cur.close()
            return jsonify({"count": row["cnt"] if row else 0})
        except Exception:
            return jsonify({"count": 0})

    return app


   # ── Entry Point ─────────────────────────────────────────────
app = create_app()

if __name__ == "main":
       port = int(os.environ.get("PORT", 5000))
       app.run(host="0.0.0.0", port=port, debug=True)
