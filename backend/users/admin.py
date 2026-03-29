from django.contrib import admin
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'role', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_active', 'is_superuser', 'created_at')
    search_fields = ('email', 'name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        ('Login Credentials', {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'bio', 'profile_picture')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)})
    )
    
    @admin.action(description='✅ Activate selected users')
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='🚫 Block/Deactivate selected users')
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    
    def save_model(self, request, obj, form, change):
        if obj.pk:
            orig_obj = User.objects.get(pk=obj.pk)
            if obj.password != orig_obj.password:
                obj.set_password(obj.password)
        else:
            obj.set_password(obj.password)
        
        # Security: Automate is_staff based on role
        if obj.role in ['admin', 'editor', 'author', 'reporter']:
            obj.is_staff = True
        else:
            obj.is_staff = False
            
        super().save_model(request, obj, form, change)