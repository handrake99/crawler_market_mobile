import requests
import logging
from typing import List, Dict, Any
import random
from app_store_scraper import AppStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StoreScraper:
    def __init__(self):
        # A curated list of 20 diverse keywords where indie developers thrive (Micro-SaaS, Niche solutions)
        self.niche_keywords = [
            "ADHD Planner", "Visual Timer", "Minimalist tracker", 
            "Couple budget", "Neurodivergent focus", "Pomodoro study",
            "Freelance invoice", "Receipt tracker", "Pet journal",
            "Digital detox", "Mood tracker", "Baby sleep",
            "Intermittent fasting", "Plant care", "Habit builder",
            "Language flashcards", "Workout logger", "Medication reminder",
            "Subscription manager", "Flight tracker"
        ]

    def _search_itunes_by_keyword(self, keyword: str, country: str = "us", limit: int = 15) -> List[Dict[str, Any]]:
        logging.info(f"Searching iTunes App Store for keyword: '{keyword}' in country: '{country.upper()}'")
        
        # iTunes Search API endpoint
        search_url = f"https://itunes.apple.com/search?term={requests.utils.quote(keyword)}&country={country}&entity=software&limit={limit}"
        
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
                    
                    # V6 Extended Metrics
                    average_rating = float(entry.get('averageUserRating', 0.0))
                    rating_count = int(entry.get('userRatingCount', 0))
                    release_date = entry.get('releaseDate', '')
                    file_size_bytes = str(entry.get('fileSizeBytes', '0'))
                    primary_genre = entry.get('primaryGenreName', '')
                    
                    apps_data.append({
                        'app_id': app_id,
                        'title': title,
                        'description': description,
                        'price': formatted_price,
                        'url': entry.get('trackViewUrl', ''),
                        'source_keyword': keyword,
                        'average_rating': average_rating,
                        'rating_count': rating_count,
                        'release_date': release_date,
                        'file_size_bytes': file_size_bytes,
                        'primary_genre': primary_genre
                    })
        except Exception as e:
            logging.error(f"Error searching iOS for keyword '{keyword}' in {country}: {e}")
            
        return apps_data

    def get_top_target_apps(self, max_pool_size: int = 40, keywords: List[str] = None, countries: List[str] = None) -> List[Dict[str, Any]]:
        logging.info("Gathering initial app pool via Niche Keyword searches...")
        if not countries:
            countries = ['us']
            
        # If specific keywords are provided, use them. Otherwise, pick random 3 from the 20 list.
        if keywords and isinstance(keywords, list):
            search_keywords = keywords
            logging.info(f"Using provided keywords: {search_keywords}")
        else:
            search_keywords = random.sample(self.niche_keywords, min(3, len(self.niche_keywords)))
            logging.info(f"Using randomly selected keywords: {search_keywords}")
        
        # Merge dictionary by app_id
        merged_apps = {}
        
        for keyword in search_keywords:
            if len(merged_apps) >= max_pool_size:
                break
                
            for country in countries:
                results = self._search_itunes_by_keyword(keyword, country=country, limit=10)
                
                for app in results:
                    app_id = app['app_id']
                    if app_id not in merged_apps:
                        merged_apps[app_id] = {
                            "platform": "ios",
                            "app_store_id": app_id,
                            "source_keyword": keyword,
                            "country_data": {}
                        }
                    
                    merged_apps[app_id]["country_data"][country] = {
                        "title": app['title'],
                        "description": app['description'],
                        "price": app['price'],
                        "url": app['url'],
                        "average_rating": app['average_rating'],
                        "rating_count": app['rating_count'],
                        "release_date": app['release_date'],
                        "file_size_bytes": app['file_size_bytes'],
                        "primary_genre": app['primary_genre']
                    }
                    
        result_list = list(merged_apps.values())
        random.shuffle(result_list)
        logging.info(f"Gathered a raw pool of {len(result_list)} unique iOS apps for LLM filtering across countries: {countries}")
        return result_list[:max_pool_size]

    def get_app_reviews(self, app_id: str, app_title: str, country: str = "us") -> List[Dict[str, Any]]:
        logging.info(f"Fetching reviews for iOS app: {app_title} ({app_id}) in {country}")
        
        # app_store_scraper requires the app_name (cleaned title) and app_id
        # Heuristic to clean title representing the path part in iTunes url
        safe_title = ''.join(e for e in app_title.split('-')[0].split(':')[0] if e.isalnum() or e == ' ').strip().replace(' ', '-').lower()
        if not safe_title:
            safe_title = "app"
            
        try:
            ios_app = AppStore(country=country, app_name=safe_title, app_id=int(app_id))
            ios_app.review(how_many=150) # Fetch a batch to filter negative ones
            
            negative_reviews = []
            for review in ios_app.reviews:
                if review.get('rating', 5) <= 3: # 1 to 3 stars
                    negative_reviews.append({
                        'rating': review.get('rating'),
                        'review': review.get('review'),
                        'date': review.get('date').isoformat() if review.get('date') else None
                    })
                    if len(negative_reviews) >= 30:
                        break
                        
            return negative_reviews
        except Exception as e:
            logging.error(f"Error fetching reviews for {app_title}: {e}")
            return []

if __name__ == "__main__":
    scraper = StoreScraper()
    apps = scraper.get_top_target_apps(max_pool_size=15)
    print(f"Found {len(apps)} target apps.")
    if apps:
        app = apps[0]
        print(f"Sample App: {app['title']} - {app['url']} (From keyword: {app['source_keyword']})")
