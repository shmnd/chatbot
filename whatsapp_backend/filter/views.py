from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Filter
# Create your views here.


def filter_list_create_view(request):
    if request.method == "POST":
        name = request.POST.get("filter_name")
        if name:
            Filter.objects.create(filter_name=name)
        return redirect("filter:filter_module")  # name of your url

    filters = Filter.objects.all()
    return render(request, "filter/filter_page.html", {"filters": filters})

def delete_filter(request, pk):
    print(pk,'idddddddddddd')
    filter_obj = get_object_or_404(Filter, pk=pk)
    filter_obj.delete()
    return JsonResponse({"status": "deleted"})

def update_filter(request, pk):
    filter_obj = get_object_or_404(Filter, pk=pk)
    if request.method == "POST":
        name = request.POST.get("filter_name")
        filter_obj.filter_name = name
        filter_obj.save()
        return JsonResponse({"status": "updated"})
    return JsonResponse({"filter_name": filter_obj.filter_name})
