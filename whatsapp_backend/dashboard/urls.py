from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'home'

urlpatterns = [
    path('',login_required(views.Homepage.as_view()),name='dashboard'),
    path('chat_filter',login_required(views.ChatFilter.as_view()),name='chat_filter'),
    path('unread-count/', login_required(views.unread_message_count_api), name='dashboard_unread_count'),

    # catergory 
    path("category/", views.category_list_create_view, name="category_module"),
    path("category/delete/<int:pk>/", views.delete_category, name="delete_category"),
    path("category/update/<int:pk>/", views.update_category, name="update_category"),
    path('category/<int:category_id>/users/', views.category_users_view, name='category_users'),


]   
