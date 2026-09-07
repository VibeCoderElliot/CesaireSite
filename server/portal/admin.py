from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Internship, Claim, Application, AuditEvent

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

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display=('name','sector','status','owner','is_demo')
    list_filter=('status','is_demo','sector')
    search_fields=('name','address')

@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display=('title','organization','start','end','status','is_demo')
    list_filter=('status','is_demo')

admin.site.register(Claim)
admin.site.register(Application)
