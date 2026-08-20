import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from config import Config
from app.routes.auth import login_required
from app.services.contact_service import (
    create_contact, update_contact, delete_contact, get_contacts,
    get_groups, get_labels, import_contacts_from_file, bulk_add_contacts_to_group,
    create_group, delete_group
)

contacts_bp = Blueprint("contacts", __name__)

@contacts_bp.route("/contacts")
@login_required
def index():
    user_id = session.get("user_id")
    group_id = request.args.get("group_id")
    label_id = request.args.get("label_id")
    search = request.args.get("search")
    
    contacts = get_contacts(user_id, group_id=group_id, label_id=label_id, search=search)
    groups = get_groups(user_id)
    labels = get_labels(user_id)
    
    return render_template(
        "contacts/index.html",
        contacts=contacts,
        groups=groups,
        labels=labels,
        selected_group=group_id,
        selected_label=label_id,
        search_query=search or ""
    )

@contacts_bp.route("/contacts/add", methods=["POST"])
@login_required
def add():
    user_id = session.get("user_id")
    email = request.form.get("email", "")
    name = request.form.get("name", "")
    company_name = request.form.get("company_name", "")
    group_ids = request.form.getlist("group_ids")
    label_ids = request.form.getlist("label_ids")
    
    # Custom fields JSON or key-value pairs
    custom_json = request.form.get("custom_fields", "{}")
    custom_fields = {}
    try:
        if custom_json:
            custom_fields = json.loads(custom_json)
    except Exception:
        pass
        
    success, message, contact = create_contact(
        user_id=user_id,
        email=email,
        name=name,
        company_name=company_name,
        custom_fields=custom_fields,
        group_ids=group_ids,
        label_ids=label_ids
    )
    
    if success:
        flash("Contact created successfully.", "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/<contact_id>/edit", methods=["POST"])
@login_required
def edit(contact_id):
    user_id = session.get("user_id")
    data = {
        "email": request.form.get("email", ""),
        "name": request.form.get("name", ""),
        "company_name": request.form.get("company_name", ""),
        "group_ids": request.form.getlist("group_ids"),
        "label_ids": request.form.getlist("label_ids")
    }
    
    custom_json = request.form.get("custom_fields", "{}")
    try:
        data["custom_fields"] = json.loads(custom_json)
    except Exception:
        pass
        
    success, message = update_contact(contact_id, user_id, data)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/<contact_id>/delete", methods=["POST"])
@login_required
def delete(contact_id):
    user_id = session.get("user_id")
    success, message = delete_contact(contact_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/import", methods=["POST"])
@login_required
def import_file():
    user_id = session.get("user_id")
    if "file" not in request.files:
        flash("No file selected for import.", "danger")
        return redirect(url_for("contacts.index"))
        
    file = request.files["file"]
    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("contacts.index"))
        
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ["csv", "xlsx", "xls"]:
        flash("Invalid file format. Only CSV or XLSX files are allowed.", "danger")
        return redirect(url_for("contacts.index"))
        
    upload_dir = os.path.join(Config.UPLOAD_FOLDER, "contact_imports")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{user_id}_{filename}")
    file.save(file_path)
    
    group_ids = request.form.getlist("group_ids")
    label_ids = request.form.getlist("label_ids")
    
    success, message, summary = import_contacts_from_file(file_path, user_id, group_ids, label_ids)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/bulk-group-assign", methods=["POST"])
@login_required
def bulk_group_assign():
    user_id = session.get("user_id")
    contact_ids = request.form.getlist("contact_ids")
    group_id = request.form.get("group_id", "")
    
    success, message = bulk_add_contacts_to_group(contact_ids, group_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/groups/add", methods=["POST"])
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
    return redirect(url_for("contacts.index"))

@contacts_bp.route("/contacts/groups/<group_id>/delete", methods=["POST"])
@login_required
def remove_group(group_id):
    user_id = session.get("user_id")
    success, message = delete_group(group_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("contacts.index"))

