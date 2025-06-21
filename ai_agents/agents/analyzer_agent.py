from config.system_config import SystemConfig
from pathlib import Path
import logging
import google.generativeai as genai
import re
import json
from typing import Dict, Optional, List, Tuple
import os
import base64
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from google.adk.artifacts import InMemoryArtifactService
from google.genai.types import Part

class AnalyzerAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.artifact_service = InMemoryArtifactService()
        
        # Initialize Gemini API - Required
        if not hasattr(config, 'gemini_api_key') or not config.gemini_api_key:
            raise ValueError("Gemini API key is required for analysis")
        
        self.logger.info("Initializing Gemini API for pixel-perfect analysis")
        genai.configure(api_key=config.gemini_api_key)
        self.model = self._initialize_gemini_model()
        
        if not self.model:
            raise RuntimeError("Failed to initialize Gemini model")

    def _setup_logger(self):
        """Setup logger for detailed analysis tracking"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    def _initialize_gemini_model(self):
        """Initialize Gemini model with vision capabilities"""
        model_options = [
            'gemini-2.0-flash-exp',
            'gemini-2.0-flash',
            'gemini-1.5-pro',
            'gemini-pro-vision'
        ]
        
        for model_name in model_options:
            try:
                model = genai.GenerativeModel(model_name)
                self.logger.info(f"Successfully initialized {model_name} model")
                return model
            except Exception as e:
                self.logger.warning(f"Failed to initialize {model_name}: {e}")
                continue
        
        self.logger.error("Failed to initialize any Gemini model")
        return None

    def _get_fallback_analysis(self, image_path: str) -> Dict:
        """Generate a fallback analysis structure when Gemini fails"""
        self.logger.warning("Generating fallback analysis structure")
        
        return {
            "viewport_analysis": {
                "estimated_width": "1200px",
                "estimated_height": "800px", 
                "device_type": "desktop",
                "responsive_indicators": []
            },
            "visual_elements": [
                {
                    "id": "main_container",
                    "type": "container",
                    "position": {"x": 0, "y": 0, "width": 1200, "height": 800},
                    "styling": {
                        "background": "#ffffff",
                        "color": "#000000",
                        "font_family": "Arial, sans-serif",
                        "font_size": "16px",
                        "font_weight": "400",
                        "padding": "20px",
                        "margin": "0",
                        "border": "none",
                        "border_radius": "0px",
                        "box_shadow": "none"
                    },
                    "content": "Main content area",
                    "children": []
                }
            ],
            "dynamic_components": {
                "detected_sections": [
                    {
                        "name": "main_content",
                        "elements": ["main_container"],
                        "suggested_component": "MainContent.tsx",
                        "props_needed": ["children"],
                        "styling_classes": ["main-container"]
                    }
                ]
            },
            "layout_system": {
                "type": "flexbox",
                "container_structure": {
                    "max_width": "1200px",
                    "margin": "0 auto",
                    "padding": "0 20px",
                    "display": "flex",
                    "flex_direction": "column",
                    "gap": "20px"
                },
                "breakpoints": {
                    "mobile": "768px",
                    "tablet": "1024px", 
                    "desktop": "1200px"
                }
            },
            "color_palette": {
                "primary": "#2563eb",
                "secondary": "#64748b",
                "accent": "#0ea5e9",
                "background": "#ffffff",
                "text_primary": "#1e293b",
                "text_secondary": "#475569",
                "borders": "#e2e8f0",
                "extracted_colors": ["#2563eb", "#64748b", "#0ea5e9", "#ffffff", "#1e293b"]
            },
            "typography_system": {
                "font_families": ["Inter", "system-ui", "sans-serif"],
                "font_sizes": {
                    "xs": "12px",
                    "sm": "14px", 
                    "base": "16px",
                    "lg": "18px",
                    "xl": "20px",
                    "2xl": "24px",
                    "3xl": "30px"
                },
                "font_weights": {
                    "light": 300,
                    "normal": 400,
                    "medium": 500,
                    "semibold": 600,
                    "bold": 700
                },
                "line_heights": {
                    "tight": "1.25",
                    "normal": "1.5", 
                    "relaxed": "1.75"
                }
            },
            "spacing_system": {
                "base_unit": "4px",
                "scale": ["2px", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "40px", "48px"],
                "common_margins": ["8px", "16px", "24px"],
                "common_paddings": ["12px", "16px", "20px"]
            }
        }

    async def analyze_screenshot(self, image_path: str, html_content: str = "") -> Dict:
        """Main pixel-perfect analysis method"""
        self.logger.info(f"Starting pixel-perfect analysis for image: {image_path}")
        
        # Validate image file
        if not os.path.exists(image_path):
            self.logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        image_size = os.path.getsize(image_path)
        self.logger.info(f"Image file size: {image_size} bytes")
        
        # Parse HTML content
        html_text = ""
        analysis_config = {}
        try:
            if html_content:
                html_data = json.loads(html_content)
                html_text = html_data.get('content', '')
                analysis_config = html_data.get('analysis_config', {})
        except json.JSONDecodeError:
            html_text = html_content
        
        # Perform enhanced Gemini analysis with fallback
        try:
            analysis = await self._gemini_pixel_analysis(image_path, html_text)
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {e}")
            self.logger.info("Using fallback analysis")
            analysis = self._get_fallback_analysis(image_path)
        
        # Ensure analysis has required structure
        analysis = self._validate_and_fix_analysis(analysis)
        
        # Generate dynamic components based on analysis
        analysis = self._generate_dynamic_components(analysis)
        
        # Save analysis as artifact
        try:
            analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
            try:
                artifact_part = Part(
                    data=analysis_json.encode('utf-8'),
                    mime_type="application/json"
                )
            except Exception:
                try:
                    artifact_part = Part(text=analysis_json)
                except Exception:
                    raise Exception("Could not create Part object")
            
            revision_id = await self.artifact_service.save_artifact(
                app_name="pixel_analyzer_app",
                user_id="user_pixel_analyzer",
                session_id="session_pixel_analyzer",
                filename=f"pixel_analysis_{Path(image_path).stem}.json",
                artifact=artifact_part
            )
            self.logger.info(f"Pixel analysis artifact saved with revision ID: {revision_id}")
        except Exception as artifact_error:
            self.logger.warning(f"Failed to save artifact: {artifact_error}")
        
        return analysis

    def _validate_and_fix_analysis(self, analysis: Dict) -> Dict:
        """Validate analysis structure and add missing required fields"""
        
        # Ensure color_palette exists with all required colors
        if "color_palette" not in analysis or not isinstance(analysis["color_palette"], dict):
            analysis["color_palette"] = {}
        
        default_colors = {
            "primary": "#2563eb",
            "secondary": "#64748b", 
            "accent": "#0ea5e9",
            "background": "#ffffff",
            "text_primary": "#1e293b",
            "text_secondary": "#475569",
            "borders": "#e2e8f0",
            "extracted_colors": ["#2563eb", "#64748b", "#0ea5e9", "#ffffff", "#1e293b"]
        }
        
        for color_key, default_value in default_colors.items():
            if color_key not in analysis["color_palette"]:
                analysis["color_palette"][color_key] = default_value
        
        # Ensure typography_system exists
        if "typography_system" not in analysis:
            analysis["typography_system"] = {
                "font_families": ["Inter", "system-ui", "sans-serif"],
                "font_sizes": {
                    "xs": "12px", "sm": "14px", "base": "16px", "lg": "18px", 
                    "xl": "20px", "2xl": "24px", "3xl": "30px"
                },
                "font_weights": {
                    "light": 300, "normal": 400, "medium": 500, "semibold": 600, "bold": 700
                },
                "line_heights": {
                    "tight": "1.25", "normal": "1.5", "relaxed": "1.75"
                }
            }
        
        # Ensure spacing_system exists
        if "spacing_system" not in analysis:
            analysis["spacing_system"] = {
                "base_unit": "4px",
                "scale": ["2px", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "40px", "48px"],
                "common_margins": ["8px", "16px", "24px"],
                "common_paddings": ["12px", "16px", "20px"]
            }
        
        # Ensure visual_elements exists
        if "visual_elements" not in analysis:
            analysis["visual_elements"] = []
        
        # Ensure dynamic_components exists
        if "dynamic_components" not in analysis:
            analysis["dynamic_components"] = {"detected_sections": []}
        
        return analysis

    def analyze_screenshot_sync(self, image_path: str, html_content: str = "") -> Dict:
        """Synchronous version of pixel-perfect analysis"""
        return asyncio.run(self.analyze_screenshot(image_path, html_content))

    async def _gemini_pixel_analysis(self, image_path: str, html_content: str) -> Dict:
        """Perform pixel-perfect analysis using Gemini API"""
        # Read image data
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()
        
        self.logger.info(f"Successfully read image data: {len(image_data)} bytes")
        
        # Create pixel-perfect analysis prompt
        prompt = self._create_pixel_perfect_prompt(html_content)
        
        # Perform vision analysis
        self.logger.info("Performing pixel-perfect vision analysis with Gemini")
        image_part = {"mime_type": "image/png", "data": image_data}
        
        response = await self.model.generate_content_async([prompt, image_part])
        
        if not response or not response.text:
            raise RuntimeError("Empty response from Gemini vision analysis")
        
        self.logger.info(f"Got response from Gemini: {len(response.text)} characters")
        analysis = self._parse_gemini_response(response.text)
        
        return analysis

    def _create_pixel_perfect_prompt(self, html_content: str) -> str:
        """Create enhanced prompt for pixel-perfect analysis"""
        return f"""
