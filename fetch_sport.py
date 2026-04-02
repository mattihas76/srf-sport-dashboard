import urllib.request
import json
import re
import os
from datetime import datetime

CATEGORIES = [
    {"name": "Fussball", "emoji": "⚽", "url": "https://www.srf.ch/sport/fussball"},
    {"name": "Eishockey", "emoji": "🏒", "url": "https://www.srf.ch/sport/eishockey"},
    {"name": "Tennis", "emoji": "🎾", "url": "https://www.srf.ch/sport/tennis"},
    {"name": "Mehr Sport", "emoji": "🏅", "url": "https://www.srf.ch/sport/mehr-sport"},
]

def fetch_category(cat):
    """Scrape 3 headlines + images from a single SRF Sport category page."""
    url = cat["url"]
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    try:
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
    except Exception as e:
        print(f"  Fehler beim Abrufen von {url}: {e}")
        return []

    articles = []
    
    # SRF uses article teaser blocks. We look for linked article cards with titles and images.
    # Pattern: find article teaser links with their href, image src, and text content.
    
    # Strategy 1: Extract article links with their surrounding context
    # SRF wraps articles in <a> tags with class containing 'teaser' or similar
    # Each article link contains an <img> and headline text
    
    # Find all major linked blocks that point to /sport/ articles
    link_pattern = re.compile(
        r'<a\s[^>]*href=["\'](/sport/[^"\']+)["\'][^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE
    )
    
    seen_urls = set()
    
    for match in link_pattern.finditer(html):
        href = match.group(1)
        content = match.group(2)
        
        # Skip navigation/category links, only want actual articles
        if '/category/' in href or href.count('/') < 3:
            continue
        
        # Skip result center / live links
        if 'resultcenter' in href or 'tippspiel' in href:
            continue
        
        # Skip duplicate URLs
        full_url = "https://www.srf.ch" + href
        if full_url in seen_urls:
            continue
        
        # Extract image from within this link block
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        # Also try srcset for higher quality
        srcset_match = re.search(r'srcset=["\']([^"\']+)["\']', content)
        
        image_url = ""
        if srcset_match:
            # Take the largest image from srcset (last entry)
            srcset = srcset_match.group(1)
            parts = [p.strip().split(' ')[0] for p in srcset.split(',') if p.strip()]
            if parts:
                image_url = parts[-1]  # largest
        elif img_match:
            image_url = img_match.group(1)
        
        # Skip articles without images
        if not image_url:
            continue
        
        # Make image URL absolute
        if not image_url.startswith('http'):
            image_url = "https://www.srf.ch" + image_url
        
        # Extract text - strip all HTML tags
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Skip if too short (navigation items)
        if len(clean_text) < 15:
            continue
        
        # Skip promotional/tippspiel links
        if 'mitmachen' in clean_text.lower():
            continue
        
        # Try to split into title and subtitle
        # SRF typically structures: "Category Title  Subtitle  Description"
        # We'll grab the meaningful parts
        # Remove boilerplate teaser text
        clean_text = re.split(r'Hier finden Sie', clean_text, flags=re.IGNORECASE)[0].strip()
        title = clean_text
        
        seen_urls.add(full_url)
        articles.append({
            "title": title,
            "url": full_url,
            "image": image_url,
        })
        
        if len(articles) >= 2:
            break
    
    return articles


def fetch_all():
    """Fetch headlines from all SRF Sport categories and save to JSON."""
    print("SRF Sport Dashboard - Daten werden aktualisiert...")
    print(f"Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    
    result = {
        "lastUpdated": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "categories": []
    }
    
    for cat in CATEGORIES:
        print(f"Lade {cat['name']}...")
        articles = fetch_category(cat)
        print(f"  -> {len(articles)} Artikel gefunden")
        
        result["categories"].append({
            "name": cat["name"],
            "emoji": cat["emoji"],
            "url": cat["url"],
            "articles": articles
        })
    
    # Save to JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'sport_data.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    total = sum(len(c["articles"]) for c in result["categories"])
    print(f"\nFertig! {total} Artikel in sport_data.json gespeichert.")


if __name__ == '__main__':
    fetch_all()
