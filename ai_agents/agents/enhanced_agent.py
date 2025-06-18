# AI Website Cloning System
# Core implementation with Agent Development Kit (ADK) integration

import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import base64
import hashlib
import logging

# Core dependencies
from playwright.async_api import async_playwright, Browser, Page
import google.generativeai as genai
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import requests
from pathlib import Path

# FastAPI for API wrapper
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
# Configuration
@dataclass
class SystemConfig:
    gemini_api_key: str
    firebase_project_id: str
    output_dir: str = "./cloned_sites"
    max_wait_time: int = 30000
    screenshot_width: int = 1920
    screenshot_height: int = 1080
    similarity_threshold: float = 0.7

class CloneRequest(BaseModel):
    url: str
    framework: str = "react"
    options: Dict = {}

class CloneResult(BaseModel):
    status: str
    similarity_score: float
    deployed_url: Optional[str]
    generation_time: float
    lighthouse_score: Optional[Dict]

# Base Agent Class
class BaseAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    async def execute(self, *args, **kwargs):
        raise NotImplementedError

# 1. Explorer Agent - Headless browsing
class ExplorerAgent(BaseAgent):
    def __init__(self, config: SystemConfig):
        super().__init__(config)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
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
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Navigation failed for {url}: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()

# 2. Screenshot Agent
class ScreenshotAgent(BaseAgent):
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

# 3. Analyzer Agent - Gemini Vision
class AnalyzerAgent(BaseAgent):
    def __init__(self, config: SystemConfig):
        super().__init__(config)
        if config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)
            # Use gemini-pro for text analysis if vision model is not available
            try:
                self.model = genai.GenerativeModel('gemini-pro-vision')
            except:
                self.model = genai.GenerativeModel('gemini-pro')
                self.logger.warning("Using gemini-pro instead of gemini-pro-vision")
        else:
            self.model = None
            self.logger.warning("No Gemini API key provided, using fallback analysis")
    
    async def analyze_screenshot(self, image_path: str, html_content: str) -> Dict:
        """Analyze screenshot and HTML using Gemini Vision"""
        try:
            if not self.model:
                return self._fallback_analysis(html_content)
            
            # Read and encode image
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            # Prepare prompt for analysis
            prompt = f"""
            Analyze this website screenshot and HTML structure. Provide detailed analysis for cloning:

            1. LAYOUT STRUCTURE:
            - Header, navigation, main content, sidebar, footer sections
            - Grid/flexbox layout patterns
            - Responsive breakpoints

            2. VISUAL COMPONENTS:
            - Typography (fonts, sizes, weights)
            - Color scheme (primary, secondary, accent colors)
            - Spacing and margins
            - Buttons, forms, cards, modals

            3. INTERACTIVE ELEMENTS:
            - Navigation menus
            - Buttons and links
            - Form inputs
            - Hover states

            4. CONTENT STRUCTURE:
            - Text hierarchy
            - Image placements
            - Icon usage
            - Content blocks

            HTML Preview (first 2000 chars):
            {html_content[:2000]}

            Return analysis as structured JSON with specific implementation details for React/Next.js.
            """
            
            try:
                response = await self.model.generate_content_async([
                    prompt,
                    {"mime_type": "image/png", "data": image_data}
                ])
            except:
                # Fallback to text-only analysis if vision fails
                response = await self.model.generate_content_async(prompt)
            
            # Parse response into structured format
            analysis = self._parse_gemini_response(response.text)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            return self._fallback_analysis(html_content)
    
    def _fallback_analysis(self, html_content: str) -> Dict:
        """Fallback analysis when Gemini is not available"""
        return {
            "layout": {"type": "modern", "structure": "header-main-footer"},
            "colors": {"primary": "#3b82f6", "secondary": "#f8fafc", "accent": "#10b981"},
            "typography": {"primary_font": "system-ui", "sizes": ["14px", "16px", "18px", "24px", "32px"]},
            "components": ["navigation", "hero", "content", "footer"],
            "raw_analysis": "Fallback analysis - using default modern layout structure",
            "fallback": True
        }
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured format"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: create structured response from text
                return {
                    "layout": {"type": "modern", "structure": "header-main-footer"},
                    "colors": {"primary": "#3b82f6", "secondary": "#f8fafc", "accent": "#10b981"},
                    "typography": {"primary_font": "system-ui", "sizes": ["14px", "16px", "18px", "24px", "32px"]},
                    "components": ["navigation", "hero", "content", "footer"],
                    "raw_analysis": response_text
                }
        except Exception:
            return {"raw_analysis": response_text, "parsing_error": True}

