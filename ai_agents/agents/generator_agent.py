from config.system_config import SystemConfig
from pathlib import Path
import logging
import google.generativeai as genai
import json
from typing import Dict, List
import asyncio
import os
from tqdm.auto import tqdm
import re

class DCGenGenerator:
    """Dynamic DCGen generator that creates entire project structures using AI prompts"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        
        if not hasattr(config, 'gemini_api_key') or not config.gemini_api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=config.gemini_api_key)
        self.model = self._initialize_gemini_model()
        
        if not self.model:
            raise ValueError("No suitable Gemini model available")

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    def _initialize_gemini_model(self):
        model_options = ['gemini-2.0-flash-exp', 'gemini-2.0-flash', 'gemini-1.5-flash']
        for model_name in model_options:
            try:
                model = genai.GenerativeModel(model_name)
                self.logger.info(f"Initialized {model_name}")
                return model
            except Exception as e:
                self.logger.warning(f"Failed to initialize {model_name}: {e}")
                continue
        raise ValueError("Failed to initialize any Gemini model")

    async def generate_dcgen_website(self, analysis: Dict, output_dir: str) -> Dict:
        """Generate complete Next.js project structure dynamically"""
        self.logger.info(f"Starting dynamic DCGen generation for: {output_dir}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate project structure and files dynamically
        project_structure = await self._generate_project_structure(analysis)
        generated_files = await self._generate_all_files(analysis, project_structure)
        
        # Write files to disk
        await self._write_files(generated_files, output_path)
        
        return {
            "status": "success",
            "output_directory": str(output_path),
            "generated_files": list(generated_files.keys()),
            "total_files": len(generated_files)
        }

    async def _generate_project_structure(self, analysis: Dict) -> Dict:
        """Dynamically generate the complete project structure"""
        dcgen_data = analysis.get('dcgen_analysis', {})
        segments = dcgen_data.get('all_segments', {})
        
        prompt = f"""
        Generate a complete Next.js 14 project structure for a website based on DCGen analysis.
        
        ANALYSIS DATA:
        - Total segments: {len(segments)}
        - Segments: {list(segments.keys())[:5]}... (showing first 5)
        - Has hierarchical structure: {bool(dcgen_data.get('root_segment'))}
        
        Create a JSON structure defining:
        1. All files needed (components, pages, styles, config)
        2. Component hierarchy and relationships
        3. Dependencies and packages needed
        
        REQUIREMENTS:
        - Use Next.js 14 app router structure
        - Create components for each segment
        - Include all necessary config files
        - Use TypeScript if analysis suggests complex structure
        - Include proper styling approach (Tailwind CSS)
        
        Return ONLY a JSON object with this structure:
        {{
            "files": {{
                "app/page.tsx": {{"type": "page", "imports": ["Component1", "Component2"]}},
                "app/layout.tsx": {{"type": "layout"}},
                "components/Component1.tsx": {{"type": "component", "segment_id": "segment_1"}},
                "package.json": {{"type": "config"}},
                "tailwind.config.js": {{"type": "config"}}
            }},
            "dependencies": ["next", "react", "react-dom", "tailwindcss"],
            "file_order": ["package.json", "tailwind.config.js", "app/layout.tsx", "components/...", "app/page.tsx"]
        }}
        """
        
        response = await self.model.generate_content_async(prompt)
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse project structure JSON: {e}")
            raise ValueError(f"Invalid JSON response: {e}")

    async def _generate_all_files(self, analysis: Dict, project_structure: Dict) -> Dict[str, str]:
        """Generate all project files dynamically"""
        files = project_structure.get('files', {})
        dcgen_data = analysis.get('dcgen_analysis', {})
        segments = dcgen_data.get('all_segments', {})
        
        generated_files = {}
        
        # Process files in the specified order
        file_order = project_structure.get('file_order', list(files.keys()))
        
        for file_path in tqdm(file_order, desc="Generating files"):
            if file_path not in files:
                continue
                
            file_info = files[file_path]
            file_type = file_info.get('type')
            
            if file_type == 'config':
                content = await self._generate_config_file(file_path, project_structure)
            elif file_type == 'layout':
                content = await self._generate_layout_file(analysis)
            elif file_type == 'page':
                content = await self._generate_page_file(analysis, file_info, generated_files)
            elif file_type == 'component':
                segment_id = file_info.get('segment_id')
                segment_data = segments.get(segment_id, {})
                content = await self._generate_component_file(file_path, segment_data, segments)
            else:
                content = await self._generate_generic_file(file_path, analysis, file_info)
            
            generated_files[file_path] = content
        
        return generated_files

    async def _generate_config_file(self, file_path: str, project_structure: Dict) -> str:
        """Generate configuration files dynamically"""
        dependencies = project_structure.get('dependencies', [])
        
        if file_path == 'package.json':
            prompt = f"""
            Generate a package.json for a Next.js 14 project with these dependencies: {dependencies}
            
            Include:
            - Proper scripts (dev, build, start, lint)
            - All required dependencies and devDependencies
            - TypeScript if needed
            
            Return ONLY the JSON content, no markdown formatting.
            """
        elif file_path == 'tailwind.config.js':
            prompt = """
            Generate a tailwind.config.js for a Next.js 14 app router project.
            Include proper content paths and any useful extensions.
            Return ONLY the JavaScript code.
            """
        elif file_path == 'next.config.js':
            prompt = """
            Generate a next.config.js for a Next.js 14 project.
            Include image domains and any optimizations.
            Return ONLY the JavaScript code.
            """
        else:
            prompt = f"Generate the content for {file_path} configuration file for a Next.js 14 project."
        
        response = await self.model.generate_content_async(prompt)
        return self._extract_code(response.text)

    async def _generate_layout_file(self, analysis: Dict) -> str:
        """Generate root layout file"""
        colors = analysis.get('colors', {})
        fonts = analysis.get('typography', {})
        
        prompt = f"""
        Generate a Next.js 14 app router layout.tsx file.
        
        STYLING INFO:
        - Primary colors: {colors}
        - Typography: {fonts}
        
        REQUIREMENTS:
        - Import global CSS
        - Include proper metadata
        - Use TypeScript
        - Include proper HTML structure
        - Add font loading if needed
        
        Return ONLY the TypeScript code, no markdown.
        """
        
        response = await self.model.generate_content_async(prompt)
        return self._extract_code(response.text)

    async def _generate_page_file(self, analysis: Dict, file_info: Dict, existing_files: Dict) -> str:
        """Generate main page file"""
        imports = file_info.get('imports', [])
        dcgen_data = analysis.get('dcgen_analysis', {})
        
        prompt = f"""
        Generate a Next.js 14 app router page.tsx file.
        
        REQUIREMENTS:
        - Import and use these components: {imports}
        - Create a responsive layout
        - Use TypeScript
        - Include proper SEO metadata export
        - Structure components based on DCGen analysis: {len(dcgen_data.get('all_segments', {}))} segments
        
        Return ONLY the TypeScript code, no markdown.
        """
        
        response = await self.model.generate_content_async(prompt)
        return self._extract_code(response.text)

    async def _generate_component_file(self, file_path: str, segment_data: Dict, all_segments: Dict) -> str:
        """Generate individual component files"""
        component_name = Path(file_path).stem
        children = segment_data.get('children', [])
        
        prompt = f"""
        Generate a Next.js 14 React component: {component_name}
        
        SEGMENT DATA:
        - Text content: {segment_data.get('text_content', '')}
        - Tailwind classes: {segment_data.get('tailwind_classes', '')}
        - Colors: {segment_data.get('colors', {})}
        - Position: {segment_data.get('position', {})}
        - Children components: {children}
        
        REQUIREMENTS:
        - Use TypeScript
        - Import child components if any: {children}
        - Apply provided styling
        - Make responsive
        - Export as default
        
        Return ONLY the TypeScript code, no markdown.
        """
        
        response = await self.model.generate_content_async(prompt)
        return self._extract_code(response.text)

    async def _generate_generic_file(self, file_path: str, analysis: Dict, file_info: Dict) -> str:
        """Generate any other files needed"""
        if file_path.endswith('.css'):
            prompt = f"""
            Generate CSS content for {file_path} based on this analysis: {analysis.get('colors', {})}
            Include Tailwind imports and custom styles.
            Return ONLY the CSS code.
            """
        elif file_path.endswith('.md'):
            prompt = f"""
            Generate a README.md for a Next.js project created from DCGen analysis.
            Include setup instructions and project description.
            Return ONLY the markdown content.
            """
        else:
            prompt = f"Generate appropriate content for {file_path} in a Next.js 14 project."
        
        response = await self.model.generate_content_async(prompt)
        return self._extract_code(response.text)

    async def _write_files(self, files: Dict[str, str], output_path: Path):
        """Write all generated files to disk"""
        for file_path, content in files.items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"Written: {full_path}")

    def _extract_code(self, response_text: str) -> str:
        """Extract code from AI response, removing markdown formatting"""
        # Remove code blocks
        code_block_pattern = r'```(?:\w+)?\n?(.*?)\n?```'
        match = re.search(code_block_pattern, response_text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return response_text.strip()

    # Sync wrapper
    async def generate_website(self, analysis: Dict, output_dir: str) -> Dict:
        return await self.generate_dcgen_website(analysis, output_dir)
    def generate_website_sync(self, analysis: Dict, output_dir: str) -> Dict:
        """Synchronous wrapper"""
        return asyncio.run(self.generate_dcgen_website(analysis, output_dir))

# Compatibility alias
class GeneratorAgent(DCGenGenerator):
    pass