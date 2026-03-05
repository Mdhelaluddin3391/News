from django.contrib import admin
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    # Admin panel mein kaun-kaun se columns dikhane hain
    list_display = ('email', 'name', 'is_staff', 'is_active', 'created_at')
    
    # Search box kin fields par kaam karega
    search_fields = ('email', 'name')
    
    # Sorting (ordering) email ke basis par hogi, na ki username par
    ordering = ('email',)
    
    # Admin panel mein user edit karte waqt fields kaise dikhenge
    fieldsets = (
        ('Login Info', {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'bio', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )