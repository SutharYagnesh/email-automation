from app.db import get_db
from app.services.auth_service import register_user
from app.services.contact_service import create_group, create_label, create_contact
from app.services.sender_service import create_sender_account
from app.services.template_service import create_template
from app.services.campaign_service import create_campaign

def seed_database():
    db = get_db()
    
    # 1. Create Admin User if not exists
    user = db.users.find_one({"username": "admin"})
    if not user:
        _, _, user = register_user("admin", "admin@example.com", "AdminPassword123!", "Admin User")
    
    user_id = str(user["_id"])
    
    # 2. Create Groups & Labels
    grp1_ok, _, grp1 = create_group(user_id, "VIP Clients", "High priority enterprise contacts")
    grp2_ok, _, grp2 = create_group(user_id, "Newsletter Subscribers", "Opted-in weekly newsletter readers")
    
    lbl1_ok, _, lbl1 = create_label(user_id, "Hot Lead", "#ef4444")
    lbl2_ok, _, lbl2 = create_label(user_id, "Customer", "#10b981")
    
    group_ids = [grp1.get("_id"), grp2.get("_id")]
    group_ids = [g for g in group_ids if g]
    
    # 3. Create Sample Contacts
    sample_contacts = [
        {"email": "alex.smith@acme.com", "name": "Alex Smith", "company_name": "Acme Corp", "custom_fields": {"role": "CEO", "city": "New York"}},
        {"email": "sarah.connor@cyber.io", "name": "Sarah Connor", "company_name": "Cyberdyne Systems", "custom_fields": {"role": "CTO", "city": "San Francisco"}},
        {"email": "michael.jordan@bulls.org", "name": "Michael Jordan", "company_name": "Bulls Enterprise", "custom_fields": {"role": "Managing Director", "city": "Chicago"}},
        {"email": "emily.watson@tech.co", "name": "Emily Watson", "company_name": "TechCo Labs", "custom_fields": {"role": "VP Product", "city": "Austin"}}
    ]
    
    for sc in sample_contacts:
        create_contact(
            user_id=user_id,
            email=sc["email"],
            name=sc["name"],
            company_name=sc["company_name"],
            custom_fields=sc["custom_fields"],
            group_ids=group_ids
        )
        
    # 4. Create Sample Sender Account
    sender_ok, _, sender = create_sender_account(
        user_id=user_id,
        username="demo.sender@gmail.com",
        app_password="abcd efgh ijkl mnop",
        sender_name="Demo Marketing Team",
        reply_to="demo.sender@gmail.com"
    )
    
    # 5. Create Sample Email Template
    template_ok, _, template = create_template(
        user_id=user_id,
        name="Product Welcome & Onboarding",
        subject="Welcome {{name}} to {{company_name}}!",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #2563eb;">Welcome aboard, {{name}}!</h2>
            <p>We are excited to have <strong>{{company_name}}</strong> partner with us.</p>
            <p>As the {{custom.role}} in {{custom.city}}, we have tailored exclusive resources for your team.</p>
            <div style="margin: 24px 0;">
                <a href="https://example.com/onboarding" style="background-color: #2563eb; color: #ffffff; padding: 12px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Get Started Now</a>
            </div>
            <p style="color: #64748b; font-size: 14px;">Best regards,<br/>The Marketing Team</p>
        </div>
        """,
        body_text="Welcome {{name}}! We are excited to have {{company_name}} partner with us."
    )
    
    # 6. Create Sample Campaign Draft
    if sender.get("_id") and template.get("_id"):
        create_campaign(
            user_id=user_id,
            name="Q3 Welcome Campaign",
            sender_id=sender["_id"],
            template_id=template["_id"],
            recipient_type="groups",
            group_ids=group_ids,
            delay_seconds=2.0
        )
        
    print("Database seeded with sample contacts, groups, sender account, template, and campaign!")

if __name__ == "__main__":
    seed_database()
