from config.system_config import SystemConfig
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, Page
import logging
from typing import Dict

class ExplorerAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': self.config.screenshot_width, 'height': self.config.screenshot_height}
        )
        self.page = await context.new_page()
    
    async def navigate_to_url(self, url: str) -> Dict:
        """Navigate to URL and gather basic page info"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            response = await self.page.goto(url, wait_until='networkidle', timeout=self.config.max_wait_time)
            
            # Gather page metadata
            title = await self.page.title()
            
            # Try to get meta description safely
            try:
                meta_description = await self.page.get_attribute('meta[name="description"]', 'content') or ""
            except:
                meta_description = ""
            
            # Get page structure
            html_content = await self.page.content()
            
            return {
                "url": url,
                "title": title,
                "description": meta_description,
                "html_content": html_content,
                "status_code": response.status if response else None,
                "timestamp": None
            }
        except Exception as e:
            self.logger.error(f"Navigation failed for {url}: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()
