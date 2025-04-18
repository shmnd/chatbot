from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
app_name = 'filter'

urlpatterns = [
    path("filters/", views.filter_list_create_view, name="filter_module"),
    path("filters/delete/<int:pk>/", views.delete_filter, name="delete_filter"),
    path("filters/update/<int:pk>/", views.update_filter, name="update_filter"),
]