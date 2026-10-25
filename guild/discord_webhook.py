import requests

RED = 0xB22222  # Horde red


def send_embed(url, title, description, link=None):
    """Post an embed. Returns True on success; never raises (Discord being down
    must not break saving)."""
    if not url:
        return False
    embed = {"title": title[:256], "description": description[:4000], "color": RED}
    if link:
        embed["url"] = link
    try:
        r = requests.post(
            url,
            json={"embeds": [embed], "allowed_mentions": {"parse": []}},
            timeout=8,
        )
        return r.ok
    except requests.RequestException:
        return False