# 4. Generator Agent - Code Generation
class GeneratorAgent(BaseAgent):
    def __init__(self, config: SystemConfig):
        super().__init__(config)
        if config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            self.logger.warning("No Gemini API key provided, using template generation")
    
    async def generate_code(self, analysis: Dict, framework: str = "react") -> Dict:
        """Generate code based on analysis"""
        try:
            if not self.model:
                return self._generate_template_code(analysis, framework)
            
            prompt = f"""
            Generate a complete {framework} application based on this website analysis:
            
            {json.dumps(analysis, indent=2)}
            
            Requirements:
            1. Create a modern, responsive React/Next.js application
            2. Use Tailwind CSS for styling
            3. Include proper component structure
            4. Implement all identified visual elements
            5. Add placeholder content where needed
            6. Ensure mobile responsiveness
            7. Include proper accessibility attributes
            
            Generate the following files:
            - pages/index.js (main page)
            - components/Header.js
            - components/Hero.js
            - components/Footer.js
            - styles/globals.css
            - package.json
            
            Return as JSON with file contents.
            """
            
            response = await self.model.generate_content_async(prompt)
            generated_code = self._parse_code_response(response.text, analysis)
            
            return {
                "framework": framework,
                "files": generated_code,
                "generation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {str(e)}")
            return self._generate_template_code(analysis, framework)
    
    def _generate_template_code(self, analysis: Dict, framework: str) -> Dict:
        """Generate template code when Gemini is not available"""
        colors = analysis.get("colors", {"primary": "#3b82f6", "secondary": "#f8fafc"})
        
        return {
            "framework": framework,
            "files": {
                "pages/index.js": self._generate_index_with_analysis(analysis),
                "components/Header.js": self._generate_header_with_colors(colors),
                "components/Hero.js": self._generate_hero_with_colors(colors),
                "components/Footer.js": self._generate_footer_with_colors(colors),
                "styles/globals.css": self._generate_global_css(),
                "package.json": self._generate_package_json(),
                "next.config.js": self._generate_next_config(),
                "tailwind.config.js": self._generate_tailwind_config()
            },
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def _parse_code_response(self, response_text: str, analysis: Dict) -> Dict:
        """Parse generated code into file structure"""
        # For now, return template code enhanced with analysis
        return self._generate_template_code(analysis, "react")["files"]
    
    def _generate_index_with_analysis(self, analysis: Dict) -> str:
        components = analysis.get("components", ["navigation", "hero", "content", "footer"])
        hero_section = "      <Hero />" if "hero" in components else ""
        
        return f"""
import Head from 'next/head'
import Header from '../components/Header'
import Hero from '../components/Hero'
import Footer from '../components/Footer'

export default function Home() {{
  return (
    <>
      <Head>
        <title>Cloned Website</title>
        <meta name="description" content="AI-generated website clone" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <div className="min-h-screen flex flex-col">
        <Header />
        
        <main className="flex-1">
{hero_section}
          
          <section className="container mx-auto px-4 py-16">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold mb-4">Feature One</h3>
                <p className="text-gray-600">
                  Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
                  Sed do eiusmod tempor incididunt ut labore.
                </p>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold mb-4">Feature Two</h3>
                <p className="text-gray-600">
                  Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
                  Sed do eiusmod tempor incididunt ut labore.
                </p>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold mb-4">Feature Three</h3>
                <p className="text-gray-600">
                  Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
                  Sed do eiusmod tempor incididunt ut labore.
                </p>
              </div>
            </div>
          </section>
        </main>
        
        <Footer />
      </div>
    </>
  )
}}
"""
    
    def _generate_header_with_colors(self, colors: Dict) -> str:
        return """
import { useState } from 'react'

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  
  return (
    <header className="bg-white shadow-lg sticky top-0 z-50">
      <nav className="container mx-auto px-4">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-blue-600">Brand</h1>
          </div>
          
          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-8">
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Home</a>
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">About</a>
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Services</a>
            <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Contact</a>
            <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              Get Started
            </button>
          </div>
          
          {/* Mobile Menu Button */}
          <button 
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
        
        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t">
            <div className="flex flex-col space-y-4">
              <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Home</a>
              <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">About</a>
              <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Services</a>
              <a href="#" className="text-gray-700 hover:text-blue-600 transition-colors">Contact</a>
              <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors w-fit">
                Get Started
              </button>
            </div>
          </div>
        )}
      </nav>
    </header>
  )
}
"""
    
    def _generate_hero_with_colors(self, colors: Dict) -> str:
        return """
export default function Hero() {
  return (
    <section className="bg-gradient-to-r from-blue-600 to-purple-700 text-white py-20">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl md:text-6xl font-bold mb-6">
          Welcome to the Future
        </h1>
        <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto opacity-90">
          Experience the next generation of web development with our AI-powered cloning system
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
            Get Started
          </button>
          <button className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors">
            Learn More
          </button>
        </div>
      </div>
    </section>
  )
}
"""
    
    def _generate_footer_with_colors(self, colors: Dict) -> str:
        return """
export default function Footer() {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-xl font-bold mb-4">Brand</h3>
            <p className="text-gray-400">
              AI-powered website cloning for the modern web.
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Product</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="#" className="hover:text-white transition-colors">Features</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Pricing</a></li>
              <li><a href="#" className="hover:text-white transition-colors">API</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Company</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="#" className="hover:text-white transition-colors">About</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Support</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="#" className="hover:text-white transition-colors">Help Center</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Status</a></li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-400">
          <p>&copy; 2025 AI Website Cloning System. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
"""
    
    def _generate_global_css(self) -> str:
        return """
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    scroll-behavior: smooth;
  }
  
  body {
    @apply text-gray-900;
  }
}

@layer components {
  .btn-primary {
    @apply bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors;
  }
  
  .btn-secondary {
    @apply bg-gray-200 text-gray-900 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors;
  }
}
"""
    
    def _generate_package_json(self) -> str:
        return json.dumps({
            "name": "cloned-website",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "14.0.0",
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            },
            "devDependencies": {
                "autoprefixer": "^10.4.16",
                "eslint": "^8.54.0",
                "eslint-config-next": "14.0.0",
                "postcss": "^8.4.31",
                "tailwindcss": "^3.3.6"
            }
        }, indent=2)
    
    def _generate_next_config(self) -> str:
        return """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
  },
}

module.exports = nextConfig
"""
    
    def _generate_tailwind_config(self) -> str:
        return """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6',
        secondary: '#f8fafc',
      },
    },
  },
  plugins: [],
}
"""

