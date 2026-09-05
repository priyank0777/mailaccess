import asyncio
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
