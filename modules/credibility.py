import re
import dns.resolver

DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "trashmail.com", "sharklasers.com", "throwawaymail.com",
    "getnada.com", "dispostable.com", "fakeinbox.com", "mohmal.com"
}

FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "protonmail.com", "proton.me", "aol.com", "zoho.com"
}

def analyze_email_credibility(email: str) -> dict:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return {
            "status": "FAILED",
            "score": 0,
            "valid_syntax": False,
            "is_disposable": False,
            "is_free_provider": False,
            "has_mx": False,
            "details": "Invalid email syntax format."
        }

    domain = email.split("@")[1].lower()
    is_disposable = domain in DISPOSABLE_DOMAINS
    is_free = domain in FREE_PROVIDERS

    has_mx = False
    mx_records = []
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        mx_records = [str(r.exchange).rstrip('.') for r in answers]
        has_mx = len(mx_records) > 0
    except Exception:
        has_mx = False

    score = 100
    if not has_mx:
        score -= 70
    if is_disposable:
        score -= 60
    if is_free:
        score -= 10

    score = max(0, min(100, score))

    return {
        "status": "SUCCESS" if has_mx and not is_disposable else "PARTIAL",
        "score": score,
        "domain": domain,
        "valid_syntax": True,
        "is_disposable": is_disposable,
        "is_free_provider": is_free,
        "has_mx": has_mx,
        "mx_records": mx_records[:3],
        "details": "Credibility verified" if score > 70 else "High-risk or disposable address"
    }
