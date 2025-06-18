from config.system_config import SystemConfig
from playwright.async_api import Page
from pathlib import Path
import logging
from typing import Dict

class ScreenshotAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    async def capture_full_page(self, page: Page, output_path: str) -> str:
        """Capture full page screenshot"""
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=output_path, full_page=True)
            self.logger.info(f"Screenshot saved: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Screenshot failed: {str(e)}")
            raise

    async def capture_full_page_url(self, url: str, output_path: str) -> str:
        # This is a stub for compatibility with orchestrator; implement as needed
        self.logger.info(f"Stub: Would capture screenshot of {url} to {output_path}")
        return output_path
