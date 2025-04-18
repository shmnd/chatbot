from django.db import models

# Create your models here.

class AbstractDateFieldMix(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, editable=False, blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True, editable=False, blank=True, null=True)

    class Meta:
        abstract = True


class WhatsAppMessage(AbstractDateFieldMix):

    msg_id            = models.AutoField(primary_key=True)
    uid               = models.IntegerField(blank=True, null=True)
    id_phone          = models.CharField(max_length=250,blank=True, null=True)
    ournum            = models.CharField(max_length=250,blank=True, null=True)
    usernumber        = models.CharField(max_length=250,blank=True, null=True)
    msg_body          = models.TextField(blank=True, null=True)
    msg_status        = models.IntegerField(blank=True, null=True)
    msg_type          = models.CharField(max_length=250)
    temp_name         = models.CharField(max_length=250)
    array_testing     = models.TextField(blank=True, null=True)
    timestamp         = models.IntegerField(blank=True, null=True)
    mime_type         = models.CharField(max_length=250,blank=True, null=True)
    sha256            = models.CharField(max_length=250,blank=True, null=True)
    local_date_time   = models.CharField(max_length=250,blank=True, null=True)
    filename          = models.CharField(max_length=500,blank=True, null=True)
    send_id           = models.CharField(max_length=500,blank=True, null=True)
    status            = models.IntegerField(blank=True, null=True)
    funnel_id         = models.IntegerField(blank=True, null=True)
    is_read           = models.IntegerField(blank=True, null=True)
    id                = models.IntegerField(blank=True, null=True)  # extra column in your table
    msg_sent_by       = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'whatsapp_messages'  # Let Django create this in local DB
        # managed = False  # Since table already exists
        
class whatsappUsers(AbstractDateFieldMix):
    wa_uid = models.AutoField(primary_key=True)
    phoneid = models.CharField(max_length=250,blank=True, null=True)
    our_num = models.CharField(max_length=250,blank=True, null=True)
    user_name = models.CharField(max_length=250,blank=True, null=True)
    user_num = models.CharField(max_length=250,blank=True, null=True)
    date_time = models.CharField(max_length=250,blank=True, null=True)
    view_order = models.IntegerField(blank=True,null=True)
    agent_id = models.IntegerField(default=0)
    timestamps = models.IntegerField(blank=True,null=True)
    msgstatus = models.IntegerField(default=0)
    lead_status = models.IntegerField(default=1)

    class Meta:
        db_table = 'db_wa_users'
        # managed = False  # Since table already exists
