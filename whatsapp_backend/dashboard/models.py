from django.db import models
# Create your models here.

class AbstractDateFieldMix(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, editable=False, blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True, editable=False, blank=True, null=True)
    class Meta:
        abstract = True

class Categories(AbstractDateFieldMix):
    name = models.CharField(max_length=225,blank=True,null=True,default="Fresh lead")
    messages =  models.TextField(blank=True,null=True)
    total_request = models.IntegerField(default=0,blank=True,null=True)
    unreaded_request = models.IntegerField(default=0,blank=True,null=True)

    def __str__(self):
        return self.name
    
class Lead(AbstractDateFieldMix):
    lead_name = models.CharField(max_length=255,blank=True,null=True)

    def __str__(self):
        return self.lead_name