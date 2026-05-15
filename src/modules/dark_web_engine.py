"""
Inspector Rabbit - Dark Web Search Engine
Searches the Tor network using public onion search gateways.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from PyQt6.QtCore import QThread, pyqtSignal

class DarkWebEngine:
    """Engine for searching onion sites via public gateways."""
    
    # Public gateways for onion search
    GATEWAYS = [
        {
            "name": "Ahmia",
            "search_url": "https://ahmia.fi/search/?q={}",
            "result_selector": "li.result",
            "title_selector": "a",
            "link_selector": "a",
            "snippet_selector": "p",
            "onion_regex": r"([a-z2-7]{16,56}\.onion)"
        },
        {
            "name": "Phobos",
            "search_url": "https://phobos.fi/search?q={}",
            "result_selector": "div.result",
            "title_selector": "h4",
            "link_selector": "a",
            "snippet_selector": "p",
            "onion_regex": r"([a-z2-7]{16,56}\.onion)"
        }
    ]

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=20)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def search(self, query: str) -> List[Dict]:
        """Search multiple gateways for the given query."""
        tasks = []
        async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
            for gateway in self.GATEWAYS:
                tasks.append(self._search_gateway(session, gateway, query))
            
            results = await asyncio.gather(*tasks)
            
        # Flatten and deduplicate by onion address
        all_results = []
        seen_onions = set()
        
        for gateway_results in results:
            for res in gateway_results:
                onion = res.get("onion")
                if onion and onion not in seen_onions:
                    seen_onions.add(onion)
                    all_results.append(res)
        
        return all_results

    async def _search_gateway(self, session: aiohttp.ClientSession, gateway: Dict, query: str) -> List[Dict]:
        """Search a specific gateway."""
        url = gateway["search_url"].format(query)
        results = []
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, "lxml")
                
                items = soup.select(gateway["result_selector"])
                for item in items:
                    title_elem = item.select_one(gateway["title_selector"])
                    link_elem = item.select_one(gateway["link_selector"])
                    snippet_elem = item.select_one(gateway["snippet_selector"])
                    
                    if not title_elem or not link_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    raw_link = link_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Extract onion address
                    onion_match = re.search(gateway["onion_regex"], raw_link)
                    if not onion_match:
                        # Try searching in title or snippet
                        onion_match = re.search(gateway["onion_regex"], title + " " + snippet)
                    
                    if onion_match:
                        onion = onion_match.group(1)
                        results.append({
                            "title": title,
                            "onion": onion,
                            "snippet": snippet,
                            "source": gateway["name"],
                            "full_link": f"http://{onion}"
                        })
        except Exception as e:
            print(f"Error searching {gateway['name']}: {e}")
            
        return results

class DarkWebThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query
        self.engine = DarkWebEngine()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.engine.search(self.query))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
