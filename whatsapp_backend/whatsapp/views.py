import os
import mimetypes
import tempfile
import requests
from django.utils.text import slugify
from django.views import View
from django.shortcuts import render,redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from whatsapp.service.whatsapp_api import fetch_contact
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from bs4 import BeautifulSoup
from whatsapp.models import whatsappUsers
from django.conf import settings
from datetime import datetime
from django.urls import reverse
# Create your views here.
class WhatsappHomePageView(LoginRequiredMixin, View):
    def get(self, request):
        phone = request.GET.get("phone", "").strip()
        messages = []

        user_exists = False
        user_name = phone

        if phone:
            user_obj = whatsappUsers.objects.filter(user_num=phone).first()
            if user_obj:
                user_exists = True
                user_name = user_obj.user_name or phone

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            res = requests.get(
                f"https://dynoble.com/app/API/fetch_chats.php?user_num={phone}",
                headers=headers,
            )

            if res.status_code == 200:
                messages = res.json()

                for m in messages:
                    m["msg_status"] = int(m.get("msg_status", 0))
                    raw = m.get("msg_body", "")

                    soup = BeautifulSoup(raw, "html.parser")
                    m["clean_body"] = soup.text.split("Time:")[0].strip()
                    m["timestamp"] = soup.text.split("Time:")[1].strip() if "Time:" in soup.text else ""

                    if m.get("filename"):
                        m["file_url"] = f"https://dynoble.com/uploads/{m['filename']}"

        return render(request, "whatsapp/interface.html", {
            "messages": messages,
            "user_phone": phone,
            "user_name": user_name,
            "user_exists": user_exists,
            "chat_users": whatsappUsers.objects.all().order_by("-timestamps")
        })

    def post(self, request):
        phone = request.GET.get("phone")
        message = request.POST.get("message", "").strip()
        attachment = request.FILES.get("attachment")

        PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
        ACCESS_TOKEN = settings.WHATSAPP_TOKEN

        if phone and attachment:
            file_type, _ = mimetypes.guess_type(attachment.name)
            print("Detected File Type:", file_type)

            filename = slugify(os.path.splitext(attachment.name)[0]) + os.path.splitext(attachment.name)[1]
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            print("Saving to:", file_path)

            with open(file_path, "wb+") as f:
                for chunk in attachment.chunks():
                    f.write(chunk)

            try:
                upload_url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/media"
                upload_headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                }

                with open(file_path, 'rb') as file_stream:
                    files = {
                        'file': (filename, file_stream),
                        'type': (None, file_type or 'image/jpeg'),
                        'messaging_product': (None, 'whatsapp')
                    }

                    upload_response = requests.post(upload_url, headers=upload_headers, files=files)
                    print("Upload Status:", upload_response.status_code)
                    print("Upload Response:", upload_response.text)

                    if upload_response.status_code == 200:
                        media_id = upload_response.json().get("id")
                        print(media_id,'idddddddddddddddddddddd')

                        send_url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
                        send_headers = {
                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }

                        media_type = file_type.split("/")[0] if file_type else "document"

                        if media_type == "image":
                            payload = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": phone,
                                "type": "image",
                                "image": {
                                    "id": media_id,
                                    "link": "<MEDIA_URL>",
                                    "caption": message or ""
                                }
                            }
                        elif media_type == "video":
                            payload = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": phone,
                                "type": "video",
                                "video": {
                                    "id": media_id,
                                    "caption": message or ""
                                }
                            }
                        elif media_type == "audio":
                            payload = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": phone,
                                "type": "audio",
                                "audio": {
                                    "id": media_id
                                }
                            }
                        else:
                            payload = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": phone,
                                "type": "document",
                                "document": {
                                    "id": media_id,
                                    "caption": message or ""
                                }
                            }

                        send_response = requests.post(send_url, headers=send_headers, json=payload)
                        print("Send Status:", send_response.status_code)
                        print("Send Response:", send_response.text)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        elif phone and message:
            send_url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
            send_headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }

            send_response = requests.post(send_url, headers=send_headers, json=payload)
            print("Text Status:", send_response.status_code)
            print("Text Response:", send_response.text)

        return HttpResponseRedirect(f"{request.path}?phone={phone}")



class WhatsappContactView(LoginRequiredMixin,View):

    def get(self,request,*args, **kwargs):
        search = request.GET.get("search", "")
        page = request.GET.get('page',1)
        starts_with = request.GET.get("starts_with", "")
        contacts = fetch_contact()

        if search:
            contacts = [
                contact for contact in contacts
                if search.lower() in contact.get("user_name", "").lower() or search in contact.get("user_num", "")
            ]

        # Apply A–Z filter
        if starts_with:
            contacts = [
                contact for contact in contacts
                if contact.get("user_name", "").lower().startswith(starts_with.lower())
            ]

        paginator = Paginator(contacts, 20)  # 20 per page
        page_obj = paginator.get_page(page)


        return render(request,'whatsapp/contact.html',{
            'search':search,
            'page_obj':page_obj,
            'starts_with': starts_with,

            })
    
class SaveContactView(View):

    def __init__(self, **kwargs):
        self.response_format = {"status_code": 101, "message": "", "error": ""}

    def post(self,request):
        try:
            phone = request.POST.get('phone','')
            name = request.POST.get('name','')
            your_num = settings.WHATSAPP_NUMBER

            if phone and name :
                obj,created = whatsappUsers.objects.get_or_create(
                    user_num = phone,
                    defaults={
                        "user_name":name,
                        "phoneid":phone,
                        "our_num":your_num,
                        "date_time": datetime.now(),
                        "view_order": 0,
                        "agent_id": 0,
                        "timestamps": int(datetime.now().timestamp()),
                        "msgstatus": 0,
                        "lead_status": 1
                    }
                )
                if not created:
                    obj.user_name = name
                    obj.timestamps = int(datetime.now().timestamp())
                    obj.save()
                return redirect(f"{reverse('whatsapp:interface')}?phone={phone}")
            return redirect("whatsapp:interface")
        except Exception as e:
            self.response_format['message'] = 'error'
            self.response_format['error'] = str(e)


