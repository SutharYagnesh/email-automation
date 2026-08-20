from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.services.auth_service import register_user, login_user, logout_user, get_current_user

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required."}), 401
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        identifier = request.form.get("username", "")
        password = request.form.get("password", "")
        
        try:
            success, message, user = login_user(identifier, password)
            if success:
                flash("Welcome back!", "success")
                next_url = request.args.get("next") or url_for("dashboard.index")
                return redirect(next_url)
            else:
                flash(message, "danger")
        except Exception as e:
            flash(f"Login error: {str(e)}", "danger")
            
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "")
        
        try:
            success, message, user = register_user(username, email, password, full_name)
            if success:
                login_user(username, password)
                flash("Account created successfully!", "success")
                return redirect(url_for("dashboard.index"))
            else:
                flash(message, "danger")
        except Exception as e:
            flash(f"Registration error: {str(e)}", "danger")
            
    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
