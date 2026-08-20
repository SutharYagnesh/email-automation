from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.routes.auth import login_required
from app.services.contact_service import (
    create_group, get_groups, delete_group,
    create_label, get_labels, delete_label
)

groups_bp = Blueprint("groups", __name__)

@groups_bp.route("/groups")
@login_required
def index():
    user_id = session.get("user_id")
    groups = get_groups(user_id)
    labels = get_labels(user_id)
    return render_template("groups/index.html", groups=groups, labels=labels)

@groups_bp.route("/groups/add", methods=["POST"])
@login_required
def add_group():
    user_id = session.get("user_id")
    name = request.form.get("name", "")
    description = request.form.get("description", "")
    
    success, message, group = create_group(user_id, name, description)
    if success:
        flash("Group created successfully.", "success")
    else:
        flash(message, "danger")
    return redirect(url_for("groups.index"))

@groups_bp.route("/groups/<group_id>/delete", methods=["POST"])
@login_required
def remove_group(group_id):
    user_id = session.get("user_id")
    success, message = delete_group(group_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("groups.index"))

@groups_bp.route("/labels/add", methods=["POST"])
@login_required
def add_label():
    user_id = session.get("user_id")
    name = request.form.get("name", "")
    color = request.form.get("color", "#3b82f6")
    
    success, message, label = create_label(user_id, name, color)
    if success:
        flash("Label created successfully.", "success")
    else:
        flash(message, "danger")
    return redirect(url_for("groups.index"))

@groups_bp.route("/labels/<label_id>/delete", methods=["POST"])
@login_required
def remove_label(label_id):
    user_id = session.get("user_id")
    success, message = delete_label(label_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("groups.index"))
