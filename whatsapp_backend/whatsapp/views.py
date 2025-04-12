from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from whatsapp.service.whatsapp_api import fetch_contact
from django.core.paginator import Paginator
import requests

# Create your views here.
class WhatsppHomePageView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'whatsapp/interface.html')
    

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
