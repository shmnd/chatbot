from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
class WhatsppHomePageView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'whatsapp/interface.html')