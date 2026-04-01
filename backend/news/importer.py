import requests
import uuid
from django.core.files.base import ContentFile
from django.utils.html import strip_tags
from news.models import Article

# Nayi library import ki (Alias diya 'WebArticle' taaki Django ke Article model se clash na ho)
from newspaper import Article as WebArticle 

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
    Ab ye pura article automatically scrape karega!
    """
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if provider == 'gnews':
            articles_data = data.get('articles', [])[:10]
        elif provider == 'newsdata':
            articles_data = data.get('results', [])[:10]
        else:
            return "Invalid provider specified."
            
        imported_count = 0
        
        for item in articles_data:
            # 1. MAPPING
            if provider == 'gnews':
                title = item.get('title', '').strip()
                source_url = item.get('url', '')
                raw_desc = item.get('description', '')
                image_url = item.get('image', '')
                source_name = item.get('source', {}).get('name', 'GNews')
            
            elif provider == 'newsdata':
                title = item.get('title', '').strip()
                source_url = item.get('link', '')
                raw_desc = item.get('description', '')
                image_url = item.get('image_url', '')
                source_name = item.get('source_id', 'NewsData')

            if not title or not source_url:
                continue

            # 2. DUPLICATE CHECK
            if Article.objects.filter(source_url=source_url).exists() or Article.objects.filter(title=title).exists():
                continue 
            
            clean_desc = clean_text(raw_desc, max_length=150)

            # ==========================================
            # 🚀 NAYA SMART SCRAPER LOGIC START
            # ==========================================
            full_content = ""
            print(f"Scraping full article from: {source_url}")
            try:
                # Article ke link par jao aur pura text nikalo
                web_article = WebArticle(source_url)
                web_article.download()
                web_article.parse()
                
                # Agar website ne text de diya toh use kar lo
                if web_article.text:
                    # Paragraphs ko properly HTML <p> tags mein wrap karo
                    paragraphs = web_article.text.split('\n\n')
                    full_content = "".join([f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()])
            except Exception as e:
                print(f"Scraping failed for {title}: {e}")

            # Agar scraping fail ho jaye, tabhi purana snippet (description) use karo
            final_html_content = full_content if full_content else f"<p>{clean_desc}</p>"
            # ==========================================

            # 4. CREATE DRAFT
            article = Article(
                title=title,
                description=clean_desc,
                content=final_html_content,  # <-- Ab yahan pura scraped content aayega
                source_name=source_name[:100],
                source_url=source_url[:500],
                status='draft', 
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
            
        return f"✅ Successfully imported {imported_count} new DRAFT articles from {provider} with FULL content."
        
    except Exception as e:
        return f"❌ Error fetching from {provider}: {str(e)}"