import urllib.parse

def generate_google_dorks(email: str) -> list:
    username = email.split("@")[0]
    domain = email.split("@")[1]

    dorks = [
        {"category": "Paste & Leak Dumps", "title": "Pastebin & Dump Sites", "query": f'site:pastebin.com | site:rentry.co | site:ghostbin.com "{email}"'},
        {"category": "Leaked Documents & Logs", "title": "Confidential / Log Files", "query": f'ext:log | ext:txt | ext:env | ext:sql "{email}"'},
        {"category": "Domain Files", "title": "Domain PDF / Doc Mentions", "query": f'site:{domain} filetype:pdf | filetype:docx "{username}"'},
        {"category": "Source Code", "title": "GitHub / GitLab Mentions", "query": f'site:github.com | site:gitlab.com "{email}"'}
    ]

    for d in dorks:
        encoded = urllib.parse.quote_plus(d["query"])
        d["url"] = f"https://www.google.com/search?q={encoded}"

    return dorks
