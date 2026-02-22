import requests
import re
import pandas as pd
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RedditScraper:
    def __init__(self):
        # We use a custom User-Agent to avoid getting blocked by Reddit API too quickly
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 AppMarketAnalyzerBot/1.0'
        }
        self.subreddits = ['SaaS', 'SideProject', 'indiehackers']

    def _extract_mrr_and_url(self, text: str) -> Dict[str, Any]:
        """
        Attempt to extract MRR (Monthly Recurring Revenue) numbers and URLs from a text block
        using regular expressions.
        """
        result = {'mrr_detected': False, 'mrr_value': 0, 'urls': []}
        
        # Look for MRR patterns like "$1K MRR", "1000 MRR", "$5000/mo"
        mrr_patterns = [
            r'\$([0-9,.]+)[kK]?\s*MRR',
            r'([0-9,.]+)[kK]?\s*MRR',
            r'\$([0-9,.]+)\s*/\s*mo(?:nth)?'
        ]
        
        for pattern in mrr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(',', '')
                try:
                    # Very basic handling of 'k' suffix if it existed in original string
                    multiplier = 1000 if 'k' in text[match.start():match.end()].lower() else 1
                    result['mrr_value'] = float(val_str) * multiplier
                    result['mrr_detected'] = True
                except ValueError:
                    pass
                break # Found one match, good enough for basic filtering
                
        # Extract URLs
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        urls = re.findall(url_pattern, text)
        result['urls'] = [url for url in urls if 'reddit.com' not in url.lower() and 'imgur.com' not in url.lower()]
        
        return result

    def get_trending_apps(self, limit: int = 100) -> List[Dict[str, Any]]:
        logging.info("Fetching trending apps from Reddit...")
        trending_apps = []
        
        for sub in self.subreddits:
            try:
                # Using the JSON endpoint of standard Reddit without PRAW to avoid needing API keys for simple scraping
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        selftext = post_data.get('selftext', '')
                        score = post_data.get('score', 0)
                        
                        # Combine title and text for analysis
                        full_text = f"{title}. {selftext}"
                        
                        # Extract insights
                        insights = self._extract_mrr_and_url(full_text)
                        
                        # Filter criteria: We want posts that either explicitly mention MRR or have high engagement (score > 50) AND have an external link (presumably the app)
                        if (insights['mrr_detected'] or score > 50) and insights['urls']:
                            # Heuristic: the first non-reddit URL is often the project link
                            project_url = insights['urls'][0]
                            
                            trending_apps.append({
                                'source': f'r/{sub}',
                                'title': title,
                                'url': project_url,
                                'score': score,
                                'mrr': insights['mrr_value'] if insights['mrr_detected'] else None,
                                'post_url': f"https://www.reddit.com{post_data.get('permalink')}"
                            })
                else:
                    logging.warning(f"Failed to fetch r/{sub}: Status {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error scraping Reddit r/{sub}: {e}")
                
        # Sort by score or MRR to find the "best" ones
        trending_apps.sort(key=lambda x: (x['mrr'] is not None, x['score']), reverse=True)
        
        # Deduplicate by URL
        unique_apps = []
        seen_urls = set()
        for app in trending_apps:
            if app['url'] not in seen_urls:
                unique_apps.append(app)
                seen_urls.add(app['url'])
                
        logging.info(f"Found {len(unique_apps)} potential apps from Reddit.")
        return unique_apps

if __name__ == "__main__":
    scraper = RedditScraper()
    apps = scraper.get_trending_apps(limit=25)
    df = pd.DataFrame(apps)
    print(df.head())
