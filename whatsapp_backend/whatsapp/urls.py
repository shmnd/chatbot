from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'whatsapp'

urlpatterns = [
    path('',login_required(views.WhatsappHomePageView.as_view()),name='interface'),
    path('contacts/',login_required(views.WhatsappContactView.as_view()),name='contacts'),
    path("save-contact/", login_required(views.SaveContactView.as_view()), name="save_contact"),
    # path('chats/',login_required(views.whatsappChatView.as_view()),name='chats'),
]   
