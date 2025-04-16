import re
from bs4 import BeautifulSoup

def extract_file_url_from_msg_body(msg_body):
    if not msg_body:
        return ""
    soup = BeautifulSoup(msg_body, "html.parser")
    tag = soup.find(["img", "a", "video", "audio"])
    if tag and tag.get("src"):
        return tag["src"]
    if tag and tag.get("href"):
        return tag["href"]
    return ""