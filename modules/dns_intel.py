import dns.resolver

def inspect_domain_dns(domain: str) -> dict:
    results = {
        "spf_found": False,
        "spf_record": None,
        "dmarc_found": False,
        "dmarc_record": None,
        "nameservers": []
    }

    try:
        answers = dns.resolver.resolve(domain, 'TXT')
        for rdata in answers:
            txt_content = b''.join(rdata.strings).decode('utf-8', errors='ignore')
            if "v=spf1" in txt_content:
                results["spf_found"] = True
                results["spf_record"] = txt_content
                break
    except Exception:
        pass

    try:
        dmarc_domain = f"_dmarc.{domain}"
        answers = dns.resolver.resolve(dmarc_domain, 'TXT')
        for rdata in answers:
            txt_content = b''.join(rdata.strings).decode('utf-8', errors='ignore')
            if "v=DMARC1" in txt_content:
                results["dmarc_found"] = True
                results["dmarc_record"] = txt_content
                break
    except Exception:
        pass

    try:
        answers = dns.resolver.resolve(domain, 'NS')
        results["nameservers"] = [str(r.target).rstrip('.') for r in answers]
    except Exception:
        pass

    return results
