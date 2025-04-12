from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from whatsapp.service.whatsapp_api import fetch_contact
from django.core.paginator import Paginator
import requests
from django.http import HttpResponseRedirect
import re
from bs4 import BeautifulSoup
# Create your views here.
class WhatsappHomePageView(LoginRequiredMixin, View):
    def get(self, request):
        phone = request.GET.get("phone")
        messages = []

        if phone:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"  # Spoof a browser
            }

            res = requests.get(
                f"https://dynoble.com/app/API/fetch_chats.php?user_num={phone}",
                headers=headers,
            )

            if res.status_code == 200:
                messages = res.json()

                # Normalize keys so the template can render them
                for m in messages:
                    m["msg_status"] = int(m.get("msgstatus", 0))
                    raw = m.get("msg_body", "")
                    
                    # Extract the message without HTML
                    soup = BeautifulSoup(raw, "html.parser")
                    m["clean_body"] = soup.text.split("Time:")[0].strip()  # actual message
                    m["timestamp"] = soup.text.split("Time:")[1].strip() if "Time:" in soup.text else ""

        return render(request, "whatsapp/interface.html", {
            "messages": messages,
            "user_phone": phone,
            "user_name": phone,
            'headers':headers  
        })


    def post(self, request):
        phone = request.GET.get("phone")
        message = request.POST.get("message")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        if phone and message:
            send_url = f"https://dynoble.com/app/API/sendtextmessage.php?userphone={phone}&messages={message}"
            requests.get(send_url,headers=headers)

        return HttpResponseRedirect(f"{request.path}?phone={phone}")
    

# class whatsappChatView(View):

#     def get(self,request,*args, **kwargs):
#         phone = request.GET.get('phone')
#         messages = []
#         return render(request,'whatsapp/interface.html',{
#             'messages':messages,
#             'phone':phone,
#             'user_name':"Name"
            
#         })
    
#     def post(self,request,*args, **kwargs):
#         phone = request.GET.get('phone')
#         message = request.GET.get('message')
#         file = request.GET.get('attachment')

#         if message:
#             request.get(f"https://dynoble.com/app/API/sendtextmessage.php?userphone={phone}&messages={message}")

#         # if file:
#         #     content_type = file.content_type
#         #     files = {'file': (file.name, file.read(), content_type)}
#         #     data = {'userphone': phone}

#         #     if content_type.startswith("image/"):
#         #         media_url = 'https://dynoble.com/app/API/sendmedia.php'  # Replace with your actual endpoint
#         #         requests.post(media_url, files=files, data=data)

#         #     elif content_type.startswith("video/"):
#         #         media_url = 'https://dynoble.com/app/API/sendvideo.php'
#         #         requests.post(media_url, files=files, data=data)

#         #     elif content_type.startswith("audio/"):
#         #         media_url = 'https://dynoble.com/app/API/sendaudio.php'
#         #         requests.post(media_url, files=files, data=data)

#         #     elif content_type in [
#         #         "application/pdf",
#         #         "application/msword",
#         #         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#         #     ]:
#         #         media_url = 'https://dynoble.com/app/API/senddocument.php'
#         #         requests.post(media_url, files=files, data=data)


#         # TODO: handle file (image/video/audio/document) sending    

#         return HttpResponseRedirect(request.path + f"?phone={phone}")
    

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