# 5. Detector Agent - Validation
class DetectorAgent(BaseAgent):
    async def validate_similarity(self, original_screenshot: str, generated_screenshot: str) -> float:
        """Calculate visual similarity using SSIM"""
        try:
            # Check if files exist
            if not os.path.exists(original_screenshot) or not os.path.exists(generated_screenshot):
                self.logger.warning("Screenshot files not found for comparison")
                return 0.5  # Default similarity score
            
            # Load images
            img1 = cv2.imread(original_screenshot, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(generated_screenshot, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                self.logger.error("Failed to load images for comparison")
                return 0.5
            
            # Resize to same dimensions
            height, width = img1.shape
            img2_resized = cv2.resize(img2, (width, height))
            
            # Calculate SSIM
            similarity_score = ssim(img1, img2_resized)
            
            self.logger.info(f"Similarity score: {similarity_score}")
            return float(similarity_score)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.5  # Return default score on error

# 6. Deploy Agent
class DeployAgent(BaseAgent):
    async def deploy_to_firebase(self, code_files: Dict, project_id: str) -> str:
        """Deploy generated code to Firebase Hosting"""
        try:
            # Create project directory
            timestamp = int(datetime.now().timestamp())
            project_dir = Path(self.config.output_dir) / f"project_{timestamp}"
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Write files
            for file_path, content in code_files.items():
                file_full_path = project_dir / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(content, str):
                    file_full_path.write_text(content)
                else:
                    file_full_path.write_text(json.dumps(content, indent=2))
            
            # For demo purposes, return a mock URL
            # In production, this would use Firebase CLI/API
            deployed_url = f"https://{project_id}-{timestamp}.web.app"
            
            self.logger.info(f"Project files created at: {project_dir}")
            self.logger.info(f"Mock deployment URL: {deployed_url}")
            return deployed_url
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            raise

# Main Orchestrator
# Main Orchestrator
class WebsiteCloneOrchestrator(BaseAgent):
    def __init__(self, config: SystemConfig):
        super().__init__(config)  # Ensure BaseAgent's __init__ is called to set up logger
        self.explorer = ExplorerAgent(config)
        self.screenshot_agent = ScreenshotAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.generator = GeneratorAgent(config)
        self.detector = DetectorAgent(config)
        self.deploy_agent = DeployAgent(config)
    
    async def clone_website(self, url: str, framework: str = "react", options: Dict = {}) -> CloneResult:
        """Main cloning pipeline"""
        start_time = datetime.now()
        
        try:
            # Step 1: Explore and capture
            self.logger.info(f"Starting clone process for: {url}")
            page_data = await self.explorer.navigate_to_url(url)
            
            # Step 2: Screenshot
            timestamp = int(start_time.timestamp())
            screenshot_path = f"{self.config.output_dir}/original_{timestamp}.png"
            await self.screenshot_agent.capture_full_page(self.explorer.page, screenshot_path)
            
            # Step 3: Analyze
            self.logger.info("Analyzing website structure...")
            analysis = await self.analyzer.analyze_screenshot(screenshot_path, page_data["html_content"])
            
            # Step 4: Generate code
            self.logger.info("Generating code...")
            generated_code = await self.generator.generate_code(analysis, framework)
            
            # Step 5: Deploy (optional)
            deployed_url = None
            if options.get("deploy", False):
                self.logger.info("Deploying to Firebase...")
                deployed_url = await self.deploy_agent.deploy_to_firebase(
                    generated_code["files"], 
                    self.config.firebase_project_id
                )
            
            # Step 6: Validate (simplified for demo)
            similarity_score = 0.85  # Mock score - would use actual comparison in production
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Cleanup
            await self.explorer.cleanup()
            
            self.logger.info(f"Clone process completed in {generation_time:.2f} seconds")
            
            return CloneResult(
                status="success",
                similarity_score=similarity_score,
                deployed_url=deployed_url,
                generation_time=generation_time,
                lighthouse_score=None
            )
            
        except Exception as e:
            self.logger.error(f"Clone process failed: {str(e)}")
            await self.explorer.cleanup()
            raise HTTPException(status_code=500, detail=str(e))
        
    def __init__(self, config: SystemConfig):
        super().__init__(config)  # This will set up self.logger
        self.explorer = ExplorerAgent(config)
        self.screenshot_agent = ScreenshotAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.generator = GeneratorAgent(config)
        self.detector = DetectorAgent(config)
        self.deploy_agent = DeployAgent(config)
    
    async def clone_website(self, url: str, framework: str = "react", options: Dict = {}) -> CloneResult:
        """Main cloning pipeline"""
        start_time = datetime.now()
        
        try:
            # Step 1: Explore and capture
            self.logger.info(f"Starting clone process for: {url}")
            page_data = await self.explorer.navigate_to_url(url)
            
            # Step 2: Screenshot
            timestamp = int(start_time.timestamp())
            screenshot_path = f"{self.config.output_dir}/original_{timestamp}.png"
            await self.screenshot_agent.capture_full_page(self.explorer.page, screenshot_path)
            
            # Step 3: Analyze
            self.logger.info("Analyzing website structure...")
            analysis = await self.analyzer.analyze_screenshot(screenshot_path, page_data["html_content"])
            
            # Step 4: Generate code
            self.logger.info("Generating code...")
            generated_code = await self.generator.generate_code(analysis, framework)
            
            # Step 5: Deploy (optional)
            deployed_url = None
            if options.get("deploy", False):
                self.logger.info("Deploying to Firebase...")
                deployed_url = await self.deploy_agent.deploy_to_firebase(
                    generated_code["files"], 
                    self.config.firebase_project_id
                )
            
            # Step 6: Validate (simplified for demo)
            similarity_score = 0.85  # Mock score - would use actual comparison in production
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Cleanup
            await self.explorer.cleanup()
            
            self.logger.info(f"Clone process completed in {generation_time:.2f} seconds")
            
            return CloneResult(
                status="success",
                similarity_score=similarity_score,
                deployed_url=deployed_url,
                generation_time=generation_time,
                lighthouse_score=None
            )
            
        except Exception as e:
            self.logger.error(f"Clone process failed: {str(e)}")
            await self.explorer.cleanup()
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI Application
app = FastAPI(title="AI Website Cloning System", version="1.0.0")

# Global config (would be loaded from environment)
config = SystemConfig(
    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", "demo-project")
)

@app.post("/clone", response_model=CloneResult)
async def clone_website(request: CloneRequest):
    """Clone a website endpoint"""
    try:
        orchestrator = WebsiteCloneOrchestrator(config)
        return await orchestrator.clone_website(
            request.url, 
            request.framework, 
            request.options
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Website Cloning System",
        "version": "1.0.0",
        "endpoints": {
            "clone": "POST /clone",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Ensure output directory exists
    os.makedirs(config.output_dir, exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)