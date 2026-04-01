import requests
import uuid
from django.core.files.base import ContentFile
from django.utils.html import strip_tags
from news.models import Article

def clean_text(text, max_length=None):
    """HTML tags remove karta hai aur text ko clean karta hai."""
    if not text:
        return ""
    cleaned = strip_tags(text).strip()
    if max_length and len(cleaned) > max_length:
        return cleaned[:max_length] + "..."
    return cleaned

def fetch_and_import_news(api_url, provider):
    """
    API se news fetch karke Draft articles banata hai.
    provider: 'gnews' ya 'newsdata'
    """
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # API ke hisaab se articles ki list nikalein
        if provider == 'gnews':
            articles_data = data.get('articles', [])[:10]
        elif provider == 'newsdata':
            articles_data = data.get('results', [])[:10]
        else:
            return "Invalid provider specified."
            
        imported_count = 0
        
        for item in articles_data:
            # 1. MAPPING (Dono APIs ke alag keys hote hain)
            if provider == 'gnews':
                title = item.get('title', '').strip()
                source_url = item.get('url', '')
                raw_desc = item.get('description', '')
                raw_content = item.get('content', '')
                image_url = item.get('image', '')
                source_name = item.get('source', {}).get('name', 'GNews')
            
            elif provider == 'newsdata':
                title = item.get('title', '').strip()
                source_url = item.get('link', '')
                raw_desc = item.get('description', '')
                raw_content = item.get('content', '')
                image_url = item.get('image_url', '')
                source_name = item.get('source_id', 'NewsData')

            # Skip agar title ya URL missing hai
            if not title or not source_url:
                continue

            # 2. DUPLICATE CHECK
            if Article.objects.filter(source_url=source_url).exists() or Article.objects.filter(title=title).exists():
                continue # Agar pehle se DB mein hai toh skip kar dein
            
            # 3. CLEANING
            clean_desc = clean_text(raw_desc, max_length=150)
            # Agar content nahi hai toh description ko hi content bana dein
            actual_content = raw_content if raw_content else clean_desc
            clean_html_content = f"<p>{clean_text(actual_content)}</p>" # TinyMCE ke liye basic p tag

            # 4. CREATE DRAFT
            article = Article(
                title=title,
                description=clean_desc,
                content=clean_html_content,
                source_name=source_name[:100],
                source_url=source_url[:500],
                status='draft', # ALWAYS DRAFT - Safety rule
                is_imported=True,
                published_at=None 
            )
            
            # 5. DOWNLOAD IMAGE
            if image_url:
                try:
                    img_response = requests.get(image_url, timeout=5)
                    if img_response.status_code == 200:
                        file_name = f"imported_{uuid.uuid4().hex[:8]}.jpg"
                        article.featured_image.save(file_name, ContentFile(img_response.content), save=False)
                except Exception as e:
                    print(f"Image download failed for {title}: {e}")

            # 6. SAVE TO DATABASE
            article.save()
            imported_count += 1
            
        return f"✅ Successfully imported {imported_count} new DRAFT articles from {provider}."
        
    except Exception as e:
        return f"❌ Error fetching from {provider}: {str(e)}"