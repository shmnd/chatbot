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
    path("fetch_users/", views.FetchChatUsersView.as_view(), name="fetch_users"),
    path('update-lead-status/', views.update_lead_status, name='update_lead_status'),
    # api to fetch sended message 
    path('api/get-sent-messages/', views.get_sent_messages, name='get_sent_messages'),

    # Template message
    path('message_categories/', views.FetchCategoriesView.as_view(), name='get_all_categories'),
    path('template_message_category/<int:category_id>/', views.FetchTemplatesByCategoryView.as_view(), name='get_templates_by_category'),
    path('template_preview/<int:template_id>/', views.GetTemplatePreview.as_view(), name='template_preview'),
    path('send_template_message/',views.SendWhatsAppTemplateView.as_view(),name='send_template_message'),

]
