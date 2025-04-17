# Standard library imports
import os
import json
import mimetypes
import tempfile
from datetime import datetime

# Third-party imports
import requests
from bs4 import BeautifulSoup

# Django imports
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.decorators import method_decorator
# Local app imports
from whatsapp.models import whatsappUsers, WhatsAppMessage
from whatsapp.service.whatsapp_api import fetch_contact
from whatsapp.helpers.utils import extract_file_url_from_msg_body,handle_new_message

# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
            print(data,'datassssssssssssssss')
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts")
                    our_number = settings.WHATSAPP_NUMBER

                    contact_name = None
                    if contacts:
                        contact_name = contacts[0].get("profile", {}).get("name")
                        print(contact_name,'contact nameeeeeeeeeeeeeeeee')

                    for msg in messages:
                        sender = msg.get("from")
                        msg_type = msg.get("type")

                        msg_body = ""
                        file_url = ""
                        mime_type = ""

                        if msg_type == "text":
                            msg_body = msg['text']['body']

                        elif msg_type in ["image", "audio", "video", "document"]:
                            media_id = msg[msg_type]["id"]
                            media_url = f"https://graph.facebook.com/v18.0/{media_id}"
                            headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}

                            # Step 1: Get the direct download URL
                            media_res = requests.get(media_url, headers=headers)
                            if media_res.status_code == 200:
                                direct_url = media_res.json().get("url")
                                media_content = requests.get(direct_url, headers=headers)
                                if media_content.status_code == 200:
                                    mime_type = media_content.headers.get("Content-Type")
                                    extension = mimetypes.guess_extension(mime_type)
                                    filename = f"received_{media_id}{extension}"

                                    subfolder = os.path.join(settings.MEDIA_ROOT, "whatsapp_received")
                                    os.makedirs(subfolder, exist_ok=True)
                                    path = os.path.join(subfolder, filename)

                                    with open(path, 'wb') as f:
                                        f.write(media_content.content)

                                    # Prepare the public link to serve the file
                                    public_url = f"{settings.MEDIA_URL}whatsapp_received/{filename}"
                                    msg_body = f"<a href='{public_url}' target='_blank'>View {msg_type}</a>"

                        message_obj = WhatsAppMessage.objects.create(
                            usernumber=sender,
                            id_phone=our_number,
                            msg_body=msg_body,
                            msg_status=0,
                            msg_type=msg_type,
                            mime_type=mime_type,
                            status=0,
                            local_date_time=now().strftime("%d-%m-%Y %H:%M:%S"),
                            created_date=now(),
                            modified_date=now(),
                            msg_sent_by="0",
                            temp_name = contact_name or ""
                        )

                        handle_new_message(message_obj,contact_name )

            return JsonResponse({"status": "received"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def get(self, request, *args, **kwargs):
        return JsonResponse({"error": "Invalid method"}, status=405)
    
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

                # ✅ Reset msgstatus to 0 since we're opening this chat
                user_obj.msgstatus = 0
                user_obj.save()

            messages_qs = WhatsAppMessage.objects.filter(Q(usernumber=phone) | Q(id_phone=phone)).order_by("msg_id")
            messages = []
   
            for m in messages_qs:
                soup = BeautifulSoup(m.msg_body or "", "html.parser")
                clean_body = soup.text.split("Time:")[0].strip()
                timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

                messages.append({
                "msg_body": m.msg_body,
                "msg_status": m.msg_status or 0,
                "msg_type": m.msg_type,
                "clean_body": clean_body,
                "timestamp": timestamp,
                "filename": m.filename,
                "file_url": extract_file_url_from_msg_body(m.msg_body),
                "mime_type": m.mime_type or "",
                "local_date_time": m.local_date_time,
                "sent_by": m.msg_sent_by,
            })
                
        chat_users = sorted(
            whatsappUsers.objects.all(),
            key=lambda user:WhatsAppMessage.objects.filter(usernumber=user.user_num).order_by("-msg_id").first().created_date
            if WhatsAppMessage.objects.filter(usernumber=user.user_num).exists() else user.created_date,reverse=True)

        return render(request, "whatsapp/interface.html", {
            "messages": messages,
            "user_phone": phone,
            "user_name": user_name,
            "user_exists": user_exists,
            "chat_users": chat_users,
        })

    def post(self, request):
        phone = request.GET.get("phone")
        message = request.POST.get("message")
        attachment = request.FILES.get('attachment')

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        if phone:
            if attachment:

                file_type,_ = mimetypes.guess_type(attachment.name)

                if not file_type:
                    return HttpResponse("Unsupported file type", status=400)
                
                file_name = slugify(os.path.splitext(attachment.name)[0]) + os.path.splitext(attachment.name)[1]

                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir,file_name)
                with open(file_path,"wb+") as f:
                    for chunks in attachment.chunks():
                        f.write(chunks)

                # Upload file to dynoble (replace with your real upload endpoint)
                upload_url = "https://dynoble.com/sales_new/application/views/waba/media_v2.php"

                with open(file_path,'rb') as file_data:
                    files = {'file':(file_name,file_data,file_type)}
                    upload_res = requests.post(upload_url, files=files, headers=headers) 

                if upload_res.status_code == 200:
                    uploaded_data = upload_res.json()
                    uploaded_url = uploaded_data.get("url") # Adjust based on real response

                    if not uploaded_url:
                        return HttpResponse("Upload failed. No file URL returned.", status=500)
                    
                    # Determine media type
                    if file_type.startswith("image/"):
                        msg_type = "image"
                    elif file_type.startswith("video/"):
                        msg_type = "video"
                    elif file_type.startswith("audio/"):
                        msg_type = "audio"
                    else:
                        msg_type = "document"

                    # Step 3: Send via WhatsApp Cloud API
                    WA_URL = f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages"
                    WA_HEADERS = {
                        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                        "Content-Type": "application/json"
                    }
                    wa_payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": msg_type,
                        msg_type: {
                            "link": uploaded_url
                        }
                    }
                    if message:
                        wa_payload[msg_type]["caption"] = message

                    send_res = requests.post(WA_URL, json=wa_payload, headers=WA_HEADERS)
                    print("SEND STATUS:", send_res.status_code)
                    print("SEND RESPONSE:", send_res.text)

                    message_id = None
                    try:
                        message_id = send_res.json()["messages"][0]["id"]
                    except:
                        pass

                    # Step 4: Save to DB
                    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    status = 1
                    color = "#03ac37" if status == 2 else "blue" 
                    our_number = settings.WHATSAPP_NUMBER

                    if msg_type == "image":
                        msg_body = f'<img src="{uploaded_url}" >'
                    elif msg_type == "video":
                        msg_body = f'<a href="{uploaded_url}" target="_blank">View video</a>'
                    elif msg_type == "audio":
                        msg_body = f'<a href="{uploaded_url}" target="_blank">Listen audio</a>'
                    else:
                        msg_body = f'<a href="{uploaded_url}" target="_blank">View document</a>'

                    if message:
                        msg_body += f'<p>{message}</p>'

                    msg_body += (
                        f'<p style="color:{color}; text-align:right; font-size:12px; margin-bottom:-5px;">'
                        f'Time:{timestamp} Message: {status}</p>'
                    )

                    WhatsAppMessage.objects.create(
                        msg_body=msg_body,
                        mime_type = file_type,
                        msg_status=1,
                        msg_type=msg_type,
                        status=status,
                        local_date_time=timestamp,
                        usernumber=phone,
                        created_date=datetime.now(),
                        modified_date=datetime.now(),
                        msg_sent_by="1",
                        send_id=message_id,
                        id_phone=our_number, 
                    )

                    return HttpResponseRedirect(f"{request.path}?phone={phone}")

            elif message:   
                # Send text message only
                WA_URL = f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages"

                WA_HEADERS = {
                    "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                    "Content-Type": "application/json"
                }

                wa_payload = {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }

                send_res = requests.post(WA_URL,headers=WA_HEADERS,json=wa_payload)
                print("TEXT SEND STATUS:", send_res.status_code)
                print("TEXT SEND RESPONSE:", send_res.text)

                our_number = settings.WHATSAPP_NUMBER

                message_id = None
                try:
                    message_id = send_res.json()["messages"][0]["id"]
                except:
                    pass


                timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                status = 1
                color = "#03ac37" if status == 2 else "blue" 

                msg_body = (
                    f'<p>{message}</p>'
                    f'<p style="color:{color}; text-align:right; font-size:12px; margin-bottom:-5px;">'
                    f'Time:{timestamp} Message: {status}</p>'
                )

                WhatsAppMessage.objects.create(
                    msg_body=msg_body,
                    msg_status=1,
                    msg_type="text",
                    status=status,
                    local_date_time=timestamp,
                    usernumber=phone,
                    created_date=datetime.now(),
                    modified_date=datetime.now(),
                    msg_sent_by="1",
                    send_id=message_id,
                    id_phone=our_number, 
                )

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
            our_num = settings.WHATSAPP_NUMBER

            if phone and name :
                obj,created = whatsappUsers.objects.get_or_create(
                    user_num = phone,
                    defaults={
                        "user_name":name,
                        "phoneid":phone,
                        "our_num":our_num,
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


@method_decorator(csrf_exempt, name='dispatch')
class FetchMessagesAPI(View):
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

            messages_qs = WhatsAppMessage.objects.filter(Q(usernumber=phone) | Q(id_phone=phone)).order_by("msg_id")
            messages = []
   
            for m in messages_qs:
                soup = BeautifulSoup(m.msg_body or "", "html.parser")
                clean_body = soup.text.split("Time:")[0].strip()
                timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

                messages.append({
                "msg_body": m.msg_body,
                "msg_status": m.msg_status or 0,
                "msg_type": m.msg_type,
                "clean_body": clean_body,
                "timestamp": timestamp,
                "filename": m.filename,
                "file_url": extract_file_url_from_msg_body(m.msg_body),
                "mime_type": m.mime_type or "",
                "local_date_time": m.local_date_time,
                "sent_by": m.msg_sent_by,
            })


        return JsonResponse({"messages": messages}, status=200)

class FetchChatUsersView(View):
    def get(self, request):
        users = sorted(
            whatsappUsers.objects.all(),
            key=lambda user:WhatsAppMessage.objects.filter(usernumber=user.user_num).order_by("-msg_id").first().created_date
            if WhatsAppMessage.objects.filter(usernumber=user.user_num).exists() else user.created_date,reverse=True)
        return JsonResponse({"users": list(users)})