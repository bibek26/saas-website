from django.contrib import admin
from .models import Tenant,Subscription, CustomUser, Notification
# Register your models here.
admin.site.register(Tenant)
admin.site.register(Subscription)
admin.site.register(CustomUser)
admin.site.register(Notification)