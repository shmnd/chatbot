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
from whatsapp.models import whatsappUsers,WhatsAppMessage
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
        message = request.POST.get("message")
        attachment = request.FILES.get('attachment')

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        if phone:
            if attachment:

                file_type,_ = mimetypes.guess_type(attachment.name)
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

                print('resultttttttttt')
                print("UPLOAD STATUS:", upload_res.status_code)
                print("UPLOAD RESPONSE TEXT:", upload_res.text)

                if upload_res.status_code == 200:
                    uploaded_data = upload_res.json()
                    uploaded_url = uploaded_data.get("url") # Adjust based on real response
                    
                    # Determine media type
                    if file_type.startswith("image/"):
                        media_type = "image"
                    elif file_type.startswith("video/"):
                        media_type = "video"
                    elif file_type.startswith("audio/"):
                        media_type = "audio"
                    else:
                        media_type = "document"
                    
                    # Send media using single API
                    send_url = f"https://dynoble.com/app/API/sendmedia.php?userphone={phone}&type={media_type}&media_url={uploaded_url}"

                    if message:
                        send_url += f"&caption={message}"

                    print('urlllllllllllllllllll')
                    print("📦 Uploaded media URL:", uploaded_url)
                    print("📤 Final send URL:", send_url)

                    requests.get(send_url, headers=headers)

            elif message:   
                # Send text message only
                send_url = f"https://dynoble.com/app/API/sendtextmessage.php?userphone={phone}&messages={message}"
                requests.get(send_url,headers=headers)

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


