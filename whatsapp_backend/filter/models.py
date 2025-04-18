from django.db import models


class AbstractDateFieldMix(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, editable=False, blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True, editable=False, blank=True, null=True)

    class Meta:
        abstract = True

# Create your models here.
class Filter(AbstractDateFieldMix):
    filter_name = models.CharField(max_length=255)

    def __str__(self):
        return self.filter_name