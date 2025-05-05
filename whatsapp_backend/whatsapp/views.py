# Standard library imports
import requests

import os
import json
import mimetypes
import tempfile
from datetime import datetime

# Third-party imports
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
from whatsapp.models import whatsappUsers, WhatsAppMessage,WhatsAppTemplate
from whatsapp.service.whatsapp_api import fetch_contact
from whatsapp.helpers.utils import extract_file_url_from_msg_body,handle_new_message,SendMessageWebhookView,sync_templates_from_meta,guess_header_type
from dashboard.models import Lead,Categories
from django.db.models import OuterRef, Subquery, Max, F, Q, Case, When
# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
            # print(data,'datassssssssssssssss')
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts")
                    our_number = settings.WHATSAPP_NUMBER

                    contact_name = None
                    if contacts:
                        contact_name = contacts[0].get("profile", {}).get("name")

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

                            try:
                                requests.post(...)  # OK here
                            except:
                                pass

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
        search = request.GET.get("phone", "").strip()
        messages = []
        user_exists = False
        user_name = search
        phone = ""  # Will be set only if there's an exact number match
        leads = Lead.objects.all()
        selected_user = None

        # Fetch filtered chat users based on name or number
        if search:
            chat_users = whatsappUsers.objects.filter(
                Q(user_num__icontains=search) | Q(user_name__icontains=search)
            )

            # If the search string exactly matches a number, treat it as a chat open request
            exact_match_user = whatsappUsers.objects.filter(user_num=search).first()
            if exact_match_user:
                phone = search
                selected_user = exact_match_user
                user_exists = True
                user_name = exact_match_user.user_name or phone

                # Reset unread message indicator
                exact_match_user.msgstatus = 0
                exact_match_user.save()

        else:
            chat_users = whatsappUsers.objects.all()

        # Get messages if phone is identified
        if phone:
            # Prefetch user data for all messages at once
            messages_qs = WhatsAppMessage.objects.filter(Q(usernumber=phone) | Q(id_phone=phone)).order_by("msg_id")

            # Get all unique user numbers from the messages
            user_numbers = set(messages_qs.values_list('usernumber', flat=True))

            # Create a dictionary mapping user numbers to their lead status
            user_lead_map = {}
            for user in whatsappUsers.objects.filter(user_num__in = user_numbers).select_related('lead_status'):
                lead_name = user.lead_status.lead_name if  user.lead_status else "None"
                user_lead_map[user.user_num] = lead_name

            # Process messages using the pre-fetched data
            for m in messages_qs:
                soup = BeautifulSoup(m.msg_body or "", "html.parser")
                clean_body = soup.text.split("Time:")[0].strip()
                timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

                # Use the mapping instead of querying for each message
                lead_name = user_lead_map.get(m.usernumber,"None")


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
                    "lead_name": lead_name
                })


        lastest_message_subquery = WhatsAppMessage.objects.filter(
            usernumber = OuterRef('user_num')
        ).order_by('-msg_id').values('created_date')[:1]

        chat_users = chat_users.annotate(
            latest_activity=Case(
                When(
                    user_num__in=WhatsAppMessage.objects.values('usernumber').distinct(),
                    then = Subquery(lastest_message_subquery)
                ),
                default=F('created_date')
            )
        ).order_by('-latest_activity')

        return render(request, "whatsapp/interface.html", {
            "messages": messages,
            "user_phone": phone,
            "user_name": user_name,
            "user_exists": user_exists,
            "chat_users": chat_users,
            "leads":leads,
            "user": selected_user, 
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

                    try:
                        requests.post(...)  # OK here
                    except:
                        pass

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

                    try:
                        requests.post(...)  # OK here
                    except:
                        pass

                    send_res = requests.post(WA_URL, json=wa_payload, headers=WA_HEADERS)
                    # print("SEND STATUS:", send_res.status_code)
                    # print("SEND RESPONSE:", send_res.text)

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

                    msg =WhatsAppMessage.objects.create(
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

                    # Forward to PHP API
                    payload = {
                        "usernumber": msg.usernumber,
                        "msg_body": msg.msg_body,
                        "msg_type": msg.msg_type,
                        "msg_status": msg.msg_status,
                        "timestamp": msg.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "filename": msg.filename,
                        "mime_type": msg.mime_type,
                        "file_url": extract_file_url_from_msg_body(msg.msg_body),
                        "sent_by": msg.msg_sent_by,
                    }
                    #  api to give seniior to my my msg paste senior given api here 
                    try:
                        requests.post("https://example.com/api/save_message.php", json=payload)
                    except:
                        pass

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

                #  api to give seniior to my my msg paste senior given api here 
                try:
                    requests.post("https://example.com/api/save_message.php", json=msg_body)
                except:
                    pass

                send_res = requests.post(WA_URL,headers=WA_HEADERS,json=wa_payload)
                # print("TEXT SEND STATUS:", send_res.status_code)
                # print("TEXT SEND RESPONSE:", send_res.text)

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

                # ✅ Mark previous unread messages from this user as read
                WhatsAppMessage.objects.filter(usernumber=phone, is_read=False).update(is_read=True)

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

        # Create a subquery to get the latest message date for each user
        lastest_message_dates = WhatsAppMessage.objects.filter(
            usernumber = OuterRef('user_num')
        ).order_by('-created_date').values('created_date')[:1]

        # Create a subquery to get the latest message body for each user
        latest_message_body_subquery = WhatsAppMessage.objects.filter(
            usernumber=OuterRef('user_num')
        ).order_by('-msg_id').values('msg_body')[:1]
        
        # Annotate users with their latest message date, falling back to user creation date
        users = whatsappUsers.objects.annotate(
            latest_activity = Case(
                When(
                    user_num__in = WhatsAppMessage.objects.values('usernumber').distinct(),
                    then=Subquery(lastest_message_dates)
                ),
                default=F('created_date')
            ),
            last_message_body=Subquery(latest_message_body_subquery)

        ).order_by('-latest_activity')


        # users = sorted(
        #     whatsappUsers.objects.all(),
        #     key=lambda user: WhatsAppMessage.objects.filter(usernumber=user.user_num).order_by("-msg_id").first().created_date
        #     if WhatsAppMessage.objects.filter(usernumber=user.user_num).exists() else user.created_date,
        #     reverse=True
        # )

        user_data = []
        for user in users:
            # last_msg = WhatsAppMessage.objects.filter(usernumber=user.user_num).order_by("-msg_id").first()
            last_message = ""
            if user.last_message_body:
                soup = BeautifulSoup(user.last_message_body or "", "html.parser")
                last_message = soup.text.strip()

            user_data.append({
                "user_num": user.user_num,
                "user_name": user.user_name or "Unnamed User",
                "msgstatus": user.msgstatus,
                "last_message": last_message,
            })

        return JsonResponse({"users": user_data})
    

def update_lead_status(request):
    if request.method == "POST":
        phone = request.POST.get("user_phone")
        lead_id = request.POST.get("lead_status")

        try:
            user = whatsappUsers.objects.get(user_num=phone)
        except whatsappUsers.DoesNotExist:
            return redirect(request.META.get('HTTP_REFERER', '/'))  # No user? redirect back

        try:
            if lead_id:
                lead_instance = Lead.objects.get(id=lead_id)
                user.lead_status = lead_instance
            else:
                user.lead_status = None
            user.save()
        except Lead.DoesNotExist:
            pass  # Invalid lead_id? silently skip or handle if needed

        return redirect(request.META.get('HTTP_REFERER', '/'))
    
# ----------------------------------------------------------------- TEMPLATE CHAT -----------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class FetchCategoriesView(View):
    def get(self, request):
        try:
            categories = Categories.objects.all()
            data = [{"id": c.id, "name": c.name} for c in categories]
            return JsonResponse({"categories": data})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class FetchTemplatesByCategoryView(View):
    def get(self, request, category_id):
        try:
            sync_templates_from_meta()
            templates = WhatsAppTemplate.objects.filter(category_id=category_id,template_status="APPROVED")
            data = [{"id": t.id, "name": t.template_name} for t in templates]  # template_name should match Meta name
            return JsonResponse({"templates": data})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class GetTemplatePreview(View):
    def get(self, request, template_id):
        try:
            template = WhatsAppTemplate.objects.get(id=template_id)

            # Load structured JSON data from the description field if you're saving it as JSON
            try:
                components = json.loads(template.description).get("components", [])
            except (json.JSONDecodeError, TypeError, AttributeError):
                components = []

            image_url = None
            body_text = ""
            for comp in components:
                if comp.get("type") == "HEADER" and comp.get("format") == "IMAGE":
                    header_example = comp.get("example", {}).get("header_handle", [])
                    if header_example:
                        image_url = header_example[0]
                if comp.get("type") == "BODY":
                    body_text = comp.get("text", "")

            return JsonResponse({
                "template_name": template.template_name,
                "has_media": bool(image_url),
                "media_type": "image" if image_url else "",
                "media_url": image_url,
                "description": body_text or "No message available"
            })

        except WhatsAppTemplate.DoesNotExist:
            return JsonResponse({"error": "Template not found."}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class SendWhatsAppTemplateView(View):

    def get(self, request):
        try:
            categories = Categories.objects.all()
            url = f'https://graph.facebook.com/v18.0/{settings.WHATSAPP_BUSINESS_ID}/message_templates'

            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url,headers=headers)

            if response.status_code == 200:
                templates = response.json().get('data',[])
            else:
                templates = []    
                # print("❌ Error fetching templates:", response.text)

            return render(request,'whatsapp/interface.html',{
                'categories':categories,
                'templates':templates
            })
                    
        except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

    def post(self, request):
        try:
            data = request.POST
            files = request.FILES
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            template_name = data.get("template") or data.get("template_id") 
            numbers = data.get("numbers", "").split(",")
            variables = json.loads(data.get("variables", "[]")) 

            if not template_name or not numbers:
                return JsonResponse({"error": "Missing template or numbers"}, status=400)

            media = files.get("media")
            media_id = None
            mime_type = None
            real_header_type = None
            header_type = None

            template_obj = WhatsAppTemplate.objects.filter(template_name=template_name).first()

            if not template_obj:
                return JsonResponse({"error": "Template not found."}, status=404)
            
            expected_header_type = getattr(template_obj, "header_type", None)  # Safe access from DB

            # 1. Determine MIME and real header type if media is uploaded
            if media:
                mime_type = media.content_type

                if not mime_type:
                    mime_type, _ = mimetypes.guess_type(media.name)

                    
                real_header_type = guess_header_type(mime_type)

                # print("🧾 DEBUG: --- Incoming Media Info ---")
                # print("📎 File Name:", media.name)
                # print("🧪 MIME Type:", mime_type)
                # print("📦 Guessed Header Type:", real_header_type)
                # print("📄 Template Expects:", expected_header_type)
                # print("📍 Final Header Type Used:", header_type)
                # print("📤 Uploading to Meta from path:", local_path if 'local_path' in locals() else "Not saved yet")


                # Validate header type matches actual uploaded type
                if expected_header_type and expected_header_type != real_header_type:
                    return JsonResponse({
                        "error": f"Template expects a {expected_header_type.upper()}, but uploaded file is a {real_header_type.upper()}."
                    }, status=400)
                    
                header_type = real_header_type
            else:
                header_type = expected_header_type # fallback to template value if no media uploaded

            if media and template_obj:
                # Save media locally
                extension = mimetypes.guess_extension(mime_type) or ''
                local_filename = f"{template_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{extension}"

                upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                local_path = os.path.join(upload_dir, local_filename)

                with open(local_path, 'wb') as f:
                    f.write(media.read())

                # Upload to Meta
                with open(local_path, 'rb') as f:
                    upload_response = requests.post(
                        f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/media",
                        headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                        files={"file": (local_filename, f, mime_type)},
                        data={"messaging_product": "whatsapp"}
                    )

                if upload_response.status_code == 200:
                    media_id = upload_response.json().get("id")
                    # Save info to template
                    template_obj.media_url = media_id  
                    template_obj.has_media = True
                    template_obj.header_type = header_type
                    template_obj.media_type = header_type
                    template_obj.save()
                else:
                    return JsonResponse({"error": "Failed to upload media to Meta."}, status=500)
            
                # print("🧾 Meta upload response:", upload_response.status_code, upload_response.text)


            # If no new media, use stored image from template (if exists)
            elif template_obj and template_obj.has_media:
                media_id = template_obj.media_url  # This must be an actual media ID
                header_type = getattr(template_obj, "header_type", None)

            # 2. Send to all numbers
            success, failed = [], []
            for number in numbers:
                number = number.strip()

                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": number,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "en"},
                        "components": []
                    }
                }

                # Attach header media
                if media_id and header_type in ["image", "video", "document"]:
                    if header_type == "document":
                        header_component = {
                            "type": "header",
                            "parameters": [{
                                "type": "document",
                                "document": {
                                    "id": media_id,
                                    "filename": local_filename  # required for document type
                                }
                            }]
                        }
                    else:
                        header_component = {
                            "type": "header",
                            "parameters": [{
                                "type": header_type,
                                header_type: {
                                    "id": media_id
                                }
                            }]
                        }

                    payload["template"]["components"].append(header_component)

                # Add variables
                if variables:
                    body_component = {
                        "type": "body",
                        "parameters": [{"type": "text", "text": str(var)} for var in variables]
                    }
                    payload["template"]["components"].append(body_component)


                # Send the message
                response = requests.post(
                    f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages",
                    headers = {
                        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                # print("📬 WhatsApp Send Payload:", json.dumps(payload, indent=2))
                # print("📬 WhatsApp Response:", response.status_code, response.text)


                if response.status_code == 200:
                    success.append(number)
                    WhatsAppMessage.objects.create(
                        usernumber=number,
                        id_phone=settings.WHATSAPP_NUMBER,
                        temp_name=f"Template name: {template_name}",
                        msg_body=f"Template body: {template_name}",
                        msg_status=1,
                        msg_type="template",
                        mime_type=mime_type if media else "",
                        status=1,
                        local_date_time=timestamp,
                        created_date=now(),
                        modified_date=now(),
                        msg_sent_by="1",
                    )
                else:
                    failed.append({"number": number, "error": response.text})
                    # print(f"❌ Failed to send to {number}:", response.text)

            return JsonResponse({
                "success": success,
                "failed": failed,
                "message": f"Sent to {len(success)} numbers, failed for {len(failed)}."
            }, status=200)

        except Exception as e:
            # print('nooooooooooooo❌ Exception:', str(e))
            return JsonResponse({"error": str(e)}, status=500)
        

@csrf_exempt
def get_sent_messages(request):

    token = request.GET.get('token')
    if token != settings.WHATSAPP_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        # Filter only messages sent by you
        messages = WhatsAppMessage.objects.filter(
            msg_sent_by=1,      # Replace with your user ID or make dynamic
        ).order_by('-created_date')[:100]

        data = []
        for msg in messages:
            data.append({
                'msg_id': msg.msg_id,
                'id_phone': msg.id_phone,
                'ournum': msg.ournum,
                'usernumber': msg.usernumber,
                'msg_body': msg.msg_body,
                'msg_status': msg.msg_status,
                'msg_type': msg.msg_type,
                'array_testing': msg.array_testing,
                'timestamp': msg.timestamp,
                'mime_type': msg.mime_type,
                'sha256': msg.sha256,
                'local_date_time': msg.local_date_time,
                'filename': msg.filename,
                'send_id': msg.send_id,
                'status': msg.status,
                'funnel_id': msg.funnel_id,
                'is_read': msg.is_read
            })
            print(data,'dataaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        return JsonResponse({'messages': data}, safe=False)

    return JsonResponse({'error': 'Only GET method allowed'}, status=405)
