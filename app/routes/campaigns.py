from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.routes.auth import login_required
from app.services.sender_service import get_sender_accounts
from app.services.contact_service import get_groups, get_contacts
from app.services.template_service import get_templates
from app.services.campaign_service import (
    create_campaign, launch_campaign, get_campaigns, get_campaign_detail, resolve_campaign_recipients,
    delete_campaign, add_sends_to_campaign
)
from app.db import get_db
from bson import ObjectId

campaigns_bp = Blueprint("campaigns", __name__)

@campaigns_bp.route("/campaigns")
@login_required
def index():
    user_id = session.get("user_id")
    campaign_list = get_campaigns(user_id)
    return render_template("campaigns/index.html", campaigns=campaign_list)

@campaigns_bp.route("/campaigns/create", methods=["GET", "POST"])
@login_required
def create():
    user_id = session.get("user_id")
    
    if request.method == "POST":
        name = request.form.get("name", "")
        sender_id = request.form.get("sender_id", "")
        template_id = request.form.get("template_id", "")
        recipient_type = request.form.get("recipient_type", "groups")
        group_ids = request.form.getlist("group_ids")
        contact_ids = request.form.getlist("contact_ids")
        delay_seconds = request.form.get("delay_seconds", "2.0")
        
        success, message, campaign = create_campaign(
            user_id=user_id,
            name=name,
            sender_id=sender_id,
            template_id=template_id,
            recipient_type=recipient_type,
            group_ids=group_ids,
            contact_ids=contact_ids,
            delay_seconds=float(delay_seconds)
        )
        
        if success:
            flash(message, "success")
            # Auto-launch if requested
            if request.form.get("auto_launch") == "1":
                launch_campaign(campaign["_id"], user_id)
                flash("Campaign launched successfully!", "success")
            return redirect(url_for("campaigns.detail", campaign_id=campaign["_id"]))
        else:
            flash(message, "danger")
            
    senders = get_sender_accounts(user_id)
    groups = get_groups(user_id)
    contacts = get_contacts(user_id)
    templates_list = get_templates(user_id)
    
    return render_template(
        "campaigns/create.html",
        senders=senders,
        groups=groups,
        contacts=contacts,
        templates=templates_list
    )

@campaigns_bp.route("/campaigns/<campaign_id>")
@login_required
def detail(campaign_id):
    user_id = session.get("user_id")
    campaign = get_campaign_detail(campaign_id, user_id)
    if not campaign:
        flash("Campaign not found.", "danger")
        return redirect(url_for("campaigns.index"))
        
    db = get_db()
    # Resolve sender name & template name
    sender = db.sender_accounts.find_one({"_id": ObjectId(campaign["sender_id"])}) if campaign.get("sender_id") else None
    template = db.templates.find_one({"_id": ObjectId(campaign["template_id"])}) if campaign.get("template_id") else None
    
    campaign["sender_username"] = sender.get("username", "N/A") if sender else "N/A"
    campaign["template_name"] = template.get("name", "N/A") if template else "N/A"
    
    groups = get_groups(user_id)
    contacts = get_contacts(user_id)
    templates = get_templates(user_id)
    
    return render_template("campaigns/detail.html", campaign=campaign, groups=groups, contacts=contacts, templates=templates)

@campaigns_bp.route("/campaigns/<campaign_id>/delete", methods=["POST"])
@login_required
def delete(campaign_id):
    user_id = session.get("user_id")
    success, message = delete_campaign(campaign_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("campaigns.index"))

@campaigns_bp.route("/campaigns/<campaign_id>/add-sends", methods=["POST"])
@login_required
def add_sends(campaign_id):
    user_id = session.get("user_id")
    template_id = request.form.get("template_id")
    recipient_type = request.form.get("recipient_type", "groups")
    group_ids = request.form.getlist("group_ids")
    contact_ids = request.form.getlist("contact_ids")
    delay_seconds = request.form.get("delay_seconds", "2.0")
    
    success, message = add_sends_to_campaign(
        campaign_id=campaign_id,
        user_id=user_id,
        template_id=template_id,
        recipient_type=recipient_type,
        group_ids=group_ids,
        contact_ids=contact_ids,
        delay_seconds=float(delay_seconds) if delay_seconds else 2.0
    )
    
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

@campaigns_bp.route("/campaigns/<campaign_id>/launch", methods=["POST"])
@login_required
def launch(campaign_id):
    user_id = session.get("user_id")
    success, message = launch_campaign(campaign_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

@campaigns_bp.route("/campaigns/<campaign_id>/status")
@login_required
def status_api(campaign_id):
    user_id = session.get("user_id")
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid campaign ID"}), 400
        
    campaign = db.campaigns.find_one({"_id": cid, "user_id": user_id})
    if not campaign:
        return jsonify({"success": False, "message": "Campaign not found"}), 404
        
    total = campaign.get("total_recipients", 0)
    sent = campaign.get("sent_count", 0)
    progress_pct = round((sent / total * 100), 1) if total > 0 else 0
    
    return jsonify({
        "success": True,
        "status": campaign.get("status", "draft"),
        "total_recipients": total,
        "sent_count": sent,
        "delivered_count": campaign.get("delivered_count", 0),
        "opened_count": campaign.get("opened_count", 0),
        "replied_count": campaign.get("replied_count", 0),
        "failed_count": campaign.get("failed_count", 0),
        "progress_percent": progress_pct
    })

@campaigns_bp.route("/campaigns/preview-recipients", methods=["POST"])
@login_required
def preview_recipients():
    user_id = session.get("user_id")
    payload = request.json or {}
    recipient_type = payload.get("recipient_type", "groups")
    group_ids = payload.get("group_ids", [])
    contact_ids = payload.get("contact_ids", [])
    
    recipients = resolve_campaign_recipients(user_id, recipient_type, group_ids, contact_ids)
    return jsonify({
        "success": True,
        "count": len(recipients),
        "recipients": [{"email": r["email"], "name": r.get("name", "")} for r in recipients[:10]]
    })
