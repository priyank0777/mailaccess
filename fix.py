import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(MODULES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

FILES = {
    # -------------------------------------------------------------
    # 1. Identity & Name Segmenter with Delimiter & Tag Stripping
    # -------------------------------------------------------------
    "modules/identity.py": '''import asyncio
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
''',

    # -------------------------------------------------------------
    # 2. Account Discovery (Accurate & Fast)
    # -------------------------------------------------------------
    "modules/account_discovery.py": '''import asyncio
import urllib.parse
import httpx

async def check_github(client: httpx.AsyncClient, email: str, candidates: list) -> dict:
    headers = {"Accept": "application/vnd.github.cloak-preview+json", "User-Agent": "MailAccess-OSINT"}

    try:
        url = f"https://api.github.com/search/commits?q=author-email:{email}&sort=author-date"
        r = await client.get(url, headers=headers, timeout=5.0)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                author_obj = item.get("author")
                if author_obj and author_obj.get("login"):
                    login = author_obj.get("login")
                    return {
                        "platform": "GitHub",
                        "category": "Developer",
                        "handle": f"@{login}",
                        "profile_url": f"https://github.com/{login}",
                        "exists": True,
                        "color": "purple"
                    }
    except Exception:
        pass

    for u in candidates:
        try:
            r = await client.get(f"https://api.github.com/users/{u}", headers=headers, timeout=4.0)
            if r.status_code == 200:
                login = r.json().get("login", u)
                return {
                    "platform": "GitHub",
                    "category": "Developer",
                    "handle": f"@{login}",
                    "profile_url": f"https://github.com/{login}",
                    "exists": True,
                    "color": "purple"
                }
        except Exception:
            pass

    return {"platform": "GitHub", "exists": False}

async def check_instagram_and_threads(client: httpx.AsyncClient, email: str, username: str) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/accounts/emailsignup/",
        "X-Requested-With": "XMLHttpRequest"
    }
    results = []
    try:
        init_res = await client.get("https://www.instagram.com/accounts/emailsignup/", headers=headers, timeout=4.0)
        csrf_token = init_res.cookies.get("csrftoken") or "missing"
        headers["X-CSRFToken"] = csrf_token

        check_url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/"
        post_res = await client.post(check_url, data={"email": email}, headers=headers, timeout=5.0)
        resp_text = post_res.text.lower()

        if "email_is_taken" in resp_text or "another account is using the same email" in resp_text:
            results.append({
                "platform": "Instagram",
                "category": "Social Media",
                "handle": f"@{username}",
                "profile_url": f"https://instagram.com/{username}",
                "exists": True,
                "color": "pink"
            })
            results.append({
                "platform": "Threads",
                "category": "Social Media",
                "handle": f"@{username}",
                "profile_url": f"https://threads.net/@{username}",
                "exists": True,
                "color": "cyan"
            })
    except Exception:
        pass
    return results

async def check_spotify(client: httpx.AsyncClient, email: str) -> dict:
    url = f"https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
    try:
        r = await client.get(url, headers=headers, timeout=4.0)
        if r.status_code == 200:
            data = r.json()
            errors = str(data.get("errors", {})).lower()
            if data.get("status") == 20 or "already registered" in errors or "email_exists" in errors:
                return {
                    "platform": "Spotify",
                    "category": "Music / Streaming",
                    "handle": "Registered Account",
                    "profile_url": "https://open.spotify.com",
                    "exists": True,
                    "color": "emerald"
                }
    except Exception:
        pass
    return {"platform": "Spotify", "exists": False}

async def check_linkedin(client: httpx.AsyncClient, identity: dict) -> list:
    results = []
    permutations = identity.get("permutations", [])
    target_name = permutations[0] if permutations else identity.get("full_name")

    if target_name and target_name != "Unknown / Private":
        encoded = urllib.parse.quote_plus(f'"{target_name}"')
        results.append({
            "platform": "LinkedIn",
            "category": "Professional",
            "handle": f"Search: {target_name}",
            "profile_url": f"https://www.google.com/search?q=site:linkedin.com/in+{encoded}",
            "exists": True,
            "color": "blue"
        })
    return results

async def check_twitter_x(client: httpx.AsyncClient, email: str, username: str) -> dict:
    url = f"https://api.twitter.com/i/users/email_available.json?email={email}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
    try:
        r = await client.get(url, headers=headers, timeout=4.0)
        if r.status_code == 200 and r.json().get("taken") is True:
            return {
                "platform": "X (formerly Twitter)",
                "category": "Social Media",
                "handle": f"@{username}",
                "profile_url": f"https://x.com/{username}",
                "exists": True,
                "color": "slate"
            }
    except Exception:
        pass
    return {"platform": "X (formerly Twitter)", "exists": False}

async def check_duolingo(client: httpx.AsyncClient, email: str, username: str) -> dict:
    url = f"https://www.duolingo.com/2017-06-30/users?email={email}"
    try:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4.0)
        if r.status_code == 200:
            users = r.json().get("users", [])
            if len(users) > 0:
                d_user = users[0].get("username", username)
                return {
                    "platform": "Duolingo",
                    "category": "Education",
                    "handle": f"@{d_user}",
                    "profile_url": f"https://www.duolingo.com/profile/{d_user}",
                    "exists": True,
                    "color": "emerald"
                }
    except Exception:
        pass
    return {"platform": "Duolingo", "exists": False}

async def scan_account_discovery(email: str, identity: dict) -> dict:
    clean_email = email.strip().lower()
    candidate_handles = identity.get("candidate_handles", [clean_email.split("@")[0]])
    primary_handle = candidate_handles[0]

    async with httpx.AsyncClient(follow_redirects=True) as client:
        gh_task = check_github(client, clean_email, candidate_handles)
        spot_task = check_spotify(client, clean_email)
        meta_task = check_instagram_and_threads(client, clean_email, primary_handle)
        tw_task = check_twitter_x(client, clean_email, primary_handle)
        duo_task = check_duolingo(client, clean_email, primary_handle)
        li_task = check_linkedin(client, identity)

        gh_res, spot_res, meta_res, tw_res, duo_res, li_res = await asyncio.gather(
            gh_task, spot_task, meta_task, tw_task, duo_task, li_task
        )

    all_raw = [gh_res, spot_res] + meta_res + [tw_res, duo_res] + li_res
    matched = [acc for acc in all_raw if acc.get("exists") is True]

    return {
        "status": "SUCCESS",
        "total_scanned": len(all_raw),
        "total_found": len(matched),
        "accounts": matched
    }
'''
}

print("[*] Updating MailAccess with Delimiter & Tag-Stripping Tokenizer...")
for rel_path, content in FILES.items():
    full_path = os.path.join(BASE_DIR, rel_path)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [✔] Updated {rel_path}")

print("\n[✔] Done! 'vir' and tag stripping activated.")
print("[*] Refresh your dashboard at http://127.0.0.1:8000")