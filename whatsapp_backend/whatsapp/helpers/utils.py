import requests
import json
from bs4 import BeautifulSoup
from django.conf import settings
from whatsapp.models import whatsappUsers,WhatsAppTemplate
from dashboard.models import Categories
from django.views import View
from django.http import JsonResponse

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

'''Send my database data to php with his api '''
class SendMessageWebhookView(View):
    def post(self, request):
        from django.views.decorators.csrf import csrf_exempt
        from django.utils.decorators import method_decorator
        import requests

        try:
            data = json.loads(request.body)
            payload = {
                "usernumber": data.get("usernumber"),
                "msg_body": data.get("msg_body"),
                "msg_type": data.get("msg_type"),
                "msg_status": data.get("msg_status"),
                "timestamp": data.get("timestamp"),
                "filename": data.get("filename"),
                "mime_type": data.get("mime_type"),
                "file_url": data.get("file_url"),
                "sent_by": data.get("sent_by"),
            }

            try:
                import requests
                requests.post(...)  # OK here
            except:
                pass

            res = requests.post("https://example.com/api/save_message.php", json=payload)

            if res.status_code == 200:
                return JsonResponse({"status": "success", "php_response": res.text})
            else:
                return JsonResponse({"status": "error", "message": res.text}, status=res.status_code)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        


def sync_templates_from_meta():
    url = f'https://graph.facebook.com/v18.0/{settings.WHATSAPP_BUSINESS_ID}/message_templates'
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        meta_templates = res.json().get("data", [])

        for tpl in meta_templates:

            components = tpl.get("components", [])
            header = next((c for c in components if c["type"] == "HEADER"), None)
            body = next((c for c in components if c["type"] == "BODY"), None)

            # Extract media if present
            media_url = None
            media_type = None
            if header and header.get("format") == "IMAGE":
                header_example = header.get("example", {})
                handles = header_example.get("header_handle", [])
                if handles:
                    media_url = handles[0]
                    media_type = "image"

            # Store the full components JSON in the description
            description_json = json.dumps({"components": components})

            WhatsAppTemplate.objects.update_or_create(
                template_name=tpl["name"],
                defaults={
                    "language": tpl.get("language") or "en_US",
                    "description": description_json,
                    "variable_count": len(body.get("parameters", [])) if body and "parameters" in body else 0,
                    "has_media": bool(media_url),
                    "media_type": media_type,
                    "media_url": media_url,
                }
            )
