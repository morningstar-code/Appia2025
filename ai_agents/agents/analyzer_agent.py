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
import cv2
import numpy as np
from dataclasses import dataclass

@dataclass
class ImageSegment:
    """Represents a segment of the image with its boundaries and metadata"""
    x1: int
    y1: int
    x2: int
    y2: int
    depth: int
    parent: Optional['ImageSegment'] = None
    children: List['ImageSegment'] = None
    segment_id: str = ""
    image_data: np.ndarray = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if not self.segment_id:
            self.segment_id = f"segment_{self.depth}_{self.x1}_{self.y1}"

class DCGenAnalyzer:
    """DCGen-enhanced analyzer implementing divide-and-conquer image segmentation"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.artifact_service = InMemoryArtifactService()
        
        # DCGen parameters (optimized from paper)
        self.var_threshold = 50  # Variance threshold for blank areas
        self.diff_threshold = 30  # Brightness difference threshold
        self.portion_threshold = 0.3  # Minimum portion of row/col that must exceed diff_threshold
        self.window_size = 3  # Sliding window size for implicit line detection
        self.max_depth = 4  # Maximum recursion depth
        self.min_segment_size = 50  # Minimum segment size (pixels)
        
        # Initialize Gemini API
        if not hasattr(config, 'gemini_api_key') or not config.gemini_api_key:
            raise ValueError("Gemini API key is required for analysis")
        
        self.logger.info("Initializing Gemini API for DCGen analysis")
        genai.configure(api_key=config.gemini_api_key)
        self.model = self._initialize_gemini_model()
        
        if not self.model:
            raise RuntimeError("Failed to initialize Gemini model")

    def _setup_logger(self):
        """Setup logger similar to ScreenshotAgent"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    def _initialize_gemini_model(self):
        """Initialize Gemini model with fallback options"""
        model_options = [
            'gemini-2.0-flash-exp',
            'gemini-2.0-flash', 
            'gemini-1.5-pro',
            'gemini-pro-vision',
            'gemini-pro'
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

    def detect_separation_lines(self, img: np.ndarray, direction: str = 'horizontal') -> List[int]:
        """
        Detect separation lines using DCGen algorithm
        
        Args:
            img: Grayscale image as numpy array
            direction: 'horizontal' or 'vertical'
        
        Returns:
            List of line positions
        """
        if direction == 'vertical':
            img = img.T  # Transpose for vertical line detection
        
        lines = []
        height, width = img.shape
        
        for i in range(self.window_size + 1, height - 1):
            # Get upper row, current window, and lower row
            upper = img[i - self.window_size - 1]
            window = img[i - self.window_size:i]
            lower = img[i]
            
            # Calculate variance within the window
            var = np.var(window)
            is_blank = var < self.var_threshold
            
            # Check borders (top and bottom of window)
            diff_top = np.mean(np.abs(upper.astype(float) - window[0].astype(float)))
            diff_bottom = np.mean(np.abs(lower.astype(float) - window[-1].astype(float)))
            
            # Check if differences exceed threshold over enough portion
            diff_top_mask = np.abs(upper.astype(float) - window[0].astype(float)) > self.diff_threshold
            diff_bottom_mask = np.abs(lower.astype(float) - window[-1].astype(float)) > self.diff_threshold
            
            is_border_top = (diff_top > self.diff_threshold and 
                           np.sum(diff_top_mask) / width > self.portion_threshold)
            is_border_bottom = (diff_bottom > self.diff_threshold and 
                              np.sum(diff_bottom_mask) / width > self.portion_threshold)
            
            # Add separation line if conditions are met
            if is_blank and (is_border_top or is_border_bottom):
                if is_border_bottom:
                    pos = i
                else:
                    pos = i - self.window_size
                lines.append(pos)
        
        return sorted(list(set(lines)))  # Remove duplicates and sort

    def subdivide_screenshot(self, image: np.ndarray, segment: ImageSegment, 
                           current_depth: int = 0) -> List[ImageSegment]:
        """
        Recursively subdivide screenshot using DCGen algorithm
        
        Args:
            image: Full image as numpy array
            segment: Current segment to subdivide
            current_depth: Current recursion depth
        
        Returns:
            List of leaf segments (fully subdivided)
        """
        if current_depth >= self.max_depth:
            return [segment]
        
        # Extract segment from full image
        segment_img = image[segment.y1:segment.y2, segment.x1:segment.x2]
        
        # Check minimum size
        if segment_img.shape[0] < self.min_segment_size or segment_img.shape[1] < self.min_segment_size:
            return [segment]
        
        # Convert to grayscale if needed
        if len(segment_img.shape) == 3:
            gray_img = cv2.cvtColor(segment_img, cv2.COLOR_RGB2GRAY)
        else:
            gray_img = segment_img
        
        # Try horizontal division first
        horizontal_lines = self.detect_separation_lines(gray_img, 'horizontal')
        
        if horizontal_lines:
            # Create horizontal segments
            prev_y = 0
            children = []
            
            for line_y in horizontal_lines + [gray_img.shape[0]]:
                if line_y - prev_y > self.min_segment_size:
                    child_segment = ImageSegment(
                        x1=segment.x1,
                        y1=segment.y1 + prev_y,
                        x2=segment.x2,
                        y2=segment.y1 + line_y,
                        depth=current_depth + 1,
                        parent=segment
                    )
                    children.append(child_segment)
                prev_y = line_y
            
            # Recursively subdivide children
            all_leaves = []
            for child in children:
                segment.children.append(child)
                leaves = self.subdivide_screenshot(image, child, current_depth + 1)
                all_leaves.extend(leaves)
            
            return all_leaves
        
        # Try vertical division if no horizontal lines found
        vertical_lines = self.detect_separation_lines(gray_img, 'vertical')
        
        if vertical_lines:
            # Create vertical segments
            prev_x = 0
            children = []
            
            for line_x in vertical_lines + [gray_img.shape[1]]:
                if line_x - prev_x > self.min_segment_size:
                    child_segment = ImageSegment(
                        x1=segment.x1 + prev_x,
                        y1=segment.y1,
                        x2=segment.x1 + line_x,
                        y2=segment.y2,
                        depth=current_depth + 1,
                        parent=segment
                    )
                    children.append(child_segment)
                prev_x = line_x
            
            # Recursively subdivide children
            all_leaves = []
            for child in children:
                segment.children.append(child)
                leaves = self.subdivide_screenshot(image, child, current_depth + 1)
                all_leaves.extend(leaves)
            
            return all_leaves
        
        # No separation lines found - this is a leaf
        return [segment]

    async def analyze_leaf_segment(self, image: np.ndarray, segment: ImageSegment) -> Dict:
        """
        Analyze a leaf segment using MLLM (Leaf-solver MLLM from DCGen)
        
        Args:
            image: Full image
            segment: Leaf segment to analyze
        
        Returns:
            Analysis dict for the segment
        """
        # Extract segment image
        segment_img = image[segment.y1:segment.y2, segment.x1:segment.x2]
        
        # Convert to bytes for MLLM
        _, img_encoded = cv2.imencode('.png', segment_img)
        img_bytes = img_encoded.tobytes()
        
        # Create DCGen leaf analysis prompt
        prompt = f"""
        Analyze the provided screenshot segment of a webpage. Generate a JSON specification for a Next.js 14 component to reproduce this segment exactly. Use 'placeholder.png' for images. Focus on size, text, position, color, and layout, using Tailwind CSS classes. Return a valid JSON object.

        SEGMENT DETAILS:
        - Position: ({segment.x1}, {segment.y1}) to ({segment.x2}, {segment.y2})
        - Depth: {segment.depth}
        - Size: {segment.x2 - segment.x1}x{segment.y2 - segment.y1} pixels

        INSTRUCTIONS:
        1. Extract all visible text (headings, paragraphs, buttons).
        2. Map to a single Next.js component named 'components/Segment_{segment.depth}_{segment.x1}_{segment.y1}.jsx'.
        3. Identify design elements: layout (flexbox/grid), colors (hex codes), typography.
        4. Use Tailwind CSS classes for styling.

        OUTPUT FORMAT:
        {{
            "component": "components/Segment_{segment.depth}_{segment.x1}_{segment.y1}.jsx",
            "text_content": "Extracted text from segment",
            "layout": {{"type": "flexbox|grid", "structure": "single-column|multi-column"}},
            "colors": {{"background": "#hexcode", "text": "#hexcode"}},
            "typography": {{"font_family": "font-name", "font_size": "size", "font_weight": "weight"}},
            "tailwind_classes": "Tailwind CSS classes for the component",
            "position": {{"x": {segment.x1}, "y": {segment.y1}, "width": {segment.x2 - segment.x1}, "height": {segment.y2 - segment.y1}}},
            "segment_id": "{segment.segment_id}"
        }}
        """
        
        try:
            # Perform vision analysis
            image_part = {"mime_type": "image/png", "data": img_bytes}
            response = await self.model.generate_content_async([prompt, image_part])
            
            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini leaf analysis")
            
            analysis = self._parse_gemini_response(response.text)
            self.logger.info(f"Analyzed leaf segment {segment.segment_id}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze leaf segment {segment.segment_id}: {e}")
            # Return fallback analysis
            return {
                "component": f"components/Segment_{segment.depth}_{segment.x1}_{segment.y1}.jsx",
                "text_content": "Fallback content",
                "layout": {"type": "flexbox", "structure": "single-column"},
                "colors": {"background": "#ffffff", "text": "#000000"},
                "typography": {"font_family": "Inter", "font_size": "16px", "font_weight": "400"},
                "tailwind_classes": "flex flex-col p-4",
                "position": {"x": segment.x1, "y": segment.y1, "width": segment.x2 - segment.x1, "height": segment.y2 - segment.y1},
                "segment_id": segment.segment_id
            }

    async def assemble_segments(self, image: np.ndarray, segment: ImageSegment, 
                              child_analyses: List[Dict]) -> Dict:
        """
        Assemble analysis from child segments (Assembly MLLM from DCGen)
        
        Args:
            image: Full image
            segment: Parent segment
            child_analyses: Analyses from child segments
        
        Returns:
            Combined analysis for parent segment
        """
        # Extract segment image with bounding box
        segment_img = image[segment.y1:segment.y2, segment.x1:segment.x2]
        
        # Draw bounding box to show focus area
        img_with_box = image.copy()
        cv2.rectangle(img_with_box, (segment.x1, segment.y1), (segment.x2, segment.y2), (255, 0, 0), 3)
        
        _, img_encoded = cv2.imencode('.png', img_with_box)
        img_bytes = img_encoded.tobytes()
        
        # Create assembly prompt with child descriptions
        child_descriptions = "\n".join([
            f"Child {i+1} ({analysis['segment_id']}): {analysis['text_content']}"
            for i, analysis in enumerate(child_analyses)
        ])
        
        prompt = f"""
        Analyze the provided screenshot with red bounding box highlighting the focus area. Combine the descriptions from child segments to create a unified component specification.

        SEGMENT DETAILS:
        - Position: ({segment.x1}, {segment.y1}) to ({segment.x2}, {segment.y2})
        - Depth: {segment.depth}
        - Children: {len(child_analyses)}

        CHILD SEGMENTS DESCRIPTIONS:
        {child_descriptions}

        INSTRUCTIONS:
        1. Create a unified Next.js component that contains all child components.
        2. Determine the layout structure (flexbox/grid) that best represents the relationship between children.
        3. Extract any additional text or elements not captured by children.
        4. Maintain consistent styling and positioning.

        OUTPUT FORMAT:
        {{
            "component": "components/Segment_{segment.depth}_{segment.x1}_{segment.y1}.jsx",
            "text_content": "Combined text from all children and additional content",
            "layout": {{"type": "flexbox|grid", "structure": "description of layout"}},
            "colors": {{"background": "#hexcode", "text": "#hexcode"}},
            "typography": {{"font_family": "font-name", "font_size": "size", "font_weight": "weight"}},
            "tailwind_classes": "Tailwind CSS classes for the parent component",
            "children": {json.dumps([analysis['segment_id'] for analysis in child_analyses])},
            "position": {{"x": {segment.x1}, "y": {segment.y1}, "width": {segment.x2 - segment.x1}, "height": {segment.y2 - segment.y1}}},
            "segment_id": "{segment.segment_id}"
        }}
        """
        
        try:
            image_part = {"mime_type": "image/png", "data": img_bytes}
            response = await self.model.generate_content_async([prompt, image_part])
            
            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini assembly analysis")
            
            analysis = self._parse_gemini_response(response.text)
            self.logger.info(f"Assembled segment {segment.segment_id} from {len(child_analyses)} children")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to assemble segment {segment.segment_id}: {e}")
            # Return fallback assembly
            return {
                "component": f"components/Segment_{segment.depth}_{segment.x1}_{segment.y1}.jsx",
                "text_content": " ".join([analysis['text_content'] for analysis in child_analyses]),
                "layout": {"type": "flexbox", "structure": "vertical stack"},
                "colors": {"background": "#ffffff", "text": "#000000"},
                "typography": {"font_family": "Inter", "font_size": "16px", "font_weight": "400"},
                "tailwind_classes": "flex flex-col space-y-4",
                "children": [analysis['segment_id'] for analysis in child_analyses],
                "position": {"x": segment.x1, "y": segment.y1, "width": segment.x2 - segment.x1, "height": segment.y2 - segment.y1},
                "segment_id": segment.segment_id
            }

    async def analyze_screenshot_dcgen(self, image_path: str, html_content: str = "") -> Dict:
        """
        Main DCGen analysis method
        
        Args:
            image_path: Path to screenshot
            html_content: Optional HTML content
        
        Returns:
            Complete DCGen analysis
        """
        self.logger.info(f"Starting DCGen analysis for image: {image_path}")
        
        # Validate image file
        if not os.path.exists(image_path):
            self.logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]
        
        self.logger.info(f"Image loaded: {width}x{height} pixels")
        
        # Create root segment
        root_segment = ImageSegment(
            x1=0, y1=0, x2=width, y2=height, depth=0
        )
        
        # DIVISION STAGE: Subdivide screenshot
        self.logger.info("Starting division stage...")
        leaf_segments = self.subdivide_screenshot(image, root_segment)
        self.logger.info(f"Division complete: {len(leaf_segments)} leaf segments")
        
        # ASSEMBLY STAGE: Analyze segments bottom-up
        self.logger.info("Starting assembly stage...")
        segment_analyses = {}
        
        # Analyze all leaf segments first
        for leaf in leaf_segments:
            analysis = await self.analyze_leaf_segment(image, leaf)
            segment_analyses[leaf.segment_id] = analysis
        
        # Build tree and analyze parent segments bottom-up
        all_segments = self._collect_all_segments(root_segment)
        all_segments.sort(key=lambda s: s.depth, reverse=True)  # Process deepest first
        
        for segment in all_segments:
            if segment.segment_id in segment_analyses:
                continue  # Already analyzed (leaf)
            
            if segment.children:
                child_analyses = [segment_analyses[child.segment_id] for child in segment.children]
                analysis = await self.assemble_segments(image, segment, child_analyses)
                segment_analyses[segment.segment_id] = analysis
        
        # Generate final analysis structure
        root_analysis = segment_analyses[root_segment.segment_id]
        
        # Combine with traditional analysis structure
        final_analysis = {
            "dcgen_analysis": {
                "root_segment": root_analysis,
                "all_segments": segment_analyses,
                "leaf_segments": [s.segment_id for s in leaf_segments],
                "total_segments": len(segment_analyses)
            },
            "layout": self._extract_layout_from_dcgen(segment_analyses),
            "colors": self._extract_colors_from_dcgen(segment_analyses),
            "typography": self._extract_typography_from_dcgen(segment_analyses),
            "components": list(segment_analyses.keys()),
            "interactive_elements": self._extract_interactive_elements(segment_analyses),
            "content_structure": self._extract_content_structure(segment_analyses),
            "cloning_requirements": self._generate_cloning_requirements(segment_analyses)
        }
        
        self.logger.info("DCGen analysis completed successfully")
        return final_analysis

    def _collect_all_segments(self, segment: ImageSegment) -> List[ImageSegment]:
        """Collect all segments in the tree"""
        segments = [segment]
        for child in segment.children:
            segments.extend(self._collect_all_segments(child))
        return segments

    def _extract_layout_from_dcgen(self, segment_analyses: Dict) -> Dict:
        """Extract layout information from DCGen analysis"""
        layouts = [analysis.get('layout', {}) for analysis in segment_analyses.values()]
        layout_types = [l.get('type', 'flexbox') for l in layouts]
        
        return {
            "type": max(set(layout_types), key=layout_types.count) if layout_types else "flexbox",
            "structure": "dcgen-hierarchical",
            "breakpoints": ["sm:640px", "md:768px", "lg:1024px", "xl:1280px"],
            "component_hierarchy": list(segment_analyses.keys())
        }

    def _extract_colors_from_dcgen(self, segment_analyses: Dict) -> Dict:
        """Extract color palette from DCGen analysis"""
        all_colors = {}
        for analysis in segment_analyses.values():
            colors = analysis.get('colors', {})
            for key, value in colors.items():
                if key not in all_colors:
                    all_colors[key] = value
        
        return {
            "primary": all_colors.get('background', '#ffffff'),
            "secondary": all_colors.get('text', '#000000'),
            "accent": "#3b82f6",
            "background": all_colors.get('background', '#ffffff'),
            "text": all_colors.get('text', '#000000')
        }

    def _extract_typography_from_dcgen(self, segment_analyses: Dict) -> Dict:
        """Extract typography from DCGen analysis"""
        typography_data = [analysis.get('typography', {}) for analysis in segment_analyses.values()]
        font_families = [t.get('font_family', 'Inter') for t in typography_data]
        
        return {
            "primary_font": max(set(font_families), key=font_families.count) if font_families else "Inter",
            "font_sizes": ["12px", "14px", "16px", "18px", "24px"],
            "font_weights": [300, 400, 500, 600, 700],
            "line_heights": ["1.2", "1.4", "1.6"]
        }

    def _extract_interactive_elements(self, segment_analyses: Dict) -> Dict:
        """Extract interactive elements from DCGen analysis"""
        return {
            "navigation": ["dcgen-segments"],
            "buttons": ["primary", "secondary"],
            "forms": ["text-input", "select"],
            "animations": ["fade", "slide"]
        }

    def _extract_content_structure(self, segment_analyses: Dict) -> Dict:
        """Extract content structure from DCGen analysis"""
        text_content = {}
        for analysis in segment_analyses.values():
            component = analysis.get('component', 'unknown')
            text = analysis.get('text_content', '')
            if text:
                text_content[component] = text
        
        return {
            "sections": ["dcgen-segments"],
            "text_hierarchy": ["h1", "h2", "h3", "p"],
            "text_content": text_content,
            "images": ["placeholder.png"],
            "icons": ["custom"]
        }

    def _generate_cloning_requirements(self, segment_analyses: Dict) -> Dict:
        """Generate cloning requirements from DCGen analysis"""
        components = list(segment_analyses.keys())
        components_description = {}
        
        for analysis in segment_analyses.values():
            component = analysis.get('component', 'unknown')
            text = analysis.get('text_content', '')
            components_description[component] = f"DCGen segment with content: {text[:100]}..."
        
        return {
            "npm_packages": ["next", "react", "react-dom"],
            "component_files": components,
            "components_description": components_description,
            "pages": ["app/page.jsx", "app/layout.jsx"],
            "pages_description": {
                "app/page.jsx": "Main page combining all DCGen segments",
                "app/layout.jsx": "Root layout for DCGen components"
            },
            "styles": ["app/globals.css"],
            "styles_description": {
                "app/globals.css": "Global styles for DCGen components"
            },
            "config_files": {"next.config.js": {}, "package.json": {}},
            "assets": ["public/images/"],
            "performance_tips": ["lazy-loading", "code-splitting"],
            "package_json": {
                "name": "dcgen-cloned-website",
                "version": "1.0.0",
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
                "dependencies": {"next": "14", "react": "^18", "react-dom": "^18"},
                "devDependencies": {}
            }
        }

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured analysis"""
        try:
            # Try to parse as JSON first
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Extract JSON from response text if wrapped in markdown or other text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")

            # Validate that we have a proper dictionary
            if not isinstance(analysis, dict):
                raise ValueError("Response is not a valid JSON object")

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to parse Gemini response: {str(e)}")
            raise RuntimeError(f"Failed to parse analysis response: {str(e)}")

    # Maintain compatibility with original interface
    async def analyze_screenshot(self, image_path: str, html_content: str = "") -> Dict:
        """Main analysis method - now uses DCGen"""
        return await self.analyze_screenshot_dcgen(image_path, html_content)

    def analyze_screenshot_sync(self, image_path: str, html_content: str = "") -> Dict:
        """Synchronous version of DCGen analysis"""
        return asyncio.run(self.analyze_screenshot_dcgen(image_path, html_content))

# Maintain compatibility - alias the new class
class AnalyzerAgent(DCGenAnalyzer):
    """Compatibility alias for existing code"""
    pass