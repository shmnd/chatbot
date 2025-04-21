from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import now, datetime
from whatsapp.models import WhatsAppMessage,whatsappUsers
from filter.models import Filter
from .models import Categories
from django.core.paginator import Paginator
from django.db.models import Max
from django.views.decorators.csrf import csrf_exempt

# Create your views here.


class Homepage(LoginRequiredMixin,View):
    
    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "dashboard/dashboard.html"

    def get(self,request):

        today = now().date()
        
        today_whatsapp_users = WhatsAppMessage.objects.filter(created_date__date = today).values('usernumber').distinct().count()

        total_contact = whatsappUsers.objects.all().distinct().count()

        filter_count = Filter.objects.all().distinct().count

        return render(request,self.template_name,{
            'total_contact':total_contact,
            'today_whatsapp_users':today_whatsapp_users,
            'filter_count':filter_count
        })
    



class ChatFilter(LoginRequiredMixin,View):
    
    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "dashboard/chat_filter.html"

    def get(self,request):

        filters = Filter.objects.all()
        selected_filter = request.GET.get("filter", "")
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        page_number = request.GET.get("page", 1)

        matched_users = []

        if selected_filter:
            messages = WhatsAppMessage.objects.filter(
                msg_body__icontains=selected_filter)  # Case-insensitive match
            
            # Filter by time range

            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end = datetime.strptime(end_date, "%Y-%m-%d").date()
                    messages = messages.filter(created_date__date__range=(start, end))
                except ValueError:
                    pass  # Ignore invalid date formats

            matched_users = messages.values_list("usernumber", "temp_name").distinct()

        paginator = Paginator(matched_users, 15)  # 30 contacts per page
        page_obj = paginator.get_page(page_number)

        return render(request,self.template_name,{
            'filters':filters,
            'selected_filter':selected_filter,
            'start_date': start_date,
            'end_date': end_date,
            'page_obj': page_obj
        })
    

def unread_message_count_api(request):
    # Step 1: Get the latest message ID per user
    latest_messages = WhatsAppMessage.objects.values('usernumber').annotate(last_msg_id=Max('msg_id'))

    # Step 2: Extract the latest message IDs
    latest_ids = [entry['last_msg_id'] for entry in latest_messages]

    # Step 3: Count where latest message is from user (msg_sent_by=0) and not replied (msg_status=0)
    unread_count = WhatsAppMessage.objects.filter(
        msg_id__in=latest_ids,
        msg_status=0,
        msg_sent_by=0
    ).count()

    return JsonResponse({"unresponded_messages": unread_count})


'''---------------------------------------------------------------- CATEGORY ----------------------------------------------------------'''

def category_list_create_view(request):
    if request.method == "POST":
        name = request.POST.get("category_name")
        message = request.POST.get("category_message")
        if name and message:
            Categories.objects.create(name=name,messages=message)
        return redirect("home:category_module")  # name of your url

    categories = Categories.objects.all()
    return render(request, "dashboard/category.html", {"categories": categories})


def delete_category(request, pk):
    category_obj = get_object_or_404(Categories, pk=pk)
    category_obj.delete()
    
    categorys = Categories.objects.all()
    return render(request, "dashboard/category.html", {
        "categorys": categorys
    })


@csrf_exempt
def update_category(request, pk):
    category_obj = get_object_or_404(Categories, pk=pk)

    if request.method == "POST":
        name = request.POST.get("category_name")
        message = request.POST.get("category_message")

        category_obj.name = name 
        category_obj.messages = message 
        category_obj.save()
        

        categories = Categories.objects.all()
        return render(request, "dashboard/category.html", {
            "categories": categories
        })


    # For GET request, return current filter name
    return JsonResponse({
        "name": category_obj.name,
        "messages": category_obj.messages
    })
