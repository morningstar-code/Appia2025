import asyncio
import os
from pathlib import Path
from config.system_config import SystemConfig
from agents.screenshot_agent import ScreenshotAgent

async def main():
    # Initialize config and agent
    config = SystemConfig()
    agent = ScreenshotAgent(config)
    
    # Example URL
    url = "https://example.com"
    
    # Create output directory if it doesn't exist
    output_dir = Path("screenshots")
    output_dir.mkdir(exist_ok=True)
    
    # Generate output path
    output_path = output_dir / f"{url.replace('://', '_').replace('/', '_')}.png"
    
    try:
        # Capture screenshot using async method
        screenshot_path = await agent.capture_full_page_url(url, str(output_path))
        print(f"Screenshot saved to: {screenshot_path}")
        
    except Exception as e:
        print(f"Error capturing screenshot: {str(e)}")
        
        # Try sync method as fallback
        try:
            screenshot_path = agent.capture_full_page_sync(url, str(output_path))
            print(f"Screenshot saved using sync method: {screenshot_path}")
        except Exception as e:
            print(f"Sync method also failed: {str(e)}")

if __name__ == "__main__":
    # Check for API key
    if not os.getenv('FIRECRAWL_API_KEY'):
        print("Please set FIRECRAWL_API_KEY environment variable")
        exit(1)
        
    # Run the async main function
    asyncio.run(main()) 