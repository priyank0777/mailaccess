import hashlib
import httpx

async def check_gravatar(email: str) -> dict:
    email_clean = email.strip().lower()
    email_hash = hashlib.md5(email_clean.encode('utf-8')).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
    profile_url = f"https://www.gravatar.com/{email_hash}.json"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(profile_url)
            if r.status_code == 200:
                data = r.json()
                entry = data.get("entry", [{}])[0]
                return {
                    "status": "SUCCESS",
                    "found": True,
                    "avatar_url": gravatar_url,
                    "display_name": entry.get("displayName"),
                    "profile_url": entry.get("profileUrl", f"https://gravatar.com/{email_clean.split('@')[0]}"),
                    "location": entry.get("currentLocation")
                }
        except Exception:
            pass

    return {"status": "SUCCESS", "found": False, "avatar_url": None}

async def search_github_commits(email: str) -> dict:
    url = f"https://api.github.com/search/commits?q=author-email:{email}&sort=author-date&order=desc"
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "User-Agent": "MailAccess-OSINT-Suite"
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                total_count = data.get("total_count", 0)
                items = data.get("items", [])
                commits = []
                discovered_logins = set()

                for item in items[:5]:
                    commits.append({
                        "repo": item.get("repository", {}).get("full_name"),
                        "message": item.get("commit", {}).get("message"),
                        "date": item.get("commit", {}).get("author", {}).get("date"),
                        "url": item.get("html_url")
                    })
                    # Extract REAL GitHub login from commit author
                    author_obj = item.get("author")
                    if author_obj and author_obj.get("login"):
                        discovered_logins.add(author_obj.get("login"))

                return {
                    "status": "SUCCESS",
                    "commit_count": total_count,
                    "recent_commits": commits,
                    "discovered_logins": list(discovered_logins)
                }
            elif r.status_code == 403:
                return {"status": "PARTIAL", "commit_count": 0, "recent_commits": [], "discovered_logins": []}
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "commit_count": 0, "discovered_logins": []}

    return {"status": "SUCCESS", "commit_count": 0, "recent_commits": [], "discovered_logins": []}

async def check_keybase(email: str) -> dict:
    username = email.split("@")[0]
    url = f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={username}"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                them = data.get("them", [])
                if them and them[0] is not None:
                    user = them[0]
                    return {
                        "status": "SUCCESS",
                        "found": True,
                        "username": user.get("basics", {}).get("username"),
                        "bio": user.get("profile", {}).get("bio")
                    }
        except Exception:
            pass

    return {"status": "SUCCESS", "found": False}
