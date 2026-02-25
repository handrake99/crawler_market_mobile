import requests
import logging
from typing import List, Dict, Any, Optional
import random

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

    def lookup_app_by_id(self, app_store_id: str, country: str) -> Optional[Dict[str, Any]]:
        """Looks up a specific app by ID in a specific regional store to fetch metadata."""
        lookup_url = f"https://itunes.apple.com/lookup?id={app_store_id}&country={country}"
        try:
            response = requests.get(lookup_url, timeout=10)
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                entry = data['results'][0]
                
                # Format to match _search_itunes_by_keyword output
                return {
                    'title': entry.get('trackName', ''),
                    'description': entry.get('description', ''),
                    'price': entry.get('formattedPrice', 'Free'),
                    'url': entry.get('trackViewUrl', ''),
                    'average_rating': float(entry.get('averageUserRating', 0.0)),
                    'rating_count': int(entry.get('userRatingCount', 0)),
                    'release_date': entry.get('releaseDate', ''),
                    'file_size_bytes': str(entry.get('fileSizeBytes', '0')),
                    'primary_genre': entry.get('primaryGenreName', '')
                }
            return None
        except Exception as e:
            logging.error(f"Error looking up app {app_store_id} in {country}: {e}")
            return None

    def get_app_reviews(self, app_id: str, app_title: str, country: str = "us") -> List[Dict[str, Any]]:
        logging.info(f"Fetching reviews for iOS app: {app_title} ({app_id}) in {country}")
        
        negative_reviews = []
        try:
            # Fallback to direct iTunes RSS feed since app_store_scraper is blocking JSON decodes
            for page in range(1, 11):  # Fetch up to 10 pages (500 reviews total max)
                url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    break
                    
                data = response.json()
                entries = data.get('feed', {}).get('entry', [])
                
                if not entries:
                    break
                    
                if isinstance(entries, dict):
                    entries = [entries]
                    
                for entry in entries:
                    if 'im:rating' not in entry:
                        continue # Skip app metadata entry
                        
                    rating_str = entry.get('im:rating', {}).get('label', '5')
                    try:
                        rating = int(rating_str)
                    except ValueError:
                        rating = 5
                        
                    if rating <= 3:
                        review_text = entry.get('content', {}).get('label', '')
                        date_str = entry.get('updated', {}).get('label', '')
                        negative_reviews.append({
                            'rating': rating,
                            'review': review_text,
                            'date': date_str
                        })
                        
                    if len(negative_reviews) >= 100:
                        break
                        
                if len(negative_reviews) >= 100:
                    break
                    
            logging.info(f"[{app_id}] Fetched {len(negative_reviews)} negative reviews from RSS feed.")
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
