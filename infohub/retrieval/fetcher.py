import requests
import time  # Neu importiert für das kleine Päuschen

def fetch(url: str):
    try:
        # Ein winziges Päuschen von 0.5 Sekunden einlegen,
        # damit die Server uns nicht als Aggro-Bot einstufen
        time.sleep(0.5)

        # Volle Browser-Signatur (schon super von dir vorbereitet!)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Upgrade-Insecure-Requests": "1"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10,  # Auf 10 Sekunden erhöht, falls Wikipedia mal kurz lahmt
            allow_redirects=True  # Erlaubt das saubere Folgen von Weiterleitungen
        )

        response.raise_for_status()

        return {
            "content": response.text
        }

    except requests.exceptions.RequestException as e:
        print(f"Fetch failed: {url} -> {e}")
        return {
            "content": ""
        }