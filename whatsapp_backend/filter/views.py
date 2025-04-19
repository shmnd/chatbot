from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Filter
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
    print(pk,'delete idddddddddddd')
    filter_obj = get_object_or_404(Filter, pk=pk)
    filter_obj.delete()
    return JsonResponse({"status": "deleted"})

@csrf_exempt
def update_filter(request, pk):
    filter_obj = get_object_or_404(Filter, pk=pk)

    if request.method == "POST":
        name = request.POST.get("filter_name")
        filter_obj.filter_name = name
        filter_obj.save()
        

        filters = Filter.objects.all()
        return render(request, "filter/filter_page.html", {
            "filters": filters
        })


    # For GET request, return current filter name
    return JsonResponse({"filter_name": filter_obj.filter_name})
