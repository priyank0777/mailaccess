import httpx

async def check_hudson_rock_stealer(email: str) -> dict:
    """Queries Hudson Rock Cavalier API to detect infected machines, malware families, and logged in software."""
    url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email={email}"
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                stealers = data.get("stealers", [])
                
                parsed_stealers = []
                for s in stealers:
                    parsed_stealers.append({
                        "computer_name": s.get("computer_name") or s.get("hostname") or "UNKNOWN-PC",
                        "operating_system": s.get("operating_system") or "Windows",
                        "malware_family": s.get("malware_family") or "Infostealer",
                        "date_compromised": s.get("date_compromised") or "Recent",
                        "antivirus": s.get("antivirus_installed") or "None / Disabled",
                        "ip": s.get("ip") or "Masked"
                    })

                return {
                    "status": "SUCCESS",
                    "infected": len(stealers) > 0,
                    "stealer_count": len(stealers),
                    "machines": parsed_stealers[:5]
                }
        except Exception as e:
            return {"status": "PARTIAL", "infected": False, "stealer_count": 0, "machines": [], "error": str(e)}

    return {"status": "SUCCESS", "infected": False, "stealer_count": 0, "machines": []}

async def check_hibp_breaches(email: str, api_key: str = None) -> dict:
    if not api_key:
        return {
            "status": "SKIPPED",
            "message": "HIBP API key not configured."
        }

    headers = {"hibp-api-key": api_key, "User-Agent": "MailAccess-OSINT"}
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"

    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                breaches = r.json()
                return {
                    "status": "SUCCESS",
                    "breached": True,
                    "breach_count": len(breaches),
                    "breaches": [b.get("Name") for b in breaches]
                }
            elif r.status_code == 404:
                return {"status": "SUCCESS", "breached": False, "breach_count": 0, "breaches": []}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    return {"status": "PARTIAL", "breached": False, "breach_count": 0, "breaches": []}
