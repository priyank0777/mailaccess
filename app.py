import asyncio
import json
import time
import os
import urllib.parse
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from modules.identity import resolve_owner_identity
from modules.credibility import analyze_email_credibility
from modules.dns_intel import inspect_domain_dns
from modules.social_footprint import check_gravatar, search_github_commits, check_keybase
from modules.breaches import check_hudson_rock_stealer, check_hibp_breaches
from modules.account_discovery import scan_account_discovery
from modules.dorks import generate_google_dorks

app = FastAPI(title="MailAccess OSINT Suite")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/scan/stream")
async def scan_stream(email: str, hibp_key: str = ""):
    async def event_generator():
        email_clean = email.strip()
        domain = email_clean.split("@")[1] if "@" in email_clean else ""

        yield f"data: {json.dumps({'type': 'init', 'target': email_clean})}\n\n"

        # Step 1: Resolve Identity, Name Tokens & Avatar
        identity_res = await resolve_owner_identity(email_clean)
        yield f"data: {json.dumps({'type': 'identity', 'data': identity_res})}\n\n"

        # Step 2: Run Recon Modules
        modules = [
            ("email_credibility", analyze_email_credibility, [email_clean]),
            ("account_discovery", scan_account_discovery, [email_clean, identity_res]),
            ("hudson_rock", check_hudson_rock_stealer, [email_clean]),
            ("gravatar", check_gravatar, [email_clean]),
            ("keybase", check_keybase, [email_clean]),
            ("dns_lookup", inspect_domain_dns, [domain]),
            ("github_commits", search_github_commits, [email_clean]),
            ("hibp", check_hibp_breaches, [email_clean, hibp_key if hibp_key else None]),
        ]

        full_results = {"identity": identity_res}

        for module_name, func, args in modules:
            start_t = time.time()
            try:
                if asyncio.iscoroutinefunction(func):
                    res = await func(*args)
                else:
                    res = func(*args)
                status = res.get("status", "SUCCESS") if isinstance(res, dict) else "SUCCESS"
            except Exception as e:
                res = {"error": str(e), "status": "FAILED"}
                status = "FAILED"

            elapsed = round(time.time() - start_t, 2)
            full_results[module_name] = res

            payload = {
                "type": "module_update",
                "module": module_name,
                "status": status,
                "elapsed": f"{elapsed}s",
                "data": res
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.08)

        # Step 3: Google Dorks
        dorks = generate_google_dorks(email_clean)
        for perm in identity_res.get("permutations", [])[:2]:
            q = f'"{perm}" "{email_clean}"'
            dorks.insert(0, {
                "category": "Owner Permutation",
                "title": f'Exact Match: "{perm}"',
                "query": q,
                "url": f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            })

        yield f"data: {json.dumps({'type': 'dorks', 'data': dorks})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'summary': full_results})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
