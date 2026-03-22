# news-backend/news/tasks.py

import os
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Article

@shared_task
def process_article_image(article_id):
    """
    Yeh Celery task background mein run hoga. Article ki image ko 
    resize karke WebP format mein compress karega bina website ko slow kiye.
    """
    try:
        article = Article.objects.get(id=article_id)
        
        # Agar image nahi hai, ya pehle se WebP hai toh kuch mat karo
        if not article.featured_image or article.featured_image.name.lower().endswith('.webp'):
            return f"Skipped processing for Article {article_id}"

        # Image ko file system se open karein
        img = Image.open(article.featured_image.path)

        # PNG (RGBA) ko RGB mein convert karein taaki WebP support kare
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize karein (Max width 1200px)
        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)

        # Memory buffer mein WebP format mein save karein
        output = BytesIO()
        img.save(output, format='WEBP', quality=80)
        output.seek(0)

        # Original file ka path note karein taaki baad mein delete kar sakein
        original_path = article.featured_image.path
        
        # Naya file name banayein (.webp extension ke sath)
        base_name = os.path.basename(article.featured_image.name)
        file_name = os.path.splitext(base_name)[0] + '.webp'

        # Nayi compressed file save karein (save=False taaki abhi database save na ho)
        article.featured_image.save(file_name, ContentFile(output.read()), save=False)
        
        # Sirf featured_image field update karein DB mein
        article.save(update_fields=['featured_image'])

        # Storage free karne ke liye puraani (badi) image ko delete kar dein
        if os.path.exists(original_path) and original_path != article.featured_image.path:
            os.remove(original_path)

        return f"✅ Image compressed to WebP for Article ID: {article_id}"

    except Article.DoesNotExist:
        return f"❌ Article {article_id} not found."
    except Exception as e:
        return f"❌ Image processing error for Article {article_id}: {str(e)}"