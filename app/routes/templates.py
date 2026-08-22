from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.routes.auth import login_required
from app.services.template_service import (
    create_template, update_template, delete_template,
    get_templates, get_template_by_id, render_template_variables, save_uploaded_attachment
)

templates_bp = Blueprint("templates", __name__)

@templates_bp.route("/templates")
@login_required
def index():
    user_id = session.get("user_id")
    templates_list = get_templates(user_id)
    return render_template("templates_email/index.html", templates=templates_list)

@templates_bp.route("/templates/add", methods=["POST"])
@login_required
def add():
    user_id = session.get("user_id")
    try:
        name = request.form.get("name", "")
        subject = request.form.get("subject", "")
        body_html = request.form.get("body_html", "")
        body_text = request.form.get("body_text", "")
        
        # Process attachments uploaded in form
        attachments = []
        if request.files and "attachment_files" in request.files:
            try:
                files = request.files.getlist("attachment_files")
                for f in files:
                    if f and hasattr(f, 'filename') and f.filename != "":
                        att_info = save_uploaded_attachment(f)
                        if att_info:
                            attachments.append(att_info)
            except Exception as fe:
                print(f"[Template Attachment Warning]: {fe}")
                        
        success, message, template = create_template(user_id, name, subject, body_html, body_text, attachments)
        if success:
            flash("Template created successfully.", "success")
        else:
            flash(message, "danger")
    except Exception as e:
        flash(f"Error creating template: {str(e)}", "danger")
        
    return redirect(url_for("templates.index"))

@templates_bp.route("/templates/<template_id>/edit", methods=["POST"])
@login_required
def edit(template_id):
    user_id = session.get("user_id")
    try:
        data = {
            "name": request.form.get("name", ""),
            "subject": request.form.get("subject", ""),
            "body_html": request.form.get("body_html", ""),
            "body_text": request.form.get("body_text", "")
        }
        
        # Retain or add new attachments
        existing = get_template_by_id(template_id, user_id)
        attachments = existing.get("attachments", []) if existing else []
        
        if request.files and "attachment_files" in request.files:
            try:
                files = request.files.getlist("attachment_files")
                for f in files:
                    if f and hasattr(f, 'filename') and f.filename != "":
                        att_info = save_uploaded_attachment(f)
                        if att_info:
                            attachments.append(att_info)
            except Exception as fe:
                print(f"[Template Attachment Warning]: {fe}")
                
        data["attachments"] = attachments
        
        success, message = update_template(template_id, user_id, data)
        if success:
            flash("Template updated successfully.", "success")
        else:
            flash(message, "danger")
    except Exception as e:
        flash(f"Error updating template: {str(e)}", "danger")
        
    return redirect(url_for("templates.index"))

@templates_bp.route("/templates/<template_id>/delete", methods=["POST"])
@login_required
def delete(template_id):
    user_id = session.get("user_id")
    success, message = delete_template(template_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("templates.index"))

@templates_bp.route("/templates/preview", methods=["POST"])
@login_required
def preview():
    payload = request.json or request.form
    subject = payload.get("subject", "")
    body_html = payload.get("body_html", "")
    
    sample_contact = {
        "name": payload.get("sample_name", "Jane Doe"),
        "email": payload.get("sample_email", "jane.doe@example.com"),
        "company_name": payload.get("sample_company", "Acme Corporation"),
        "custom_fields": {
            "role": payload.get("sample_role", "Marketing Director"),
            "city": payload.get("sample_city", "New York")
        }
    }
    
    rendered_subject = render_template_variables(subject, sample_contact)
    rendered_html = render_template_variables(body_html, sample_contact)
    
    return jsonify({
        "success": True,
        "rendered_subject": rendered_subject,
        "rendered_html": rendered_html
    })

@templates_bp.route("/templates/spam-check", methods=["POST"])
@login_required
def spam_check():
    from app.services.deliverability_service import analyze_email_spam_risk
    payload = request.json or request.form
    subject = payload.get("subject", "")
    body_html = payload.get("body_html", "")
    sender_domain = payload.get("domain", "")
    
    result = analyze_email_spam_risk(subject, body_html, sender_domain)
    return jsonify({"success": True, "result": result})
