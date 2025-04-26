from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import now, datetime
from whatsapp.models import WhatsAppMessage,whatsappUsers,WhatsAppTemplate
from filter.models import Filter
from .models import Categories,Lead
from django.core.paginator import Paginator
from django.db.models import Max
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import Lower, Trim
from django.db.models import Q
# Create your views here.


class Homepage(LoginRequiredMixin,View):
    
    def __init__(self):
        self.response_format = {'status_code':101,'message':'','error':''}

    template_name = "dashboard/dashboard.html"

    def get(self,request):

        today = now().date()
        
        today_whatsapp_users = WhatsAppMessage.objects.filter(
            created_date__date=today
        ).values("usernumber").distinct().count()

        total_contact = whatsappUsers.objects.all().distinct().count()
        filter_count = Filter.objects.all().distinct().count()

        categories = Categories.objects.all()
        leads = Lead.objects.all()

        for category in categories:

            message = (category.messages or "").strip().lower()

            qs = WhatsAppMessage.objects.annotate(
                cleaned_body=Lower(Trim('msg_body'))
            ).filter(cleaned_body__icontains=message)

            category.total_request = qs.values("usernumber").distinct().count()
            category.unreaded_request = qs.filter(is_read=False).count()

            # print(f"[{category.name}] Total: {category.total_request}, Unread: {category.unreaded_request}")

        for lead in leads:
            lead.total_count = whatsappUsers.objects.filter(
                lead_status_id=lead.id
            ).count()

        return render(request,self.template_name,{
            'total_contact':total_contact,
            'today_whatsapp_users':today_whatsapp_users,
            'filter_count':filter_count,
            'categories':categories,
            'leads':leads,
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
        template_ids = request.POST.getlist("templates")

        if name and message:
            category = Categories.objects.create(name=name, messages=message)
            
            # Assign selected templates to this category
            WhatsAppTemplate.objects.filter(id__in=template_ids).update(category=category)

        return redirect("home:category_module")

    categories = Categories.objects.all()

    for category in categories:
        category.template_ids = ",".join(map(str, category.templates.values_list('id', flat=True)))

    templates = WhatsAppTemplate.objects.filter(category__isnull=True) # only unassigned templates
    
    return render(request, "dashboard/category.html", {"categories": categories,"templates": templates})


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
        template_ids = request.POST.getlist("templates")

        category_obj.name = name 
        category_obj.messages = message 
        category_obj.save()
        
        # Unassign templates from this category first
        WhatsAppTemplate.objects.filter(category=category_obj).update(category=None)

        # Re-assign selected ones
        WhatsAppTemplate.objects.filter(id__in=template_ids).update(category=category_obj)

        categories = Categories.objects.all()

        for category in categories:
            category.template_ids = ",".join(map(str, category.templates.values_list('id', flat=True))) 

        # ✅ Fetch templates assigned to this category OR unassigned
        templates = WhatsAppTemplate.objects.filter(category__isnull=True)
        return render(request, "dashboard/category.html", {
            "categories": categories,
            'templates': templates
        })


    # For GET request, return current filter name
    return JsonResponse({
        "name": category_obj.name,
        "messages": category_obj.messages
    })



def category_users_view(request, category_id):
    category = get_object_or_404(Categories, id=category_id)

    # Find users who sent a message matching the category message
    matching_messages = WhatsAppMessage.objects.filter(msg_body__icontains=category.messages)

    # Extract unique phone numbers from matching messages
    phone_numbers = matching_messages.values_list('usernumber', flat=True).distinct()

    # Get user records for those phone numbers
    users_queryset  = whatsappUsers.objects.filter(user_num__in=phone_numbers)

    # Add pagination
    paginator = Paginator(users_queryset, 10)  # Show 10 users per page
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    return render(request, "dashboard/category_users.html", {
        "category": category,
        "users": users
    })


'''---------------------------------------------------------------- Lead ----------------------------------------------------------'''

def lead_list_create_view(request):
    if request.method == "POST":
        name = request.POST.get("lead_name")
        if name:
            Lead.objects.create(lead_name=name)
        return redirect("home:lead_module")  # name of your url

    leads = Lead.objects.all()
    return render(request, "dashboard/lead.html", {"leads": leads})


def delete_lead(request, pk):
    lead_obj = get_object_or_404(Lead, pk=pk)
    lead_obj.delete()
    
    leads = Lead.objects.all()
    return render(request, "dashboard/head.html", {
        "leads":leads
    })

@csrf_exempt
def update_lead(request, pk):
    lead_obj = get_object_or_404(Lead, pk=pk)

    if request.method == "POST":
        name = request.POST.get("lead_name")
        lead_obj.lead_name = name 
        lead_obj.save()
        leads = Lead.objects.all()
        return render(request, "dashboard/lead.html", {
            "leads":leads
        })

    # For GET request, return current filter name
    return JsonResponse({
        "name": lead_obj.lead_name,
    })


def lead_users_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)

    # Find users who sent a message matching the category message
    matching_leads = whatsappUsers.objects.filter(lead_status_id=lead.id)

    # Extract unique phone numbers from matching messages
    phone_numbers = matching_leads.values_list('user_num', flat=True).distinct()

    # Get user records for those phone numbers
    users_queryset  = whatsappUsers.objects.filter(user_num__in=phone_numbers)

    # Add pagination
    paginator = Paginator(users_queryset, 10)  # Show 10 users per page
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    return render(request, "dashboard/lead_users.html", {
        "lead": lead,
        "users": users
    })