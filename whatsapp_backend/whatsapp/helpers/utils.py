from bs4 import BeautifulSoup
from whatsapp.models import whatsappUsers, WhatsAppMessage

'''for extract file url from message body'''
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


'''if user recieve new message it show in contact list'''
def handle_new_message(message, contact_name=None,current_open_number=None):
    user_number = message.usernumber
    if user_number:
        user, created = whatsappUsers.objects.get_or_create(
            user_num=user_number,
            defaults={
                "phoneid": message.id_phone,
                "our_num": message.ournum,
                "user_name": contact_name,
                "timestamps": message.timestamp,
                "msgstatus": 1
            }
        )
        if not created:
            user.timestamps = message.timestamp
            # ✅ Only set msgstatus = 1 if it's not currently open in the browser
            if current_open_number is None or user_number != current_open_number:
                user.msgstatus = 1
            if contact_name and not user.user_name:
                user.user_name = contact_name
            user.save()