PIXEL-PERFECT WEBSITE ANALYSIS

Analyze this screenshot with extreme precision to create a pixel-perfect clone specification. Focus on exact positioning, spacing, colors, and typography.

HTML CONTENT (if available):
{html_content[:2000] if html_content else "No HTML content provided"}

ANALYSIS REQUIREMENTS:

1. VISUAL STRUCTURE ANALYSIS:
   - Identify ALL visual elements and their exact positions
   - Measure margins, padding, and spacing between elements
   - Detect layout patterns (grid, flexbox, absolute positioning)
   - Note element dimensions and aspect ratios

2. DYNAMIC COMPONENT DETECTION:
   - Automatically identify distinct UI sections (don't assume header/footer)
   - Detect repeating patterns that should be components
   - Identify interactive elements (buttons, forms, navigation)
   - Map content areas to logical component boundaries

3. PRECISE STYLING EXTRACTION:
   - Extract exact colors (hex codes) from all elements
   - Identify typography (font families, sizes, weights, line heights)
   - Detect shadows, borders, gradients, and effects
   - Note responsive breakpoint indicators

4. CONTENT MAPPING:
   - Extract ALL visible text with exact positioning
   - Identify image placeholders and their dimensions
   - Map icons and their styles
   - Note content hierarchy and relationships

5. LAYOUT MEASUREMENTS:
   - Container widths and max-widths
   - Element spacing (margins, padding) in pixels/rem
   - Grid/flexbox configurations
   - Responsive behavior indicators

Return a JSON object with this exact structure:

{{
  "viewport_analysis": {{
    "estimated_width": "1200px",
    "estimated_height": "800px",
    "device_type": "desktop|mobile|tablet",
    "responsive_indicators": []
  }},
  "visual_elements": [
    {{
      "id": "element_1",
      "type": "container|text|image|button|form",
      "position": {{"x": 0, "y": 0, "width": 100, "height": 50}},
      "styling": {{
        "background": "#ffffff",
        "color": "#000000",
        "font_family": "Arial, sans-serif",
        "font_size": "16px",
        "font_weight": "400",
        "padding": "10px 20px",
        "margin": "0 0 10px 0",
        "border": "1px solid #cccccc",
        "border_radius": "4px",
        "box_shadow": "none"
      }},
      "content": "Exact text content or description",
      "children": []
    }}
  ],
  "dynamic_components": {{
    "detected_sections": [
      {{
        "name": "navigation_area",
        "elements": ["element_1", "element_2"],
        "suggested_component": "Navigation.tsx",
        "props_needed": ["items", "activeItem"],
        "styling_classes": ["nav-container", "nav-item"]
      }}
    ]
  }},
  "layout_system": {{
    "type": "css_grid|flexbox|absolute|float",
    "container_structure": {{
      "max_width": "1200px",
      "margin": "0 auto",
      "padding": "0 20px",
      "display": "grid|flex|block",
      "grid_template": "1fr / 200px 1fr 200px",
      "gap": "20px"
    }},
    "breakpoints": {{
      "mobile": "768px",
      "tablet": "1024px",
      "desktop": "1200px"
    }}
  }},
  "color_palette": {{
    "primary": "#2563eb",
    "secondary": "#64748b",
    "accent": "#0ea5e9",
    "background": "#ffffff",
    "text_primary": "#1e293b",
    "text_secondary": "#475569",
    "borders": "#e2e8f0",
    "extracted_colors": ["#2563eb", "#64748b", "#0ea5e9", "#ffffff", "#1e293b"]
  }},
  "typography_system": {{
    "font_families": ["Inter", "system-ui", "sans-serif"],
    "font_sizes": {{
      "xs": "12px",
      "sm": "14px",
      "base": "16px",
      "lg": "18px",
      "xl": "20px",
      "2xl": "24px",
      "3xl": "30px"
    }},
    "font_weights": {{
      "light": 300,
      "normal": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700
    }},
    "line_heights": {{
      "tight": "1.25",
      "normal": "1.5",
      "relaxed": "1.75"
    }}
  }},
  "spacing_system": {{
    "base_unit": "4px",
    "scale": ["2px", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "40px", "48px"],
    "common_margins": ["8px", "16px", "24px"],
    "common_paddings": ["12px", "16px", "20px"]
  }},
  "next_js_implementation": {{
    "app_structure": [
      "app/layout.tsx",
      "app/page.tsx",
      "components/[DynamicComponentName].tsx"
    ],
    "component_mapping": {{
      "components/Navigation.tsx": {{
        "elements": ["element_1", "element_2"],
        "props": ["items: NavigationItem[]"],
        "styling": "Tailwind classes or CSS modules",
        "content": "Extracted navigation text and links"
      }}
    }},
    "css_approach": "tailwind|css_modules|styled_components",
    "required_packages": ["next", "react", "react-dom"],
    "config_files": {{
      "tailwind.config.js": {{}},
      "next.config.js": {{}}
    }}
  }}
}}

CRITICAL REQUIREMENTS:
- Do NOT assume standard components like "Header" or "Footer"
- Generate component names based on actual visual analysis
- Provide exact measurements and styling values
- Extract ALL visible text content
- Map every visual element to its precise position and styling
- Return ONLY valid JSON without markdown formatting
- ALWAYS include complete color_palette, typography_system, and spacing_system objects
"""

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured analysis"""
        try:
            # Clean response text
            response_text = response_text.strip()
            
            # Try to parse as JSON first
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Extract JSON from response text if wrapped in markdown
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    # Clean up common JSON formatting issues
                    json_str = re.sub(r'```json\s*', '', json_str)
                    json_str = re.sub(r'\s*```', '', json_str)
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in response")
            
            # Validate structure
            if not isinstance(analysis, dict):
                raise ValueError("Response is not a valid JSON object")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to parse Gemini response: {str(e)}")
            self.logger.info("Response text preview:", response_text[:500])
            # Return fallback structure instead of raising
            return self._get_fallback_analysis("")

    def _generate_dynamic_components(self, analysis: Dict) -> Dict:
        """Generate dynamic components based on analysis and transform data for generator compatibility"""
        # Generator expects 'colors' but analyzer provides 'color_palette'
        if "color_palette" in analysis and "colors" not in analysis:
            color_palette = analysis["color_palette"]
            analysis["colors"] = {
                "primary": color_palette.get("primary"),
                "secondary": color_palette.get("secondary"),
                "accent": color_palette.get("accent"),
                "background": color_palette.get("background"),
                "text": color_palette.get("text_primary"),  # Map text_primary to text for generator
                "text_primary": color_palette.get("text_primary"),
                "text_secondary": color_palette.get("text_secondary"),
                "borders": color_palette.get("borders")
            }
        
        # Generator expects 'typography' but analyzer provides 'typography_system'
        # Also need to map font_families to primary_font
        if "typography_system" in analysis and "typography" not in analysis:
            typography_system = analysis["typography_system"]
            analysis["typography"] = {
                "primary_font": typography_system.get("font_families", ["Inter"])[0] if typography_system.get("font_families") else "Inter",
                "font_families": typography_system.get("font_families", ["Inter", "system-ui", "sans-serif"]),
                "font_sizes": typography_system.get("font_sizes", {}),
                "font_weights": typography_system.get("font_weights", {}),
                "line_heights": typography_system.get("line_heights", {})
            }
        
        # Extract sections from visual analysis
        visual_elements = analysis.get("visual_elements", [])
        dynamic_components = analysis.get("dynamic_components", {})
        detected_sections = dynamic_components.get("detected_sections", [])
        
        if not detected_sections:
            self.logger.warning("No sections detected in analysis, creating default sections")
            detected_sections = [
                {
                    "name": "Header",
                    "elements": [],
                    "suggested_component": "Header.tsx"
                },
                {
                    "name": "Main",
                    "elements": [],
                    "suggested_component": "Main.tsx"
                },
                {
                    "name": "Footer", 
                    "elements": [],
                    "suggested_component": "Footer.tsx"
                }
            ]
        
        # Generate enhanced component specifications
        enhanced_components = []
        component_files = []
        components_description = {}
        text_content = {}
        pages_description = {
            "app/page.tsx": "Main page component with dynamic content",
            "app/layout.tsx": "Root layout with typography and global styles"
        }
        
        for i, section in enumerate(detected_sections):
            section_name = section.get("name", f"Section{i+1}")
            component_name = section.get("suggested_component", f"{section_name}.tsx")
            
            # Ensure component name is valid
            if not component_name.endswith(('.tsx', '.jsx')):
                component_name = f"{component_name}.tsx"
            
            # Create component specification
            component_spec = {
                "name": section_name,
                "file": f"components/{component_name}",
                "type": "react",
                "content": self._generate_component_code(section, analysis),
                "dependencies": ["react"],
                "props": {},
                "styling": "tailwind"
            }
            
            enhanced_components.append(component_spec)
            component_files.append(component_spec["file"])
            
            # Extract content for this component
            section_elements = section.get("elements", [])
            visual_elements = analysis.get("visual_elements", [])
            component_text = []
            
            for element_id in section_elements:
                element = next((elem for elem in visual_elements if elem.get("id") == element_id), None)
                if element and element.get("content"):
                    component_text.append(element["content"])
            
            # Build descriptions for orchestrator compatibility
            components_description[component_spec["file"]] = f"Dynamic {section_name} component with content: {'; '.join(component_text[:3])}"
            text_content[component_spec["file"]] = "; ".join(component_text)
        
        # Update analysis with enhanced component information
        analysis["generated_components"] = enhanced_components
        
        # Add backward compatibility fields for WebsiteCloneOrchestrator
        analysis["components"] = component_files
        analysis["content_structure"] = {
            "sections": [comp["name"] for comp in enhanced_components],
            "text_hierarchy": ["h1", "h2", "h3", "p"],
            "text_content": text_content,
            "images": self._extract_image_info(analysis),
            "icons": ["detected", "from", "analysis"]
        }
        analysis["cloning_requirements"] = {
            "npm_packages": ["next", "react", "react-dom", "@types/react", "@types/node", "typescript"],
            "component_files": component_files,
            "components_description": components_description,
            "pages": ["app/page.tsx", "app/layout.tsx"],
            "pages_description": pages_description,
            "styles": ["app/globals.css", "components/styles.module.css"],
            "styles_description": {
                "app/globals.css": f"Global styles with color palette: {', '.join(analysis.get('color_palette', {}).keys())}",
                "components/styles.module.css": "Component-specific styles based on visual analysis"
            },
            "config_files": {
                "next.config.js": {},
                "tailwind.config.js": self._generate_tailwind_config(analysis),
                "tsconfig.json": {}
            },
            "assets": ["public/images/", "public/icons/"],
            "performance_tips": ["lazy-loading", "code-splitting", "image-optimization"],
            "package_json": {
                "name": "pixel-perfect-clone",
                "version": "1.0.0", 
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint"
                },
                "dependencies": {
                    "next": "14",
                    "react": "^18",
                    "react-dom": "^18"
                },
                "devDependencies": {
                    "@types/node": "^20",
                    "@types/react": "^18",
                    "@types/react-dom": "^18",
                    "typescript": "^5"
                }
            }
        }
        
        return analysis

    def _generate_component_code(self, section: Dict, analysis: Dict) -> str:
        """Generate actual React component code based on analysis"""
        component_name = section.get("suggested_component", "Component").replace(".tsx", "").replace(".jsx", "")
        elements = section.get("elements", [])
        
        # Find styling information for elements
        visual_elements = analysis.get("visual_elements", [])
        section_elements = [elem for elem in visual_elements if elem.get("id") in elements]
        
        # Generate basic component structure
        code = f"""'use client';

import React from 'react';

interface {component_name}Props {{
  // Props will be defined based on analysis
}}

export default function {component_name}(props: {component_name}Props) {{
  return (
    <div className="component-{section.get('name', 'section')}">
      {{/* Component content will be generated based on visual analysis */}}
"""
        
        # Add elements based on analysis
        for element in section_elements:
            element_type = element.get("type", "div")
            content = element.get("content", "")
            
            if element_type == "text":
                code += f'      <p>{content}</p>\n'
            elif element_type == "button":
                code += f'      <button>{content}</button>\n'
            elif element_type == "container":
                code += f'      <div>{content}</div>\n'
        
        code += """    </div>
  );
}"""
        
        return code

    def _extract_image_info(self, analysis: Dict) -> List[str]:
        """Extract image information from visual elements"""
        visual_elements = analysis.get("visual_elements", [])
        images = []
        
        for element in visual_elements:
            if element.get("type") == "image":
                images.append(element.get("content", "image"))
        
        return images if images else ["hero-image", "thumbnails", "icons"]
    
    def _generate_tailwind_config(self, analysis: Dict) -> Dict:
        """Generate Tailwind config based on analysis with safe defaults"""
        # Ensure we have validated analysis with all required fields
        color_palette = analysis.get("color_palette", {})
        typography = analysis.get("typography_system", {})
        spacing = analysis.get("spacing_system", {})
        
        # Safe color extraction with fallbacks
        colors = {
            "primary": color_palette.get("primary", "#2563eb"),
            "secondary": color_palette.get("secondary", "#64748b"),
            "accent": color_palette.get("accent", "#0ea5e9"),
            "background": color_palette.get("background", "#ffffff"),
            "text": {
                "primary": color_palette.get("text_primary", "#1e293b"),
                "secondary": color_palette.get("text_secondary", "#475569")
            },
            "border": color_palette.get("borders", "#e2e8f0")
        }
        
        # Safe typography extraction with fallbacks
        font_families = typography.get("font_families", ["Inter", "system-ui", "sans-serif"])
        font_sizes = typography.get("font_sizes", {
            "xs": "12px", "sm": "14px", "base": "16px", "lg": "18px", 
            "xl": "20px", "2xl": "24px", "3xl": "30px"
        })
        
        # Safe spacing extraction with fallbacks
        spacing_scale = spacing.get("scale", ["4px", "8px", "12px", "16px", "20px", "24px", "32px", "40px"])
        spacing_dict = {}
        for i, size in enumerate(spacing_scale):
            spacing_dict[str(i + 1)] = size
        
        return {
            "content": [
                "./pages/**/*.{js,ts,jsx,tsx,mdx}",
                "./components/**/*.{js,ts,jsx,tsx,mdx}",
                "./app/**/*.{js,ts,jsx,tsx,mdx}"
            ],
            "theme": {
                "extend": {
                    "colors": colors,
                    "fontFamily": {
                        "primary": font_families if isinstance(font_families, list) else [font_families]
                    },
                    "fontSize": font_sizes,
                    "spacing": spacing_dict
                }
            },
            "plugins": []
        }

    def get_analysis_summary(self, analysis: Dict) -> str:
        """Generate a human-readable summary of the analysis"""
        summary = "PIXEL-PERFECT ANALYSIS SUMMARY:\n\n"
        
        # Viewport info
        viewport = analysis.get("viewport_analysis", {})
        summary += f"Viewport: {viewport.get('estimated_width', 'unknown')} x {viewport.get('estimated_height', 'unknown')}\n"
        summary += f"Device Type: {viewport.get('device_type', 'unknown')}\n\n"
        
        # Components detected
        components = analysis.get("generated_components", [])
        summary += f"Dynamic Components Detected: {len(components)}\n"
        for comp in components:
            summary += f"  - {comp.get('name', 'Unknown')}: {comp.get('file', 'Unknown file')}\n"
        
        # Colors
        colors = analysis.get("colors", {})
        summary += f"\nColor Palette:\n"
        for color_name, color_value in colors.items():
            if color_name != "extracted_colors":
                summary += f"  - {color_name}: {color_value}\n"
        
        # Layout
        layout = analysis.get("layout_system", {})
        summary += f"\nLayout System: {layout.get('type', 'unknown')}\n"
        return summary