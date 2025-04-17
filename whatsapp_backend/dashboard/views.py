from django.shortcuts import render,HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from whatsapp.models import WhatsAppMessage
from django.utils.timezone import now
from django.db.models import Count
from whatsapp.models import WhatsAppMessage,whatsappUsers
# Create your views here.


class Homepage(LoginRequiredMixin,View):
    
    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "dashboard/dashboard.html"

    def get(self,request):

        today = now().date()
        
        today_whatsapp_users = WhatsAppMessage.objects.filter(created_date__date = today).values('usernumber').distinct().count()

        total_contact = whatsappUsers.objects.all().distinct().count()

        return render(request,self.template_name,{
            'total_contact':total_contact,
            'today_whatsapp_users':today_whatsapp_users
        })