"""
users/admin.py — Industry-Level User Management Admin Panel

Features:
  ✅ Role-coloured badges in list view
  ✅ Email verification status indicator
  ✅ Last login + join date tracking
  ✅ Bulk actions: activate, deactivate, change roles, send verification
  ✅ Advanced filters: role, active status, verified email, staff flag, date
  ✅ Author profile inline
  ✅ Read-only security fields
  ✅ Proper password handling
  ✅ Full search across email, name, role
"""

from django.contrib import admin, messages
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from django.conf import settings
from django.template.loader import render_to_string
from core.tasks import send_async_email

from .models import User


# ─── Custom Filters ────────────────────────────────────────────────────────

class RoleFilter(admin.SimpleListFilter):
    title = '🎭 Role'
    parameter_name = 'role_filter'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        role_counts = {
            row['role']: row['c']
            for row in qs.values('role').annotate(c=Count('id'))
        }
        return [
            ('admin',      f'👑 Admin ({role_counts.get("admin", 0)})'),
            ('editor',     f'✏️  Editor ({role_counts.get("editor", 0)})'),
            ('reporter',   f'🎙️  Reporter ({role_counts.get("reporter", 0)})'),
            ('author',     f'📝 Author ({role_counts.get("author", 0)})'),
            ('subscriber', f'👤 Subscriber ({role_counts.get("subscriber", 0)})'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(role=self.value())
        return queryset


class EmailVerifiedFilter(admin.SimpleListFilter):
    title = '✉️ Email Status'
    parameter_name = 'email_verified'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        verified   = qs.filter(is_email_verified=True).count()
        unverified = qs.filter(is_email_verified=False).count()
        return [
            ('verified',   f'✅ Verified ({verified})'),
            ('unverified', f'⏳ Unverified ({unverified})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(is_email_verified=True)
        if self.value() == 'unverified':
            return queryset.filter(is_email_verified=False)
        return queryset


class UserActivityFilter(admin.SimpleListFilter):
    title = '🕐 Activity'
    parameter_name = 'activity'

    def lookups(self, request, model_admin):
        return [
            ('active_today',    '🟢 Active Today'),
            ('active_7days',    '🟡 Active Last 7 Days'),
            ('inactive_30days', '🔴 Inactive 30+ Days'),
            ('never_logged',    '⚫ Never Logged In'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'active_today':
            return queryset.filter(last_login__date=now.date())
        if self.value() == 'active_7days':
            return queryset.filter(last_login__gte=now - timedelta(days=7))
        if self.value() == 'inactive_30days':
            return queryset.filter(
                Q(last_login__lt=now - timedelta(days=30)) | Q(last_login__isnull=True)
            )
        if self.value() == 'never_logged':
            return queryset.filter(last_login__isnull=True)
        return queryset


class StaffFilter(admin.SimpleListFilter):
    title = '🔒 Access Level'
    parameter_name = 'access_level'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        superusers = qs.filter(is_superuser=True).count()
        staff      = qs.filter(is_staff=True, is_superuser=False).count()
        regular    = qs.filter(is_staff=False, is_superuser=False).count()
        return [
            ('superuser', f'⚡ Superuser ({superusers})'),
            ('staff',     f'🔑 Staff ({staff})'),
            ('regular',   f'👤 Regular ({regular})'),
            ('active',    f'✅ Active Only'),
            ('inactive',  f'🚫 Inactive Only'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'superuser':
            return queryset.filter(is_superuser=True)
        if self.value() == 'staff':
            return queryset.filter(is_staff=True, is_superuser=False)
        if self.value() == 'regular':
            return queryset.filter(is_staff=False, is_superuser=False)
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False)
        return queryset


# ─── Inline for Author Profile ─────────────────────────────────────────────

class AuthorProfileInline(admin.StackedInline):
    """Shows author profile inline on user detail page if exists."""
    from news.models import Author
    model = Author
    can_delete    = False
    verbose_name  = "Author Profile"
    extra         = 0
    fields        = ('role', 'twitter_url', 'linkedin_url', 'slug')
    readonly_fields = ('slug',)


# ─── Main User Admin ───────────────────────────────────────────────────────

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):

    # ── List display columns ───────────────────────────────────────────────
    list_display = (
        'email_display', 'name', 'role_badge',
        'email_verified_badge', 'active_badge',
        'staff_badge', 'last_login_display', 'created_at',
    )

    list_display_links = ('email_display', 'name')

    # ── Filters ───────────────────────────────────────────────────────────
    list_filter = (
        RoleFilter,
        StaffFilter,
        EmailVerifiedFilter,
        UserActivityFilter,
        'is_superuser',
    )

    # ── Search ────────────────────────────────────────────────────────────
    search_fields = ('email', 'name', 'role')

    # ── Ordering ──────────────────────────────────────────────────────────
    ordering = ('-created_at',)

    # ── Date hierarchy ────────────────────────────────────────────────────
    date_hierarchy = 'created_at'

    # ── Inlines ───────────────────────────────────────────────────────────
    try:
        inlines = [AuthorProfileInline]
    except Exception:
        inlines = []

    # ── Actions ───────────────────────────────────────────────────────────
    actions = [
        'make_active', 'make_inactive',
        'make_role_editor', 'make_role_reporter', 'make_role_author', 'make_role_subscriber',
        'verify_as_activist',
        'mark_email_verified',
        'grant_staff_access', 'revoke_staff_access',
    ]

    # ── Fieldsets ─────────────────────────────────────────────────────────
    fieldsets = (
        ('🔐 Login Credentials', {
            'fields': ('email', 'password'),
            'description': 'Email is the login username. Use the password widget to change the user password.',
        }),
        ('👤 Personal Information', {
            'fields': ('name', 'bio', 'profile_picture'),
        }),
        ('🎭 Role & Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': (
                'Role determines what the user can do. '
                'Staff access is auto-granted to Admin/Editor/Author/Reporter roles. '
                '<br><strong>Admin/Editor:</strong> Full CMS access. '
                '<strong>Reporter/Author:</strong> Limited to own articles. '
                '<strong>Subscriber:</strong> Frontend only.'
            ),
        }),
        ('✉️ Email Verification', {
            'fields': ('is_email_verified', 'email_verification_token', 'email_verification_token_created_at'),
            'classes': ('collapse',),
            'description': 'Email verification token details. Clear token fields to force re-verification.',
        }),
        ('📅 Account History', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    # ── Read-only fields ──────────────────────────────────────────────────
    readonly_fields = (
        'last_login', 'date_joined',
        'email_verification_token', 'email_verification_token_created_at',
    )

    # ── Custom column: email with superuser crown ──────────────────────────
    @admin.display(description='📧 Email', ordering='email')
    def email_display(self, obj):
        if obj.is_superuser:
            return format_html(
                '{} <span title="Superuser" style="color:#f59e0b;font-size:11px;">⚡</span>',
                obj.email,
            )
        return obj.email

    # ── Custom column: role badge ──────────────────────────────────────────
    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        COLOR_MAP = {
            'admin':      ('👑', '#dc2626', '#7f1d1d'),
            'editor':     ('✏️', '#7c3aed', '#4c1d95'),
            'reporter':   ('🎙️', '#0284c7', '#075985'),
            'author':     ('📝', '#059669', '#064e3b'),
            'subscriber': ('👤', '#374151', '#1f2937'),
        }
        emoji, fg, bg = COLOR_MAP.get(obj.role, ('?', '#6b7280', '#374151'))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;'
            'font-size:10px;font-weight:700;letter-spacing:0.5px;">'
            '{} {}</span>',
            bg, emoji, obj.get_role_display().upper(),
        )

    # ── Custom column: email verified ─────────────────────────────────────
    @admin.display(description='✉️ Email', boolean=False, ordering='is_email_verified')
    def email_verified_badge(self, obj):
        if obj.is_email_verified:
            return format_html(
                '<span style="color:#10b981;font-weight:700;font-size:12px;">✅ Verified</span>'
            )
        return format_html(
            '<span style="color:#f59e0b;font-weight:700;font-size:12px;">⏳ Pending</span>'
        )

    # ── Custom column: active status ──────────────────────────────────────
    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#10b981;font-weight:700;">🟢</span>'
            )
        return format_html(
            '<span style="color:#ef4444;font-weight:700;">🔴</span>'
        )

    # ── Custom column: staff badge ────────────────────────────────────────
    @admin.display(description='Staff', ordering='is_staff')
    def staff_badge(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color:#f59e0b;font-size:12px;" title="Superuser">⚡</span>')
        if obj.is_staff:
            return format_html('<span style="color:#3b82f6;font-size:12px;" title="Staff">🔑</span>')
        return format_html('<span style="color:#4b5563;font-size:12px;">—</span>')

    # ── Custom column: last login ─────────────────────────────────────────
    @admin.display(description='Last Login', ordering='last_login')
    def last_login_display(self, obj):
        if not obj.last_login:
            return format_html(
                '<span style="color:#6b7280;font-size:11px;">Never</span>'
            )
        now = timezone.now()
        diff = now - obj.last_login
        if diff.days == 0:
            return format_html('<span style="color:#10b981;font-size:11px;">Today</span>')
        if diff.days <= 7:
            return format_html(
                '<span style="color:#f59e0b;font-size:11px;">{} days ago</span>', diff.days
            )
        return format_html(
            '<span style="color:#6b7280;font-size:11px;">{} days ago</span>', diff.days
        )

    # ── Save model: password hashing + auto staff ──────────────────────────
    def save_model(self, request, obj, form, change):
        if obj.pk:
            orig = User.objects.get(pk=obj.pk)
            if obj.password != orig.password:
                obj.set_password(obj.password)
        else:
            obj.set_password(obj.password)

        # Auto-manage is_staff based on role
        staff_roles = {'admin', 'editor', 'author', 'reporter'}
        obj.is_staff = obj.role in staff_roles
        super().save_model(request, obj, form, change)

    # ── Queryset: superusers see everyone, staff see non-superusers ────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_superuser=False)

    # ── Readonly: protect superuser fields from non-superusers ────────────
    def get_readonly_fields(self, request, obj=None):
        base = ('last_login', 'date_joined',
                'email_verification_token', 'email_verification_token_created_at')
        if not request.user.is_superuser:
            return base + ('is_superuser', 'user_permissions', 'groups')
        return base

    # ── Bulk Actions ──────────────────────────────────────────────────────

    @admin.action(description='✅ Activate selected users')
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'✅ {count} user(s) activated.')

    @admin.action(description='🚫 Deactivate / Block selected users')
    def make_inactive(self, request, queryset):
        if not request.user.is_superuser:
            protected = queryset.filter(is_superuser=True)
            if protected.exists():
                self.message_user(request, '⛔ Cannot deactivate superusers.', level=messages.ERROR)
                return
        count = queryset.update(is_active=False)
        self.message_user(request, f'🚫 {count} user(s) deactivated.', level=messages.WARNING)

    @admin.action(description='✏️ Change role → Editor')
    def make_role_editor(self, request, queryset):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            self.message_user(request, '⛔ Only Admins can change roles.', level=messages.ERROR)
            return
        count = queryset.update(role='editor', is_staff=True)
        self.message_user(request, f'✏️ {count} user(s) set to Editor.')

    @admin.action(description='🎙️ Change role → Reporter')
    def make_role_reporter(self, request, queryset):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            self.message_user(request, '⛔ Only Admins can change roles.', level=messages.ERROR)
            return
        count = queryset.update(role='reporter', is_staff=True)
        self.message_user(request, f'🎙️ {count} user(s) set to Reporter.')

    @admin.action(description='📝 Change role → Author')
    def make_role_author(self, request, queryset):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            self.message_user(request, '⛔ Only Admins can change roles.', level=messages.ERROR)
            return
        count = queryset.update(role='author', is_staff=True)
        self.message_user(request, f'📝 {count} user(s) set to Author.')

    @admin.action(description='🎓 Verify as Independent Journalism Contributor (+ Email)')
    def verify_as_activist(self, request, queryset):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            self.message_user(request, '⛔ Only Admins can verify activists.', level=messages.ERROR)
            return
        
        from news.models import Author
        count = 0
        for user in queryset:
            user.role = 'author'
            user.is_staff = True
            user.is_email_verified = True
            user.save(update_fields=['role', 'is_staff', 'is_email_verified'])
            
            # Ensure Author profile exists
            Author.objects.get_or_create(
                user=user,
                defaults={'role': 'Independent Journalism Contributor'}
            )
            
            # Send welcome email
            context = {
                'user_name': user.name,
                'frontend_url': settings.FRONTEND_URL
            }
            text_content = render_to_string('emails/activist_welcome.txt', context)
            html_content = render_to_string('emails/activist_welcome.html', context)
            
            send_async_email.delay(
                "Welcome to Ferox Times - Verified Independent Journalism Contributor", 
                text_content, 
                [user.email], 
                html_content
            )
            count += 1
            
        self.message_user(request, f'🎓 {count} user(s) verified as Independent Journalism Contributor and emails sent.')

    @admin.action(description='👤 Change role → Subscriber (revoke staff)')
    def make_role_subscriber(self, request, queryset):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            self.message_user(request, '⛔ Only Admins can change roles.', level=messages.ERROR)
            return
        protected = queryset.filter(is_superuser=True)
        if protected.exists():
            self.message_user(request, '⚠️ Superusers were skipped.', level=messages.WARNING)
            queryset = queryset.filter(is_superuser=False)
        count = queryset.update(role='subscriber', is_staff=False)
        self.message_user(request, f'👤 {count} user(s) downgraded to Subscriber.', level=messages.WARNING)

    @admin.action(description='✉️ Mark email as Verified')
    def mark_email_verified(self, request, queryset):
        count = queryset.update(is_email_verified=True, email_verification_token=None)
        self.message_user(request, f'✉️ {count} user(s) email marked as verified.')

    @admin.action(description='🔑 Grant Staff Access')
    def grant_staff_access(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, '⛔ Only Superusers can grant staff access.', level=messages.ERROR)
            return
        count = queryset.update(is_staff=True)
        self.message_user(request, f'🔑 {count} user(s) granted staff access.')

    @admin.action(description='🔒 Revoke Staff Access')
    def revoke_staff_access(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, '⛔ Only Superusers can revoke staff access.', level=messages.ERROR)
            return
        protected = queryset.filter(is_superuser=True)
        if protected.exists():
            self.message_user(request, '⚠️ Superusers were skipped.', level=messages.WARNING)
            queryset = queryset.filter(is_superuser=False)
        count = queryset.update(is_staff=False)
        self.message_user(request, f'🔒 {count} user(s) staff access revoked.', level=messages.WARNING)

    # ── Dashboard stats banner ─────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        total       = User.objects.count()
        active      = User.objects.filter(is_active=True).count()
        staff       = User.objects.filter(is_staff=True).count()
        unverified  = User.objects.filter(is_email_verified=False, is_active=True).count()
        new_today   = User.objects.filter(created_at__date=timezone.now().date()).count()

        messages.info(
            request,
            f'👥 Total: {total}  |  ✅ Active: {active}  |  🔑 Staff: {staff}  |  '
            f'⏳ Unverified: {unverified}  |  🆕 Joined Today: {new_today}'
        )
        return super().changelist_view(request, extra_context=extra_context)