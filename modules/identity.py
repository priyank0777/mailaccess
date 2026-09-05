import asyncio
import hashlib
import re
import urllib.parse
import httpx

# Expanded Indian & Global First Names (includes Krish)
INDIAN_FIRST_NAMES = {
    "krish", "krishna", "karan", "kunal", "kartik", "kabir", "keshav", "kanishk", "kush",
    "shreya", "harshita", "priyank", "yash", "anand", "rahul", "rohit", "amit",
    "sumit", "deepak", "alok", "manish", "suresh", "ramesh", "mahesh", "dinesh",
    "aditya", "abhinav", "abhishek", "aman", "ankit", "arjun", "ayush", "chirag",
    "dhruv", "gaurav", "harsh", "ishaan", "manan", "mayank", "mohit", "nikhil",
    "parth", "pranav", "prateek", "rishabh", "siddharth", "tanmay", "tushar",
    "utkarsh", "vaibhav", "varun", "vikram", "vivek", "ananya", "pooja", "sneha",
    "priya", "neha", "tanvi", "riya", "isha", "aditi", "divya", "kavya", "aarushi"
}

INDIAN_MIDDLE_NAMES = {
    "raj", "kumar", "chandra", "prasad", "nath", "prakash", "dev", "kant",
    "bhan", "dutt", "jeet", "pal", "singh", "kaur", "lal", "mani", "swarup", "harshita"
}

INDIAN_SURNAMES = {
    "patel", "gupta", "sharma", "verma", "singh", "shah", "reddy", "nair", "rao",
    "mehta", "jain", "das", "roy", "dey", "ghosh", "sen", "banerjee", "mukherjee",
    "chatterjee", "iyer", "iyengar", "pillai", "menon", "bhat", "hegde", "shetty",
    "gowda", "naidu", "chowdary", "agarwal", "mittal", "bansal", "garg", "goel",
    "jindal", "singhal", "choudhary", "yadav", "mishra", "pandey", "tiwari",
    "shukla", "dubey", "chaubey", "pathak", "tripathi", "joshi", "bhatt", "pant",
    "kulkarni", "deshmukh", "patil", "pawar", "shinde", "gaikwad", "jadhav", "more"
}

# Tags & Noise Words commonly appended to emails
NOISE_TOKENS = {
    "vir", "dev", "coding", "official", "real", "pro", "main", "tech",
    "work", "app", "io", "in", "net", "mail", "personal", "code", "developer", "user"
}

def clean_and_segment_username(raw_user: str) -> dict:
    """Cleans delimiters, omits tags like 'vir', and segments first, middle & last names."""
    # Split by common delimiters (., _, -, +)
    parts = [p for p in re.split(r'[\._\-\+]+', raw_user.lower()) if p]

    # Filter out noise tags and standalone digits
    clean_parts = []
    for p in parts:
        clean_p = re.sub(r'^[0-9]+|[0-9]+$', '', p)
        if clean_p in NOISE_TOKENS or not clean_p:
            continue
        clean_parts.append(clean_p)

    if not clean_parts:
        clean_parts = [raw_user.lower()]

    # Case A: Already separated by delimiter (e.g. ['krish', 'patel'] or ['yash', 'raj', 'gupta'])
    if len(clean_parts) == 2:
        return {
            "first": clean_parts[0].capitalize(),
            "middle": "",
            "last": clean_parts[1].capitalize()
        }
    elif len(clean_parts) >= 3:
        return {
            "first": clean_parts[0].capitalize(),
            "middle": " ".join([p.capitalize() for p in clean_parts[1:-1]]),
            "last": clean_parts[-1].capitalize()
        }

    # Case B: Compound string (e.g. 'krishpatel' or 'shreyaharshita' or 'yashrajgupta')
    core = clean_parts[0]

    matched_surname = ""
    for s in INDIAN_SURNAMES:
        if core.endswith(s) and len(core) > len(s):
            matched_surname = s
            core = core[:-len(s)]
            break

    matched_middle = ""
    for m in INDIAN_MIDDLE_NAMES:
        if core.endswith(m) and len(core) > len(m):
            matched_middle = m
            core = core[:-len(m)]
            break

    if not matched_surname and not matched_middle:
        for fn in INDIAN_FIRST_NAMES:
            if core.startswith(fn) and len(core) > len(fn):
                remainder = core[len(fn):]
                return {
                    "first": fn.capitalize(),
                    "middle": remainder.capitalize(),
                    "last": ""
                }

    first = core.capitalize() if core else ""
    middle = matched_middle.capitalize() if matched_middle else ""
    last = matched_surname.capitalize() if matched_surname else ""

    return {"first": first, "middle": middle, "last": last}

def parse_name_tokens(full_name: str) -> dict:
    parts = full_name.strip().split()
    first = ""
    middle = ""
    last = ""

    if len(parts) == 1:
        first = parts[0]
    elif len(parts) == 2:
        if parts[0].lower() in INDIAN_FIRST_NAMES and parts[1].lower() in INDIAN_MIDDLE_NAMES:
            first = parts[0]
            middle = parts[1]
        else:
            first = parts[0]
            last = parts[1]
    elif len(parts) >= 3:
        first = parts[0]
        middle = " ".join(parts[1:-1])
        last = parts[-1]

    permutations = []
    if first and last:
        if middle:
            permutations.append(f"{first} {middle} {last}")
            permutations.append(f"{first}{middle} {last}")
            permutations.append(f"{first} {last}")
        else:
            permutations.append(f"{first} {last}")
    elif first and middle:
        permutations.append(f"{first} {middle}")
    elif first:
        permutations.append(first)

    return {
        "first_name": first,
        "middle_name": middle,
        "last_name": last,
        "permutations": list(dict.fromkeys(permutations))
    }

async def resolve_owner_identity(email: str) -> dict:
    clean_email = email.strip().lower()
    raw_user = clean_email.split("@")[0]
    email_hash = hashlib.md5(clean_email.encode("utf-8")).hexdigest()

    discovered_name = None
    discovered_handle = None
    custom_avatar = None
    verification_source = "Lexicon Tokenizer"

    async with httpx.AsyncClient(timeout=7.0) as client:
        # Check Git Commits for Real Author Signature
        try:
            gh_url = f"https://api.github.com/search/commits?q=author-email:{clean_email}&sort=author-date&order=desc"
            gh_headers = {"Accept": "application/vnd.github.cloak-preview+json", "User-Agent": "MailAccess-OSINT"}
            r = await client.get(gh_url, headers=gh_headers)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for item in items:
                    commit_author = item.get("commit", {}).get("author", {})
                    author_name = commit_author.get("name")
                    if author_name and len(author_name) > 2 and author_name.lower() not in ["root", "admin", "github-actions"]:
                        discovered_name = author_name
                        verification_source = "Git Commit Signature"

                    gh_author = item.get("author")
                    if gh_author and gh_author.get("login"):
                        discovered_handle = gh_author.get("login")
                        if gh_author.get("avatar_url"):
                            custom_avatar = gh_author.get("avatar_url")
                        break
        except Exception:
            pass

        # Check Gravatar
        if not custom_avatar:
            try:
                grav_check = await client.get(f"https://www.gravatar.com/avatar/{email_hash}?d=404")
                if grav_check.status_code == 200:
                    custom_avatar = f"https://www.gravatar.com/avatar/{email_hash}?s=200"
                    verification_source = "Gravatar Profile"
            except Exception:
                pass

        if not discovered_name:
            try:
                grav_url = f"https://en.gravatar.com/{email_hash}.json"
                r = await client.get(grav_url)
                if r.status_code == 200:
                    entry = r.json().get("entry", [{}])[0]
                    name_cand = entry.get("name", {}).get("formatted") or entry.get("displayName")
                    if name_cand:
                        discovered_name = name_cand
                        verification_source = "Gravatar vCard"
            except Exception:
                pass

    # Clean and segment username (omits 'vir', 'coding', numbers)
    seg = clean_and_segment_username(raw_user)

    if discovered_name:
        name_info = parse_name_tokens(discovered_name)
    else:
        if seg["first"]:
            reconstructed = f"{seg['first']} {seg['middle']} {seg['last']}".replace("  ", " ").strip()
            name_info = parse_name_tokens(reconstructed)
            discovered_name = reconstructed
        else:
            clean_cand = re.sub(r'[\._\-\+][a-zA-Z0-9]+$', '', raw_user)
            name_info = {
                "first_name": clean_cand.capitalize() if clean_cand else raw_user,
                "middle_name": "",
                "last_name": "",
                "permutations": [clean_cand.capitalize() if clean_cand else raw_user]
            }
            discovered_name = name_info["first_name"]

    display_name = discovered_name or raw_user
    if not custom_avatar:
        encoded_name = urllib.parse.quote_plus(display_name)
        avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=0284c7&color=ffffff&bold=true&size=160"
    else:
        avatar_url = custom_avatar

    candidate_handles = [raw_user]
    if discovered_handle:
        candidate_handles.insert(0, discovered_handle)

    fn = name_info["first_name"].lower().replace(" ", "")
    mn = name_info["middle_name"].lower().replace(" ", "")
    ln = name_info["last_name"].lower().replace(" ", "")

    if fn and ln:
        candidate_handles.append(f"{fn}{ln}")
        candidate_handles.append(f"{fn}_{ln}")
        candidate_handles.append(f"{fn}.{ln}")
    if fn and mn:
        candidate_handles.append(f"{fn}{mn}")

    clean_base = raw_user.split(".")[0]
    if clean_base not in candidate_handles:
        candidate_handles.append(clean_base)

    unique_handles = list(dict.fromkeys([h for h in candidate_handles if len(h) >= 3]))

    return {
        "status": "SUCCESS",
        "full_name": display_name,
        "first_name": name_info["first_name"],
        "middle_name": name_info["middle_name"],
        "last_name": name_info["last_name"],
        "permutations": name_info["permutations"],
        "primary_handle": unique_handles[0],
        "candidate_handles": unique_handles,
        "avatar_url": avatar_url,
        "verification_source": verification_source
    }
