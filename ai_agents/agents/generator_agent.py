import json
import logging
import os
from pathlib import Path
from typing import Dict, List
import asyncio
import google.generativeai as genai
from config.system_config import SystemConfig
from google.adk.artifacts import InMemoryArtifactService
from google.genai.types import Part

class GeneratorAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.artifact_service = InMemoryArtifactService()
        
        if hasattr(config, 'gemini_api_key') and config.gemini_api_key:
            self.logger.info("Using Gemini API key for generation")
            genai.configure(api_key=config.gemini_api_key)
            self.model = self._initialize_gemini_model()
        else:
            self.model = None
            self.logger.error("No Gemini API key provided, cannot generate code")
            raise ValueError("Gemini API key is required for GeneratorAgent")

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    def _initialize_gemini_model(self):
        model_options = [
            'gemini-2.0-flash-exp',
            'gemini-2.0-flash', 
            'gemini-1.5-pro',
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
        raise ValueError("No suitable Gemini model available")

    async def generate_code(self, analysis: Dict, output_dir: str) -> Dict:
        return await self.generate_website(analysis, output_dir)

    async def generate_website(self, analysis: Dict, output_dir: str) -> Dict:
        self.logger.info(f"Starting Next.js website generation for output directory: {output_dir}")
        
        try:
            if not analysis or not isinstance(analysis, dict):
                self.logger.error("Invalid analysis provided")
                raise ValueError("Invalid analysis structure")
            
            # Generate complete Next.js project files
            generation_result = await self._generate_nextjs_files(analysis)
            
            if not generation_result:
                raise ValueError("No files were generated")
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Write all generated files to disk
            generated_files = []
            for file_path, content in generation_result.items():
                full_path = output_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                generated_files.append(str(full_path))
                self.logger.info(f"Generated file: {full_path}")
            
            # Save artifact for WebContainer deployment
            revision_id = None
            try:
                artifact_content = self._create_webcontainer_artifact(generation_result)
                artifact_part = Part(text=artifact_content)
                revision_id = await self.artifact_service.save_artifact(
                    app_name="generator_app",
                    user_id="user_generator", 
                    session_id="session_generator",
                    filename="nextjs_deployment.xml",
                    artifact=artifact_part
                )
                self.logger.info(f"Next.js artifact saved with revision ID: {revision_id}")
            except Exception as e:
                self.logger.error(f"Failed to save Next.js artifact: {e}")
                raise Exception(f"Failed to save Next.js artifact: {e}")
            
            result = {
                "status": "success",
                "generated_files": generated_files,
                "output_directory": str(output_path),
                "artifact_content": artifact_content,
                "artifact_id": revision_id,
                "deployment_type": "nextjs",
                "deployment_ready": True,
                "file_count": len(generated_files)
            }
            
            self.logger.info(f"Next.js website generated successfully with {len(generated_files)} files")
            return result
            
        except Exception as e:
            self.logger.error(f"Next.js website generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "generated_files": [],
                "output_directory": output_dir,
                "artifact_content": None,
                "artifact_id": None,
                "deployment_type": "nextjs",
                "deployment_ready": False
            }

    async def _generate_nextjs_files(self, analysis: Dict) -> Dict[str, str]:
        """Generate all required Next.js files based on analysis"""
        
        # Extract analysis data
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        components = analysis.get("components", [])
        content_structure = analysis.get("content_structure", {})
        cloning_requirements = analysis.get("cloning_requirements", {})
        interactive_elements = analysis.get("interactive_elements", {})
        
        if not colors and not typography and not components and not content_structure:
            raise ValueError("Analysis data is insufficient - missing colors, typography, components, and content structure")
        
        # Generate each required file
        files = {}
        
        # 1. package.json
        files["package.json"] = self._generate_package_json(cloning_requirements)
        
        # 2. next.config.js
        files["next.config.js"] = self._generate_next_config()
        
        # 3. tailwind.config.js
        files["tailwind.config.js"] = self._generate_tailwind_config(colors)
        
        # 4. postcss.config.js
        files["postcss.config.js"] = self._generate_postcss_config()
        
        # 5. app/layout.jsx
        files["app/layout.jsx"] = self._generate_layout_jsx(typography, colors)
        
        # 6. app/page.jsx - Generate with AI (NO FALLBACK)
        files["app/page.jsx"] = await self._generate_page_jsx_with_ai(analysis)
        
        # 7. app/globals.css
        files["app/globals.css"] = self._generate_globals_css(colors, typography)
        
        # 8. Additional component files if needed
        component_files = await self._generate_component_files(components, analysis)
        files.update(component_files)
        
        return files

    def _generate_package_json(self, cloning_requirements: Dict) -> str:
        npm_packages = cloning_requirements.get('npm_packages', [])
        
        # Ensure essential Next.js packages are included
        essential_packages = {
            "next": "^14.0.0",
            "react": "^18.0.0",
            "react-dom": "^18.0.0",
            "tailwindcss": "^3.0.0",
            "autoprefixer": "^10.0.0",
            "postcss": "^8.0.0",
            "lucide-react": "^0.263.1"
        }
        
        # Log what packages we're working with
        if not npm_packages:
            self.logger.info("No npm packages specified in analysis, using essential packages only")
        else:
            self.logger.info(f"Found {len(npm_packages)} npm packages in analysis: {npm_packages}")
        
        # Add any additional packages from requirements
        for package in npm_packages:
            if package not in essential_packages:
                essential_packages[package] = "latest"
                self.logger.info(f"Added additional package: {package}")
        
        # Log final package list
        self.logger.info(f"Final package.json will include {len(essential_packages)} packages")
        
        package_json = {
            "name": "generated-nextjs-website",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": essential_packages,
            "devDependencies": {
                "eslint": "^8.0.0",
                "eslint-config-next": "^14.0.0"
            }
        }
        
        return json.dumps(package_json, indent=2)

    def _generate_next_config(self) -> str:
        return """/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['images.unsplash.com', 'unsplash.com'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
  },
}

module.exports = nextConfig
"""

    def _generate_tailwind_config(self, colors: Dict) -> str:
        if not colors:
            raise ValueError("Cannot generate tailwind.config.js - no colors provided in analysis")
            
        primary = colors.get('primary')
        secondary = colors.get('secondary')
        accent = colors.get('accent')
        
        if not primary or not secondary or not accent:
            raise ValueError("Cannot generate tailwind.config.js - missing required colors (primary, secondary, accent)")
        
        return f"""/** @type {{import('tailwindcss').Config}} */
module.exports = {{
  content: [
    './pages/**/*.{{js,ts,jsx,tsx,mdx}}',
    './components/**/*.{{js,ts,jsx,tsx,mdx}}',
    './app/**/*.{{js,ts,jsx,tsx,mdx}}',
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: '{primary}',
        secondary: '{secondary}',
        accent: '{accent}',
      }},
      fontFamily: {{
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }},
    }},
  }},
  plugins: [],
}}
"""

    def _generate_postcss_config(self) -> str:
        return """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

    def _generate_layout_jsx(self, typography: Dict, colors: Dict) -> str:
        if not typography:
            raise ValueError("Cannot generate layout.jsx - no typography data provided in analysis")
            
        primary_font = typography.get('primary_font')
        if not primary_font:
            raise ValueError("Cannot generate layout.jsx - missing primary_font in typography data")
        
        font_import = primary_font.replace(' ', '_')
        
        return f"""import './globals.css'
import {{ {font_import} }} from 'next/font/google'

const font = {font_import}({{ subsets: ['latin'] }})

export const metadata = {{
  title: 'Generated Website',
  description: 'A beautiful website generated by AI',
}}

export default function RootLayout({{ children }}) {{
  return (
    <html lang="en">
      <body className={{font.className}}>
        {{children}}
      </body>
    </html>
  )
}}
"""

    def _generate_globals_css(self, colors: Dict, typography: Dict) -> str:
        if not colors:
            raise ValueError("Cannot generate globals.css - no colors provided in analysis")
            
        background = colors.get('background')
        text = colors.get('text')
        
        if not background or not text:
            raise ValueError("Cannot generate globals.css - missing background or text colors")
        
        return f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --background: {background};
  --foreground: {text};
}}

body {{
  color: var(--foreground);
  background: var(--background);
}}

@layer base {{
  * {{
    @apply border-border;
  }}
  body {{
    @apply bg-background text-foreground;
  }}
}}
"""

    async def _generate_page_jsx_with_ai(self, analysis: Dict) -> str:
        """Use AI to generate the main page.jsx content - NO FALLBACK"""
        prompt = self._create_page_generation_prompt(analysis)
        
        try:
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise Exception("AI model returned empty response for page.jsx generation")
            
            # Extract JSX code from response
            jsx_code = self._extract_jsx_from_response(response.text)
            
            if not jsx_code:
                raise Exception("Failed to extract valid JSX code from AI response")
                
            return jsx_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate page.jsx with AI: {str(e)}")
            raise Exception(f"Failed to generate page.jsx with AI: {str(e)}")

    def _create_page_generation_prompt(self, analysis: Dict) -> str:
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        components = analysis.get("components", [])
        content_structure = analysis.get("content_structure", {})
        
        if not colors and not typography and not components and not content_structure:
            raise ValueError("Cannot create generation prompt - analysis data is insufficient")
        
        return f"""Generate ONLY the JSX code for a Next.js app/page.jsx file. Do not include any explanations or markdown formatting.

Requirements:
- Use Next.js 14 App Router format
- Use Tailwind CSS classes
- Use lucide-react icons
- Make it responsive and modern
- Include proper semantic HTML

Colors: {json.dumps(colors)}
Typography: {json.dumps(typography)}
Components: {json.dumps(components)}
Content Structure: {json.dumps(content_structure)}

Return ONLY the complete JSX code for the page component, starting with imports and ending with the export statement."""

    def _extract_jsx_from_response(self, response_text: str) -> str:
        """Extract JSX code from AI response"""
        if not response_text or not response_text.strip():
            raise ValueError("AI response is empty or invalid")
            
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].startswith('```'):
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        # Validate that it contains JSX code
        if 'export default' not in response_text:
            raise ValueError("AI response does not contain valid JSX component")
        
        # Ensure it starts with proper imports
        if not response_text.strip().startswith('import') and not response_text.strip().startswith("'use client'"):
            response_text = "import React from 'react'\n" + response_text
        
        return response_text

    async def _generate_component_files(self, components: List, analysis: Dict) -> Dict[str, str]:
        """Generate additional component files if needed - NO FALLBACK"""
        files = {}
        
        if not components:
            self.logger.info("No components specified in analysis, skipping component file generation")
            return files
        
        # Generate components based on analysis only
        for component in components:
            if isinstance(component, dict):
                component_name = component.get('name', '').lower()
                component_type = component.get('type', '').lower()
                
                if 'navigation' in component_name or 'nav' in component_type:
                    files["components/Navigation.jsx"] = await self._generate_ai_component('Navigation', component, analysis)
                elif 'hero' in component_name or 'banner' in component_type:
                    files["components/Hero.jsx"] = await self._generate_ai_component('Hero', component, analysis)
                elif 'footer' in component_name:
                    files["components/Footer.jsx"] = await self._generate_ai_component('Footer', component, analysis)
        
        return files

    async def _generate_ai_component(self, component_name: str, component_data: Dict, analysis: Dict) -> str:
        """Generate component using AI - NO FALLBACK"""
        prompt = f"""Generate ONLY the JSX code for a React component named {component_name}.

Component Data: {json.dumps(component_data)}
Analysis Context: {json.dumps(analysis)}

Requirements:
- Use functional React component with hooks if needed
- Use Tailwind CSS classes
- Use lucide-react icons where appropriate
- Make it responsive and modern
- Include proper semantic HTML

Return ONLY the complete JSX code for the component."""

        try:
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise Exception(f"AI model returned empty response for {component_name} component generation")
            
            jsx_code = self._extract_jsx_from_response(response.text)
            
            if not jsx_code:
                raise Exception(f"Failed to extract valid JSX code from AI response for {component_name}")
                
            return jsx_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate {component_name} component with AI: {str(e)}")
            raise Exception(f"Failed to generate {component_name} component with AI: {str(e)}")

    def _create_webcontainer_artifact(self, files: Dict[str, str]) -> str:
        """Create WebContainer artifact for deployment"""
        if not files:
            raise ValueError("Cannot create WebContainer artifact - no files generated")
            
        file_actions = []
        
        for file_path, content in files.items():
            if not content or not content.strip():
                raise ValueError(f"File {file_path} has empty content - cannot create artifact")
            file_actions.append(f'<boltAction type="file" filePath="{file_path}">\n{content}\n</boltAction>')
        
        return f"""<boltArtifact id="nextjs-website" title="Next.js Website">
<boltAction type="shell">
npm install
</boltAction>

{''.join(file_actions)}

<boltAction type="shell">
npm run dev
</boltAction>
</boltArtifact>"""

    async def batch_generate(self, analyses: List[Dict], output_base_dir: str):
        self.logger.info(f"Starting batch Next.js generation for {len(analyses)} analyses")
        results = []
        
        for i, analysis in enumerate(analyses):
            try:
                output_dir = f"{output_base_dir}/project_{i}"
                result = await self.generate_website(analysis, output_dir)
                result["batch_index"] = i
                results.append(result)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to generate Next.js project {i+1}: {str(e)}")
                raise Exception(f"Failed to generate Next.js project {i+1}: {str(e)}")
        
        self.logger.info(f"Batch Next.js generation completed: {len(results)} results")
        return results

    def save_generation_result(self, result: Dict, output_path: str):
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            self.logger.info(f"Next.js generation result saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save Next.js generation result: {e}")
            raise

    def __del__(self):
        try:
            if hasattr(self, 'logger'):
                self.logger.info("GeneratorAgent cleanup completed")
        except:
            pass