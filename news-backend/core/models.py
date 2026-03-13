from django.db import models
from tinymce.models import HTMLField


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

    def __str__(self):
        return f"{self.title} - {self.get_slot_display()} ({self.ad_type})"
    
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