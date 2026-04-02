from django.db import models


class BaseModel(models.Model):
    """
    Industry standard: Ek abstract base class jisme sabhi tables ke liye 
    created_at aur updated_at fields automatically handle honge.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False, help_text="Mark if this query has been handled.")

    class Meta:
        indexes = [
            models.Index(fields=['is_resolved', '-created_at'], name='core_contact_resolved_idx'),
        ]

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
    


class Advertisement(models.Model):
    SLOT_CHOICES = (
        ('header', 'Header Banner'),
        ('sidebar', 'Sidebar Top'),
        ('in_article', 'In-Article (Article ke beech mein)'), # Ek aur ad placement!
    )
    
    TYPE_CHOICES = (
        ('brand', 'Brand Collab (Image + Link)'),
        ('google', 'Google AdSense (Script)'),
    )
    is_mobile_only = models.BooleanField(default=False) 
    priority = models.IntegerField(default=1)
    title = models.CharField(max_length=150, help_text="Internal reference ke liye naam")
    slot = models.CharField(max_length=20, choices=SLOT_CHOICES)
    ad_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # === Brand Ads Ke Liye ===
    image = models.ImageField(upload_to='ads/', blank=True, null=True, help_text="Brand ad image upload karein")
    url = models.URLField(blank=True, null=True, help_text="Brand ki website ka link")
    
    # === Google Ads Ke Liye ===
    google_ad_code = models.TextField(blank=True, null=True, help_text="Google Adsense ka HTML snippet yahan paste karein")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['slot', 'is_active', '-priority', '-created_at'], name='core_ad_slot_active_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_slot_display()} ({self.ad_type})"


class AdvertisePage(models.Model):
    hero_title = models.CharField(
        max_length=200,
        default="Grow Your Brand With Ferox Times",
    )
    hero_description = models.TextField(
        default=(
            "Reach a highly engaged audience through our premium digital news "
            "platform. We offer strategic ad placements to maximize your visibility."
        ),
    )
    slots_section_title = models.CharField(
        max_length=200,
        default="Available Ad Slots",
    )
    inquiry_title = models.CharField(
        max_length=200,
        default="Advertisement Inquiry",
    )
    inquiry_description = models.TextField(
        default=(
            "Fill out the form below and our advertising team will get back to you "
            "with pricing and analytics details."
        ),
    )
    submit_button_text = models.CharField(
        max_length=80,
        default="Submit Inquiry",
    )
    success_message = models.CharField(
        max_length=255,
        default="Thank you for your interest! Our advertising team will contact you shortly.",
    )

    class Meta:
        verbose_name = "Advertise Page"
        verbose_name_plural = "Advertise Page"

    def __str__(self):
        return "Advertise With Us Page"


class AdvertiseOption(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon_class = models.CharField(
        max_length=100,
        default="fas fa-bullhorn",
        help_text="Font Awesome class, e.g. fas fa-rectangle-ad",
    )
    inquiry_value = models.CharField(
        max_length=150,
        help_text="Dropdown me yahi option value use hogi.",
    )
    sort_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    show_on_page = models.BooleanField(
        default=True,
        help_text="Enable ho to advertise page ke cards me dikhega.",
    )
    show_in_inquiry_form = models.BooleanField(
        default=True,
        help_text="Enable ho to inquiry dropdown me dikhega.",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Advertise Option"
        verbose_name_plural = "Advertise Options"

    def __str__(self):
        return self.title


class SiteSetting(models.Model):
    ga4_tracking_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Google Analytics 4 Measurement ID (e.g., G-XXXXXXXXXX) yahan daalein."
    )

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Global Site Settings"
    


class JobPosting(BaseModel):
    EMPLOYMENT_TYPES = (
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    )
    title = models.CharField(max_length=200, help_text="Job ka title (e.g., Senior Reporter)")
    location = models.CharField(max_length=150, help_text="e.g., Remote, City Name (Hybrid)")
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES)
    description = models.TextField(help_text="Short description of the role")
    is_active = models.BooleanField(default=True, help_text="Uncheck karein agar ye job ab available nahi hai")

    class Meta:
        indexes = [
            models.Index(fields=['is_active', '-created_at'], name='core_job_active_idx'),
        ]

    def __str__(self):
        return self.title
