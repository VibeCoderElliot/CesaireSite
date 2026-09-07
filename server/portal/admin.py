from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, AuditEvent

@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(("Césaire Stages",{'fields':('role','classroom','interests','email_verified')}),)

@admin.register(AuditEvent)
class AuditAdmin(admin.ModelAdmin):
    list_display=('created','actor','action','target')
    readonly_fields=('created','actor','action','target')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
