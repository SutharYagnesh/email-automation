import re
from app.services.sender_service import check_domain_deliverability

SPAM_KEYWORDS = [
    "100% free", "free money", "click here", "buy now", "make money", "cash bonus",
    "urgent action", "act now", "guaranteed", "risk free", "no obligation", "winner",
    "congratulations", "earn $", "double your income", "fast cash", "extra income",
    "unlimited leads", "best price", "special promotion", "order now"
]

def analyze_email_spam_risk(subject: str, body_html: str, sender_domain: str = None) -> dict:
    """
    Analyze subject, HTML body, and domain for spam trigger patterns.
    Returns: dict with risk_level ('Low', 'Medium', 'High'), spam_score (0-100), and warnings list.
    """
    score = 0
    warnings = []
    
    subject = subject or ""
    body_html = body_html or ""
    
    # 1. Subject line checks
    if not subject:
        score += 25
        warnings.append("Subject line is missing.")
    else:
        # Check ALL CAPS subject
        if len(subject) > 5 and subject.isupper():
            score += 20
            warnings.append("Subject line is entirely ALL CAPS. Avoid ALL CAPS as spam filters flag it.")
            
        # Check excessive exclamation marks
        if "!" in subject:
            exclamations = subject.count("!")
            if exclamations >= 2:
                score += 15
                warnings.append(f"Subject contains {exclamations} exclamation marks ('!'). Reduce punctuation.")
                
        # Check spam keywords in subject
        subj_lower = subject.lower()
        found_kw_subj = [kw for kw in SPAM_KEYWORDS if kw in subj_lower]
        if found_kw_subj:
            score += 25
            warnings.append(f"Subject contains spam trigger phrase(s): '{', '.join(found_kw_subj)}'.")

    # 2. Body HTML content checks
    body_lower = body_html.lower()
    found_kw_body = [kw for kw in SPAM_KEYWORDS if kw in body_lower]
    if found_kw_body:
        score += 15
        warnings.append(f"Email body contains spam trigger phrase(s): '{', '.join(found_kw_body)}'.")
        
    # Check text-to-html ratio
    clean_text = re.sub(r'<[^>]+>', ' ', body_html).strip()
    if len(clean_text) < 50:
        score += 15
        warnings.append("Email text content is very short. Low text-to-HTML ratio increases spam score.")
        
    # Check image count vs text
    image_count = len(re.findall(r'<img[^>]+>', body_html, re.IGNORECASE))
    if image_count > 3 and len(clean_text) < 200:
        score += 20
        warnings.append(f"Email has {image_count} images but only {len(clean_text)} characters of text. Spam filters block image-heavy emails.")
        
    # Check link count
    link_count = len(re.findall(r'<a\s+[^>]*href=', body_html, re.IGNORECASE))
    if link_count > 10:
        score += 10
        warnings.append(f"Email contains {link_count} links. High link count can trigger promotional/spam filters.")

    # 3. Domain authentication check if domain provided
    domain_results = None
    if sender_domain:
        try:
            domain_results = check_domain_deliverability(sender_domain)
            if domain_results.get("spf", {}).get("status") == "fail":
                score += 30
                warnings.append(f"Domain '{sender_domain}' missing Google SPF TXT record ('v=spf1 include:_spf.google.com ~all').")
            if domain_results.get("dmarc", {}).get("status") == "fail":
                score += 15
                warnings.append(f"Domain '{sender_domain}' missing DMARC DNS record.")
        except Exception:
            pass

    # Cap score at 100
    spam_score = min(100, score)
    
    if spam_score < 20:
        risk_level = "Low"
    elif spam_score < 50:
        risk_level = "Medium"
    else:
        risk_level = "High"
        
    if not warnings:
        warnings.append("Email content passed all spam pattern checks cleanly.")
        
    return {
        "spam_score": spam_score,
        "risk_level": risk_level,
        "warnings": warnings,
        "domain_auth": domain_results
    }
