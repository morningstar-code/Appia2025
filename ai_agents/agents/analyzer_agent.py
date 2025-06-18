from config.system_config import SystemConfig
import logging
import google.generativeai as genai
import re
import json
from typing import Dict
import os
import base64
from bs4 import BeautifulSoup  # For HTML text extraction in fallback

# Optional: Uncomment for Tesseract OCR fallback
import pytesseract
from PIL import Image

class AnalyzerAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        if config.gemini_api_key:
            self.logger.info("Using Gemini API key for analysis")
            genai.configure(api_key=config.gemini_api_key)
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.logger.info("Successfully initialized gemini-2.0-flash model")
            except Exception as e:
                self.logger.warning(f"Failed to initialize gemini-2.0-flash, trying gemini-pro: {e}")
                try:
                    self.model = genai.GenerativeModel('gemini-pro-vision')
                    self.logger.info("Successfully initialized gemini-pro-vision model")
                except Exception as e2:
                    self.logger.error(f"Failed to initialize gemini-pro-vision: {e2}")
                    try:
                        self.model = genai.GenerativeModel('gemini-pro')
                        self.logger.warning("Using gemini-pro (text-only) as fallback")
                    except Exception as e3:
                        self.logger.error(f"Failed to initialize any Gemini model: {e3}")
                        self.model = None
        else:
            self.model = None
            self.logger.warning("No Gemini API key provided, using fallback analysis")

    def _setup_logger(self):
        class ExtraFormatter(logging.Formatter):
            def format(self, record):
                extra_fields = {k: v for k, v in record.__dict__.items() if k not in [
                    'asctime', 'name', 'levelname', 'message', 'levelno', 'pathname',
                    'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'msg', 'args', 'funcName', 'lineno'
                ]}
                if extra_fields:
                    record.message = f"{record.msg} | Extra: {json.dumps(extra_fields, default=str)}"
                else:
                    record.message = record.msg
                return super().format(record)

        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(ExtraFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(stream_handler)

        file_handler = logging.FileHandler('analyzer_agent.log', encoding='utf-8')
        file_handler.setFormatter(ExtraFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        return logger

    def _detect_framework_from_html(self, html_content: str) -> Dict:
        frameworks = {
            "react": ["react", "_react", "jsx", "data-reactroot", "__REACT_DEVTOOLS"],
            "vue": ["vue", "_vue", "v-", "@click", "data-v-"],
            "angular": ["ng-", "[ng", "angular", "_angular"],
            "next": ["_next", "__next", "next.js"],
            "nuxt": ["_nuxt", "__nuxt", "nuxt.js"],
            "svelte": ["svelte", "_svelte"],
            "bootstrap": ["bootstrap", "btn-", "col-", "container-fluid"],
            "tailwind": ["tailwind", "tw-", "text-", "bg-", "flex", "grid"],
            "material-ui": ["mui", "material-ui", "makeStyles"],
            "chakra": ["chakra-ui", "css-"],
            "wordpress": ["wp-content", "wordpress", "wp-"],
            "shopify": ["shopify", "liquid", "theme_id"]
        }

        detected = {"frameworks": [], "css_frameworks": [], "cms": []}
        html_lower = html_content.lower()

        for framework, indicators in frameworks.items():
            for indicator in indicators:
                if indicator in html_lower:
                    if framework in ["react", "vue", "angular", "next", "nuxt", "svelte"]:
                        detected["frameworks"].append(framework)
                    elif framework in ["bootstrap", "tailwind", "material-ui", "chakra"]:
                        detected["css_frameworks"].append(framework)
                    elif framework in ["wordpress", "shopify"]:
                        detected["cms"].append(framework)
                    break

        return detected

    async def analyze_screenshot(self, image_path: str, html_content: str) -> Dict:
        self.logger.info(f"Starting analysis for image: {image_path}")
        self.logger.info(f"HTML content length: {len(html_content)}")

        try:
            if not os.path.exists(image_path):
                self.logger.error(f"Image file not found: {image_path}")
                raise FileNotFoundError(f"Image file not found: {image_path}")

            image_size = os.path.getsize(image_path)
            self.logger.info(f"Image file size: {image_size} bytes")

            framework_hints = self._detect_framework_from_html(html_content)
            self.logger.info("Framework detection complete", extra={
                "frameworks": framework_hints.get("frameworks", []),
                "css_frameworks": framework_hints.get("css_frameworks", []),
                "cms": framework_hints.get("cms", [])
            })

            if not self.model:
                self.logger.warning("No Gemini model available, using fallback analysis")
                result = self._fallback_analysis(html_content, framework_hints)
                self._log_analysis_result(result, "fallback")
                return result

            try:
                with open(image_path, 'rb') as img_file:
                    image_data = img_file.read()
                self.logger.info(f"Successfully read image data: {len(image_data)} bytes")
            except Exception as e:
                self.logger.error(f"Failed to read image file: {e}")
                result = self._fallback_analysis(html_content, framework_hints)
                self._log_analysis_result(result, "fallback")
                return result

            prompt = self._create_analysis_prompt(html_content, framework_hints)

            try:
                self.logger.info("Attempting vision analysis with Gemini")
                image_part = {"mime_type": "image/png", "data": image_data}
                response = await self.model.generate_content_async([prompt, image_part])

                if response and response.text:
                    self.logger.info(f"Got response from Gemini: {len(response.text)} characters")
                    self.logger.debug(f"Raw Gemini response: {response.text[:500]}...")
                    analysis = self._parse_gemini_response(response.text, framework_hints)
                    self._log_analysis_result(analysis, "vision")
                    return analysis
                else:
                    self.logger.error("Empty response from Gemini")
                    result = self._fallback_analysis(html_content, framework_hints)
                    self._log_analysis_result(result, "fallback")
                    return result

            except Exception as vision_error:
                self.logger.error(f"Vision analysis failed: {vision_error}")
                self.logger.info("Attempting text-only analysis")

                try:
                    text_prompt = self._create_text_only_prompt(html_content, framework_hints)
                    response = await self.model.generate_content_async(text_prompt)

                    if response and response.text:
                        self.logger.info("Got response from text-only analysis")
                        analysis = self._parse_gemini_response(response.text, framework_hints)
                        self._log_analysis_result(analysis, "text-only")
                        return analysis
                    else:
                        self.logger.error("Empty response from text-only analysis")
                        result = self._fallback_analysis(html_content, framework_hints)
                        self._log_analysis_result(result, "fallback")
                        return result

                except Exception as text_error:
                    self.logger.error(f"Text-only analysis also failed: {text_error}")
                    result = self._fallback_analysis(html_content, framework_hints)
                    self._log_analysis_result(result, "fallback")
                    return result

        except Exception as e:
            self.logger.error(f"Analysis failed with error: {str(e)}")
            result = self._fallback_analysis(html_content, framework_hints)
            self._log_analysis_result(result, "fallback")
            return result

    def _create_analysis_prompt(self, html_content: str, framework_hints: Dict) -> str:
        return f"""
        Analyze the provided website screenshot and HTML content to generate a detailed specification for cloning the website. Extract ALL VISIBLE TEXT from the screenshot using OCR-like capabilities and map it to specific components (e.g., header, main, footer). Combine this with design elements (layout, colors, typography) from both the screenshot and HTML to produce a comprehensive cloning specification.

        FRAMEWORK DETECTION HINTS:
        - JS Frameworks: {framework_hints.get('frameworks', [])}
        - CSS Frameworks: {framework_hints.get('css_frameworks', [])}
        - CMS: {framework_hints.get('cms', [])}

        HTML CONTENT (first 3000 chars):
        {html_content[:3000]}

        INSTRUCTIONS:
        1. Extract all text visible in the screenshot, including headings, paragraphs, buttons, navigation items, and footer text.
        2. Map extracted text to components (e.g., "Header: Welcome to Our Site", "Main: About Us").
        3. Identify design elements: framework, CSS framework, colors (hex codes), typography (font-family, sizes, weights), layout (grid/flexbox), and components (header, navigation, etc.).
        4. Provide detailed descriptions in `components_description`, `pages_description`, and `styles_description`, including exact text content for each component.
        5. Ensure `content_structure.text_content` includes a dictionary mapping components to their text content.
        6. Return a valid JSON object with the structure below, ensuring all fields are populated with accurate data.

        OUTPUT FORMAT:
        {{
            "framework": {{
                "primary": "react|vue|angular|next|nuxt|svelte|vanilla|unknown",
                "css": "tailwind|bootstrap|material-ui|chakra|styled-components|css-modules|vanilla|unknown",
                "build_tools": ["vite", "webpack", "parcel"],
                "backend_indicators": ["api", "graphql", "rest"]
            }},
            "layout": {{
                "type": "grid|flexbox|float|modern",
                "structure": "header-main-footer|sidebar-main|full-width|dashboard",
                "breakpoints": ["sm:640px", "md:768px", "lg:1024px", "xl:1280px"],
                "component_hierarchy": ["Header", "Navigation", "Main", "Footer"]
            }},
            "colors": {{
                "primary": "#hexcode",
                "secondary": "#hexcode",
                "accent": "#hexcode",
                "background": "#hexcode",
                "text": "#hexcode"
            }},
            "typography": {{
                "primary_font": "font-family-name",
                "font_sizes": ["12px", "14px", "16px", "18px", "24px"],
                "font_weights": [300, 400, 500, 600, 700],
                "line_heights": ["1.2", "1.4", "1.6"]
            }},
            "components": ["header", "navigation", "hero", "cards", "forms", "footer"],
            "interactive_elements": {{
                "navigation": ["dropdown", "hamburger", "tabs"],
                "buttons": ["primary", "secondary", "outline"],
                "forms": ["text-input", "select", "checkbox"],
                "animations": ["fade", "slide", "scale"]
            }},
            "content_structure": {{
                "sections": ["hero", "features", "testimonials", "cta", "footer"],
                "text_hierarchy": ["h1", "h2", "h3", "p"],
                "text_content": {{"header": "Extracted text", "main": "Extracted text", "footer": "Extracted text"}},
                "images": ["hero-bg", "thumbnails", "icons"],
                "icons": ["fontawesome", "heroicons", "custom"]
            }},
            "cloning_requirements": {{
                "npm_packages": ["react", "react-dom", "next", "tailwindcss"],
                "component_files": ["components/Header.html", "components/Main.html"],
                "components_description": {{
                    "components/Header.html": "Header with text 'Welcome to Our Site', blue background, flexbox layout",
                    "components/Main.html": "Main section with text 'About Us', centered content"
                }},
                "pages": ["index.html"],
                "pages_description": {{
                    "index.html": "Main page with header ('Welcome'), main ('About'), and footer ('Copyright')"
                }},
                "styles": ["style.css"],
                "styles_description": {{
                    "style.css": "Styles for layout, typography, and colors, including text styling"
                }},
                "config_files": {{"package.json": {{}}}},
                "assets": ["images/", "icons/"],
                "performance_tips": ["lazy-loading", "code-splitting"],
                "package_json": {{
                    "name": "cloned-website",
                    "version": "1.0.0",
                    "scripts": {{"start": "live-server"}},
                    "dependencies": {{}},
                    "devDependencies": {{"live-server": "^1.2.2"}}
                }}
            }}
        }}

        CONSTRAINTS:
        - Return ONLY valid JSON without markdown or extra text.
        - Ensure text_content includes all extracted text, mapped to components.
        - Use reasonable defaults for missing information (e.g., "unknown" for framework).
        - Include exact hex codes for colors and precise typography details.
        """

    def _create_text_only_prompt(self, html_content: str, framework_hints: Dict) -> str:
        return f"""
        Analyze this HTML content to generate a website cloning specification. Extract all text content from the HTML and map it to components (e.g., header, main, footer). Infer design elements from HTML structure, class names, and inline styles.

        FRAMEWORK HINTS: {framework_hints}
        HTML CONTENT: {html_content[:5000]}

        Return a JSON object with the same structure as the vision analysis, including:
        - `content_structure.text_content` with extracted text mapped to components.
        - Detailed `components_description` and `pages_description` with exact text content.
        Ensure all fields are populated with reasonable defaults if specific information is missing.
        """

    def _log_analysis_result(self, analysis: Dict, analysis_type: str) -> None:
        if not analysis:
            self.logger.error("Analysis dictionary is empty or None")
            return

        try:
            framework_info = analysis.get("framework", {})
            layout_info = analysis.get("layout", {})
            components = analysis.get("components", [])
            content_structure = analysis.get("content_structure", {})

            self.logger.info(f"Completed {analysis_type} analysis", extra={
                "framework": framework_info.get("primary", "unknown"),
                "css_framework": framework_info.get("css", "unknown"),
                "components_count": len(components),
                "layout_type": layout_info.get("type", "unknown"),
                "text_content_keys": list(content_structure.get("text_content", {}).keys())
            })

            cloning_req = analysis.get("cloning_requirements", {})
            if cloning_req:
                self.logger.info("Cloning requirements found", extra={
                    "npm_packages": cloning_req.get("npm_packages", []),
                    "component_files": cloning_req.get("component_files", []),
                    "pages": cloning_req.get("pages", []),
                    "styles": cloning_req.get("styles", [])
                })

                comp_desc = cloning_req.get("components_description", {})
                for comp_name, comp_desc_text in comp_desc.items():
                    self.logger.info(f"Component found: {comp_name}", extra={
                        "description": comp_desc_text[:200] + "..." if len(comp_desc_text) > 200 else comp_desc_text
                    })

                pages_desc = cloning_req.get("pages_description", {})
                for page_name, page_desc_text in pages_desc.items():
                    self.logger.info(f"Page found: {page_name}", extra={
                        "description": page_desc_text[:200] + "..." if len(page_desc_text) > 200 else page_desc_text
                    })

                styles_desc = cloning_req.get("styles_description", {})
                for style_name, style_desc_text in styles_desc.items():
                    self.logger.info(f"Style found: {style_name}", extra={
                        "description": style_desc_text[:200] + "..." if len(style_desc_text) > 200 else style_desc_text
                    })

                package_json = cloning_req.get("package_json", {})
                if package_json:
                    self.logger.info("Package.json generated", extra={
                        "name": package_json.get("name", "unknown"),
                        "dependencies": list(package_json.get("dependencies", {}).keys()),
                        "devDependencies": list(package_json.get("devDependencies", {}).keys())
                    })
                else:
                    self.logger.warning("No package.json found in cloning requirements")

                text_content = content_structure.get("text_content", {})
                if text_content:
                    self.logger.info("Text content extracted", extra={
                        "components_with_text": list(text_content.keys()),
                        "sample_text": {k: v[:50] + "..." if len(v) > 50 else v for k, v in text_content.items()}
                    })
                else:
                    self.logger.warning("No text content extracted")

        except Exception as e:
            self.logger.error(f"Error logging analysis result: {e}")

    def _parse_gemini_response(self, response_text: str, framework_hints: Dict = None) -> Dict:
        self.logger.debug(f"Parsing Gemini response: {len(response_text)} characters")

        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text.replace('```', '').strip()

            json_patterns = [
                r'\{[\s\S]*\}',
                r'(\{[\s\S]*?\})\s*$',
                r'```json\s*(\{[\s\S]*?\})\s*```',
                r'```\s*(\{[\s\S]*?\})\s*```'
            ]

            parsed_json = None
            for i, pattern in enumerate(json_patterns):
                try:
                    match = re.search(pattern, cleaned_text, re.DOTALL)
                    if match:
                        json_str = match.group(1) if match.lastindex else match.group(0)
                        parsed_json = json.loads(json_str)
                        self.logger.info(f"Successfully parsed JSON using pattern {i}")
                        break
                except json.JSONDecodeError as e:
                    self.logger.debug(f"Pattern {i} failed: {e}")
                    continue

            if parsed_json:
                validated_analysis = self._validate_and_enhance_analysis(parsed_json, framework_hints)
                return validated_analysis
            else:
                self.logger.error("Failed to parse JSON from Gemini response")
                self.logger.debug(f"Response text: {cleaned_text[:1000]}...")
                return self._extract_from_text_response(response_text, framework_hints)

        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {e}")
            return self._extract_from_text_response(response_text, framework_hints)

    def _validate_and_enhance_analysis(self, analysis: Dict, framework_hints: Dict = None) -> Dict:
        required_fields = ["framework", "layout", "colors", "typography", "components", "interactive_elements", "content_structure", "cloning_requirements"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = {} if field != "components" else []

        if framework_hints:
            framework = analysis.get("framework", {})
            if not framework.get("primary") or framework["primary"] == "unknown":
                framework["primary"] = framework_hints.get("frameworks", ["vanilla"])[0]
            if not framework.get("css") or framework["css"] == "unknown":
                framework["css"] = framework_hints.get("css_frameworks", ["vanilla"])[0]

        cloning_req = analysis.get("cloning_requirements", {})
        if not cloning_req.get("package_json"):
            cloning_req["package_json"] = {
                "name": "cloned-website",
                "version": "1.0.0",
                "description": "Cloned website",
                "scripts": {"start": "live-server", "build": "echo 'No build step required'"},
                "dependencies": {},
                "devDependencies": {"live-server": "^1.2.2"}
            }

        content_structure = analysis.get("content_structure", {})
        if not content_structure.get("text_content"):
            content_structure["text_content"] = {
                "header": "Default header text",
                "main": "Default main content",
                "footer": "Default footer text"
            }

        if not cloning_req.get("components_description"):
            cloning_req["components_description"] = {
                "components/Header.html": f"Header with text '{content_structure['text_content']['header']}', blue background, flexbox layout",
                "components/Main.html": f"Main section with text '{content_structure['text_content']['main']}', centered content",
                "components/Footer.html": f"Footer with text '{content_structure['text_content']['footer']}', dark background"
            }

        if not cloning_req.get("pages_description"):
            cloning_req["pages_description"] = {
                "index.html": f"Main page with header ('{content_structure['text_content']['header']}'), main ('{content_structure['text_content']['main']}'), and footer ('{content_structure['text_content']['footer']}')"
            }

        if not cloning_req.get("styles_description"):
            cloning_req["styles_description"] = {
                "style.css": "Main stylesheet with layout, typography, and component styles, including text styling"
            }

        return analysis

    def _extract_from_text_response(self, response_text: str, framework_hints: Dict = None) -> Dict:
        self.logger.info("Attempting text extraction from response")

        detected_framework = "vanilla"
        detected_css = "vanilla"
        if framework_hints:
            detected_framework = framework_hints.get("frameworks", ["vanilla"])[0]
            detected_css = framework_hints.get("css_frameworks", ["vanilla"])[0]

        text_content = {"header": "Welcome to Our Site", "main": "About Us Content", "footer": "Copyright 2025"}
        try:
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line and len(line) > 5:
                    if i < len(lines) * 0.3:
                        text_content["header"] = line[:100]
                    elif i < len(lines) * 0.7:
                        text_content["main"] = line[:100]
                    else:
                        text_content["footer"] = line[:100]
        except Exception as e:
            self.logger.debug(f"Failed to extract text from response: {e}")

        result = {
            "framework": {
                "primary": detected_framework,
                "css": detected_css,
                "build_tools": ["vite"] if detected_framework != "vanilla" else [],
                "backend_indicators": []
            },
            "layout": {
                "type": "flexbox",
                "structure": "header-main-footer",
                "breakpoints": ["sm:640px", "md:768px", "lg:1024px", "xl:1280px"],
                "component_hierarchy": ["Header", "Main", "Footer"]
            },
            "colors": {
                "primary": "#3b82f6",
                "secondary": "#f8fafc",
                "accent": "#10b981",
                "background": "#ffffff",
                "text": "#111827"
            },
            "typography": {
                "primary_font": "system-ui",
                "font_sizes": ["14px", "16px", "18px", "24px", "32px"],
                "font_weights": [400, 500, 600, 700],
                "line_heights": ["1.4", "1.6", "1.8"]
            },
            "components": ["header", "main", "footer"],
            "interactive_elements": {
                "navigation": ["hamburger"],
                "buttons": ["primary"],
                "forms": ["text-input"],
                "animations": ["fade"]
            },
            "content_structure": {
                "sections": ["hero", "main", "footer"],
                "text_hierarchy": ["h1", "h2", "p"],
                "text_content": text_content,
                "images": ["hero-bg", "content-images"],
                "icons": ["fontawesome"]
            },
            "cloning_requirements": {
                "npm_packages": self._get_packages_for_framework(detected_framework, detected_css),
                "component_files": ["components/Header.html", "components/Main.html", "components/Footer.html"],
                "components_description": {
                    "components/Header.html": f"Header with text '{text_content['header']}', blue background, flexbox layout",
                    "components/Main.html": f"Main section with text '{text_content['main']}', centered content",
                    "components/Footer.html": f"Footer with text '{text_content['footer']}', dark background"
                },
                "pages": ["index.html"],
                "pages_description": {
                    "index.html": f"Main page with header ('{text_content['header']}'), main ('{text_content['main']}'), and footer ('{text_content['footer']}')"
                },
                "styles": ["style.css"],
                "styles_description": {
                    "style.css": "Global CSS with reset, typography, layout, and component-specific styles"
                },
                "config_files": {"package.json": {}},
                "assets": ["images/", "icons/", "fonts/"],
                "performance_tips": ["lazy-loading", "image-optimization"],
                "package_json": {
                    "name": "cloned-website",
                    "version": "1.0.0",
                    "description": "Cloned website",
                    "scripts": {"start": "live-server", "build": "echo 'No build step required'"},
                    "dependencies": {},
                    "devDependencies": {"live-server": "^1.2.2"}
                }
            },
            "raw_analysis": response_text,
            "text_parsing_used": True
        }
        return result

    def _get_packages_for_framework(self, framework: str, css_framework: str) -> list:
        base_packages = []
        if framework == "react":
            base_packages = ["react", "react-dom"]
        elif framework == "next":
            base_packages = ["next", "react", "react-dom"]
        elif framework == "vue":
            base_packages = ["vue"]
        elif framework == "angular":
            base_packages = ["@angular/core", "@angular/common"]
        elif framework == "vanilla":
            base_packages = ["live-server"]
        if css_framework == "tailwind":
            base_packages.extend(["tailwindcss", "autoprefixer", "postcss"])
        elif css_framework == "bootstrap":
            base_packages.append("bootstrap")
        return base_packages or ["live-server"]

    def _fallback_analysis(self, html_content: str, framework_hints: Dict = None) -> Dict:
        self.logger.info("Using fallback analysis method")

        detected_framework = "vanilla"
        detected_css = "vanilla"
        if framework_hints:
            detected_framework = framework_hints.get("frameworks", ["vanilla"])[0]
            detected_css = framework_hints.get("css_frameworks", ["vanilla"])[0]

        # Extract text from HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = {
            "header": "Welcome to Our Site",
            "main": "Main Content",
            "footer": "Copyright 2025"
        }
        try:
            header = soup.find('header') or soup.find(attrs={"class": re.compile('header', re.I)})
            if header:
                text_content["header"] = header.get_text(strip=True)[:100] or text_content["header"]
            main = soup.find('main') or soup.find(attrs={"class": re.compile('main|content', re.I)})
            if main:
                text_content["main"] = main.get_text(strip=True)[:100] or text_content["main"]
            footer = soup.find('footer') or soup.find(attrs={"class": re.compile('footer', re.I)})
            if footer:
                text_content["footer"] = footer.get_text(strip=True)[:100] or text_content["footer"]
        except Exception as e:
            self.logger.debug(f"Failed to extract text from HTML: {e}")

        # Optional: Tesseract OCR fallback (uncomment if needed)
        try:
            img = Image.open(image_path)
            ocr_text = pytesseract.image_to_string(img)
            lines = ocr_text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line and len(line) > 5:
                    if i < len(lines) * 0.3:
                        text_content["header"] = line[:100]
                    elif i < len(lines) * 0.7:
                        text_content["main"] = line[:100]
                    else:
                        text_content["footer"] = line[:100]
        except Exception as e:
            self.logger.debug(f"Tesseract OCR failed: {e}")

        result = {
            "framework": {
                "primary": detected_framework,
                "css": detected_css,
                "build_tools": [],
                "backend_indicators": []
            },
            "layout": {
                "type": "flexbox",
                "structure": "header-main-footer",
                "breakpoints": ["sm:640px", "md:768px", "lg:1024px", "xl:1280px"],
                "component_hierarchy": ["Header", "Main", "Footer"]
            },
            "colors": self._extract_colors_from_html(html_content),
            "typography": self._extract_typography_from_html(html_content),
            "components": self._detect_components_from_html(html_content),
            "interactive_elements": {
                "navigation": ["hamburger"],
                "buttons": ["primary"],
                "forms": ["text-input"],
                "animations": ["fade"]
            },
            "content_structure": {
                "sections": ["hero", "main", "footer"],
                "text_hierarchy": ["h1", "h2", "p"],
                "text_content": text_content,
                "images": ["hero-bg", "content-images"],
                "icons": ["fontawesome"]
            },
            "cloning_requirements": {
                "npm_packages": self._get_packages_for_framework(detected_framework, detected_css),
                "component_files": ["components/Header.html", "components/Main.html", "components/Footer.html"],
                "components_description": {
                    "components/Header.html": f"Header with text '{text_content['header']}', blue background, flexbox layout",
                    "components/Main.html": f"Main section with text '{text_content['main']}', centered content",
                    "components/Footer.html": f"Footer with text '{text_content['footer']}', dark background"
                },
                "pages": ["index.html"],
                "pages_description": {
                    "index.html": f"Main page with header ('{text_content['header']}'), main ('{text_content['main']}'), and footer ('{text_content['footer']}')"
                },
                "styles": ["style.css"],
                "styles_description": {
                    "style.css": "Primary stylesheet with CSS reset, typography, layout grid, and component styling"
                },
                "config_files": {"package.json": {}},
                "assets": ["images/", "icons/", "fonts/"],
                "performance_tips": ["lazy-loading", "image-optimization"],
                "package_json": {
                    "name": "cloned-website",
                    "version": "1.0.0",
                    "description": "Cloned website using fallback analysis",
                    "scripts": {"start": "live-server", "build": "echo 'No build step required'"},
                    "dependencies": {},
                    "devDependencies": {"live-server": "^1.2.2"}
                }
            },
            "fallback": True,
            "framework_hints_applied": framework_hints or {}
        }
        return result

    def _extract_colors_from_html(self, html_content: str) -> Dict:
        colors = {
            "primary": "#3b82f6",
            "secondary": "#f8fafc",
            "accent": "#10b981",
            "background": "#ffffff",
            "text": "#111827"
        }

        color_patterns = [
            r'color:\s*([#\w]+)',
            r'background-color:\s*([#\w]+)',
            r'border-color:\s*([#\w]+)',
            r'#([0-9a-fA-F]{3,6})',
            r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)'
        ]

        found_colors = []
        for pattern in color_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            found_colors.extend(matches)

        if found_colors:
            unique_colors = list(set([color for color in found_colors if color.startswith('#') or color.isalnum()]))
            if len(unique_colors) >= 1:
                colors["primary"] = unique_colors[0] if unique_colors[0].startswith('#') else f"#{unique_colors[0]}"
            if len(unique_colors) >= 2:
                colors["secondary"] = unique_colors[1] if unique_colors[1].startswith('#') else f"#{unique_colors[1]}"

        return colors

    def _extract_typography_from_html(self, html_content: str) -> Dict:
        typography = {
            "primary_font": "system-ui",
            "font_sizes": ["14px", "16px", "18px", "24px", "32px"],
            "font_weights": [400, 500, 600, 700],
            "line_heights": ["1.4", "1.6", "1.8"]
        }

        font_patterns = [
            r'font-family:\s*([^;]+)',
            r'font-size:\s*(\d+(?:px|em|rem|%))',
            r'font-weight:\s*(\d+)',
            r'line-height:\s*([\d.]+)'
        ]

        for pattern in font_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                if 'font-family' in pattern:
                    typography["primary_font"] = matches[0].strip().replace('"', '').replace("'", "")
                elif 'font-size' in pattern:
                    sizes = [match for match in matches if match]
                    if sizes:
                        typography["font_sizes"] = list(set(sizes))[:5]
                elif 'font-weight' in pattern:
                    weights = [int(match) for match in matches if match.isdigit()]
                    if weights:
                        typography["font_weights"] = sorted(list(set(weights)))
                elif 'line-height' in pattern:
                    heights = [match for match in matches if match]
                    if heights:
                        typography["line_heights"] = list(set(heights))[:3]

        return typography

    def _detect_components_from_html(self, html_content: str) -> list:
        components = []
        component_indicators = {
            "header": ["<header", "class.*header", "id.*header"],
            "navigation": ["<nav", "class.*nav", "navbar", "menu"],
            "hero": ["class.*hero", "class.*banner", "class.*jumbotron"],
            "main": ["<main", "class.*main", "id.*main"],
            "content": ["class.*content", "class.*article"],
            "sidebar": ["class.*sidebar", "class.*aside", "<aside"],
            "footer": ["<footer", "class.*footer", "id.*footer"],
            "card": ["class.*card", "class.*tile"],
            "form": ["<form", "class.*form"],
            "button": ["<button", "class.*btn"],
            "modal": ["class.*modal", "class.*popup"],
            "carousel": ["class.*carousel", "class.*slider"],
            "gallery": ["class.*gallery", "class.*grid"]
        }

        html_lower = html_content.lower()
        for component, patterns in component_indicators.items():
            for pattern in patterns:
                if re.search(pattern, html_lower):
                    if component not in components:
                        components.append(component)
                    break

        basic_components = ["header", "main", "footer"]
        for basic in basic_components:
            if basic not in components:
                components.append(basic)

        return components

    def get_analysis_summary(self, analysis: Dict) -> str:
        if not analysis:
            return "No analysis data available"

        framework = analysis.get("framework", {})
        layout = analysis.get("layout", {})
        components = analysis.get("components", [])
        text_content = analysis.get("content_structure", {}).get("text_content", {})

        summary = f"""
Website Analysis Summary:
========================
Framework: {framework.get('primary', 'Unknown')}
CSS Framework: {framework.get('css', 'Unknown')}
Layout Type: {layout.get('type', 'Unknown')}
Components Found: {', '.join(components) if components else 'None'}
Cloning Method: {'AI-Powered' if not analysis.get('fallback') else 'Rule-Based Fallback'}
Extracted Text:
- Header: {text_content.get('header', 'None')}
- Main: {text_content.get('main', 'None')}
- Footer: {text_content.get('footer', 'None')}
"""

        cloning_req = analysis.get("cloning_requirements", {})
        if cloning_req:
            npm_packages = cloning_req.get("npm_packages", [])
            component_files = cloning_req.get("component_files", [])

            summary += f"""
Required Packages: {', '.join(npm_packages) if npm_packages else 'None'}
Component Files: {len(component_files)} files
Generated Files: {', '.join(cloning_req.get('pages', []))}
"""

        return summary