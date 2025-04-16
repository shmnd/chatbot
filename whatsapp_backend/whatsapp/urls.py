from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'whatsapp'

urlpatterns = [
    path('',login_required(views.WhatsappHomePageView.as_view()),name='interface'),
    path('webhook/', views.WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    path('contacts/',login_required(views.WhatsappContactView.as_view()),name='contacts'),
    path("save-contact/", login_required(views.SaveContactView.as_view()), name="save_contact"),
    path("fetch-messages/", views.FetchMessagesAPI.as_view(), name="fetch_messages"),

]   
