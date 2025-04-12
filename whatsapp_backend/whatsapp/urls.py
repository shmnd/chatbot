from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'whatsapp'

urlpatterns = [
    path('',login_required(views.WhatsppHomePageView.as_view()),name='interface'),

    path('contacts/',login_required(views.WhatsappContactView.as_view()),name='contacts'),
]   
