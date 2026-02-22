import requests
import logging
from typing import List, Dict, Any
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StoreScraper:
    def __init__(self):
        # A curated list of keywords where indie developers thrive (Micro-SaaS, Niche solutions)
        self.niche_keywords = [
            "ADHD Planner", "Visual Timer", "Minimalist tracker", 
            "Couple budget", "Neurodivergent focus", "Pomodoro study",
            "Freelance invoice", "Receipt tracker", "Pet journal",
            "Digital detox", "Mood tracker"
        ]

    def _search_itunes_by_keyword(self, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        logging.info(f"Searching iTunes App Store for keyword: '{keyword}'")
        
        # iTunes Search API endpoint
        # entity=software ensures we only get apps
        search_url = f"https://itunes.apple.com/search?term={requests.utils.quote(keyword)}&country=us&entity=software&limit={limit}"
        
        apps_data = []
        try:
            response = requests.get(search_url, timeout=10)
            data = response.json()
            
            if 'results' in data:
                for entry in data['results']:
                    # Filter out games (PrimaryGenreId 6014) if possible, focus on utilities/productivity
                    genre = entry.get('primaryGenreName', '')
                    if 'Games' in genre:
                        continue
                        
                    app_id = str(entry.get('trackId', ''))
                    title = entry.get('trackName', '')
                    description = entry.get('description', '')
                    price = entry.get('price', 0.0)
                    formatted_price = entry.get('formattedPrice', 'Free')
                    
                    apps_data.append({
                        'platform': 'ios',
                        'app_id': app_id,
                        'title': title,
                        'description': description,
                        'price': formatted_price,
                        'url': entry.get('trackViewUrl', ''),
                        'source_keyword': keyword
                    })
        except Exception as e:
            logging.error(f"Error searching iOS for keyword '{keyword}': {e}")
            
        return apps_data

    def get_top_target_apps(self, max_pool_size: int = 40) -> List[Dict[str, Any]]:
        logging.info("Gathering initial app pool via Niche Keyword searches...")
        targets = []
        seen_ids = set()
        
        # Randomize keyword order each day to explore different verticals
        random.shuffle(self.niche_keywords)
        
        for keyword in self.niche_keywords:
            if len(targets) >= max_pool_size:
                break
                
            # Fetch 10 apps per keyword to cast a wide net
            results = self._search_itunes_by_keyword(keyword, limit=10)
            
            for app in results:
                if app['app_id'] not in seen_ids:
                    targets.append(app)
                    seen_ids.add(app['app_id'])
                    
        logging.info(f"Gathered a raw pool of {len(targets)} unique iOS apps for LLM filtering.")
        return targets

if __name__ == "__main__":
    scraper = StoreScraper()
    apps = scraper.get_top_target_apps(max_pool_size=15)
    print(f"Found {len(apps)} target apps.")
    if apps:
        app = apps[0]
        print(f"Sample App: {app['title']} - {app['url']} (From keyword: {app['source_keyword']})")
