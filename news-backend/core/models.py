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