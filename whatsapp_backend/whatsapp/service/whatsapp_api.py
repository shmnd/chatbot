import requests

def fetch_contact(page=1):
    try:
        url = f"https://dynoble.com/app/API/fetach_contacts.php?page={page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        response = requests.get(url,headers=headers,timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print('Contact Api Error',e)
        return[]
