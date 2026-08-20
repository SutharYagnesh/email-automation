import os
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from config import Config

def send_single_email(
    smtp_username: str,
    smtp_password: str,
    sender_name: str,
    reply_to: str,
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    attachments: list = None,
    tracking_id: str = None,
    host: str = "smtp.gmail.com",
    port: int = 465
) -> tuple[bool, str, str]:
    """
    Construct RFC compliant MIME message with tracking pixel, headers, and attachments,
    then dispatch via smtplib.SMTP_SSL.
    
    Returns: (success: bool, error_message: str, message_id: str)
    """
    try:
        domain = smtp_username.split("@")[-1] if "@" in smtp_username else "gmail.com"
        
        # 1. Create root MIME container
        msg = MIMEMultipart("mixed") if attachments else MIMEMultipart("alternative")
        
        # 2. Add standard required deliverability headers
        msg["From"] = f"{sender_name} <{smtp_username}>" if sender_name else smtp_username
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        
        # Generate unique Message-ID
        message_id = make_msgid(domain=domain)
        msg["Message-ID"] = message_id
        
        # Set Reply-To
        if reply_to:
            msg["Reply-To"] = reply_to
        else:
            msg["Reply-To"] = smtp_username
            
        # Unsubscribe links & headers (RFC 8058 standard)
        unsubscribe_url = f"{Config.APP_BASE_URL}/unsubscribe/{tracking_id}" if tracking_id else f"{Config.APP_BASE_URL}/unsubscribe/generic"
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>, <mailto:{smtp_username}?subject=unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        
        # 3. Process HTML & Text bodies with Tracking Pixel and Unsubscribe link
        full_html = body_html or ""
        
        # Inject Unsubscribe footer link if not present
        if "unsubscribe" not in full_html.lower():
            footer = f"""
            <br/><hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;"/>
            <p style="font-size:12px;color:#6b7280;font-family:sans-serif;text-align:center;">
                If you no longer wish to receive these emails, you can 
                <a href="{unsubscribe_url}" style="color:#2563eb;text-decoration:underline;">unsubscribe here</a>.
            </p>
            """
            full_html += footer
            
        # Inject 1x1 transparent open tracking pixel (only if tracking_id is provided)
        if tracking_id and "localhost" not in Config.APP_BASE_URL and "127.0.0.1" not in Config.APP_BASE_URL:
            tracking_pixel_url = f"{Config.APP_BASE_URL}/track/open/{tracking_id}"
            pixel_tag = f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;width:1px;height:1px;max-height:0px;max-width:0px;opacity:0;" alt="" />'
            if "</body>" in full_html.lower():
                full_html = re_sub_insensitive("</body>", f"{pixel_tag}</body>", full_html)
            else:
                full_html += pixel_tag
                
        # 4. Attach Body Parts (Text + HTML inside alternative part)
        body_container = MIMEMultipart("alternative") if attachments else msg
        
        # Generate rich plain-text fallback if body_text is missing
        plain_content = body_text if body_text else html_to_plain_text(full_html)
        body_container.attach(MIMEText(plain_content, "plain", "utf-8"))
        body_container.attach(MIMEText(full_html, "html", "utf-8"))
        
        if attachments:
            msg.attach(body_container)
            # Add file attachments
            for att in attachments:
                file_path = att.get("path") if isinstance(att, dict) else att
                if file_path and os.path.exists(file_path):
                    filename = att.get("original_name") if isinstance(att, dict) else os.path.basename(file_path)
                    with open(file_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    msg.attach(part)
                    
        # 5. Send via SMTP / SMTP_SSL
        port_num = int(port) if port else 465
        if port_num == 465:
            with smtplib.SMTP_SSL(host, port_num, timeout=15) as server:
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, [recipient_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port_num, timeout=15) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, [recipient_email], msg.as_string())
            
        return True, "Email sent successfully.", message_id

    except Exception as e:
        return False, str(e), ""

def re_sub_insensitive(pattern: str, repl: str, string: str) -> str:
    """Helper for case-insensitive string replacement."""
    import re
    return re.sub(re.escape(pattern), repl, string, flags=re.IGNORECASE)

def html_to_plain_text(html_content: str) -> str:
    """Convert HTML content into clean, readable plain text for MIME alternative part."""
    if not html_content:
        return ""
    import re
    # Remove script & style blocks
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content, flags=re.IGNORECASE)
    text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
    
    # Replace block level elements with newlines
    text = re.sub(r'</p>|<br\s*/?>|</div>|</li>|</h1>|</h2>|</h3>|</h4>|</h5>|6>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<hr[^>]*>', '\n----------------------------------------\n', text, flags=re.IGNORECASE)
    
    # Convert links <a href="url">text</a> to text (url)
    text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', text, flags=re.IGNORECASE)
    
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Unescape HTML entities
    import html
    text = html.unescape(text)
    
    # Collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = []
    prev_blank = False
    for line in lines:
        if line:
            clean_lines.append(line)
            prev_blank = False
        elif not prev_blank:
            clean_lines.append("")
            prev_blank = True
            
    return "\n".join(clean_lines).strip()
