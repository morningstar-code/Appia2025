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
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            generated_files = await self._generate_project_files(analysis, output_path)
            
            if not generated_files:
                raise ValueError("No files were generated")
            
            artifact_ids = {}
            for file_path, content in generated_files.items():
                full_path = output_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"Generated file: {full_path}")
                
                try:
                    artifact_part = Part.from_text(content)
                    revision_id = await self.artifact_service.save_artifact(
                        app_name="generator_app",
                        user_id="user_generator", 
                        session_id="session_generator",
                        filename=file_path,
                        artifact=artifact_part
                    )
                    artifact_ids[file_path] = revision_id
                    self.logger.info(f"Artifact saved for {file_path} with revision ID: {revision_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to save artifact for {file_path}: {e}")
            
            result = {
                "status": "success",
                "generated_files": list(generated_files.keys()),
                "artifact_ids": artifact_ids,
                "output_directory": str(output_path.absolute())
            }
            
            self.logger.info(f"Next.js website generation completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Website generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "generated_files": [],
                "artifact_ids": {},
                "output_directory": output_dir
            }

    async def _generate_project_files(self, analysis: Dict, output_path: Path) -> Dict[str, str]:
        prompt = self._create_bolt_style_prompt(analysis)
        
        try:
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
            
            self.logger.info("Received response from Gemini, parsing files...")
            
            files = self._parse_gemini_response(response.text)
            
            if not files:
                raise ValueError("No files parsed from Gemini response")
            
            generated_files = {}
            for file_path, content in files.items():
                clean_path = self._clean_file_path(file_path)
                generated_files[clean_path] = content
                
                if clean_path == "package.json":
                    generated_files[clean_path] = self._enhance_package_json(
                        content, 
                        analysis.get("cloning_requirements", {}).get("package_json", {})
                    )
            
            generated_files = self._ensure_critical_nextjs_files(generated_files, analysis)
            
            return generated_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate project files: {str(e)}")
            raise

    def _create_bolt_style_prompt(self, analysis: Dict) -> str:
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        components = analysis.get("components", [])
        content_structure = analysis.get("content_structure", {})
        cloning_requirements = analysis.get("cloning_requirements", {})
        interactive_elements = analysis.get("interactive_elements", {})
        
        base_instruction = """For all designs I create, make them beautiful, not cookie cutter. Make webpages that are fully featured and worthy for production.

By default, this template supports JSX syntax with Tailwind CSS classes, React hooks, and Lucide React for icons. Do not install other packages for UI themes, icons, etc unless absolutely necessary.

Use icons from lucide-react for logos.

Use stock photos from unsplash where appropriate, only valid URLs you know exist. Do not download the images, only link to them in image tags."""

        return f"""{base_instruction}

You are an expert AI assistant and exceptional senior software developer. Generate a complete, production-ready Next.js 14 website using the App Router based on the provided analysis.

SYSTEM CONSTRAINTS:
- Use Next.js 14 with App Router (app/ directory structure)
- Use Tailwind CSS for styling
- Use lucide-react for icons
- Use React Server Components by default, add "use client" only for interactive components
- Use 2-space indentation for all code
- Generate clean, maintainable, modular code
- Split functionality into reusable components

WEBSITE SPECIFICATIONS:

Colors:
- Primary: {colors.get('primary', '#3b82f6')}
- Secondary: {colors.get('secondary', '#64748b')}
- Accent: {colors.get('accent', '#10b981')}
- Background: {colors.get('background', '#ffffff')}
- Text: {colors.get('text', '#111827')}

Typography:
- Primary Font: {typography.get('primary_font', 'Inter')}
- Font Sizes: {json.dumps(typography.get('font_sizes', ['text-sm', 'text-base', 'text-lg', 'text-xl']))}
- Font Weights: {json.dumps(typography.get('font_weights', ['font-normal', 'font-medium', 'font-semibold', 'font-bold']))}

Components Required: {json.dumps(components)}

Content Structure:
- Sections: {json.dumps(content_structure.get('sections', []))}
- Text Content: {json.dumps(content_structure.get('text_content', {}))}
- Images: {json.dumps(content_structure.get('images', []))}

Interactive Elements:
- Navigation: {json.dumps(interactive_elements.get('navigation', []))}
- Buttons: {json.dumps(interactive_elements.get('buttons', []))}
- Forms: {json.dumps(interactive_elements.get('forms', []))}
- Animations: {json.dumps(interactive_elements.get('animations', []))}

Requirements:
- NPM Packages: {json.dumps(cloning_requirements.get('npm_packages', ['next', 'react', 'react-dom', 'lucide-react']))}
- Pages: {json.dumps(cloning_requirements.get('pages', ['Home']))}

INSTRUCTIONS:
1. Generate a complete Next.js 14 project with App Router
2. Create app/layout.jsx, app/page.jsx, and all necessary component files as specified in the Components Required section
3. Include package.json with all required dependencies
4. Include next.config.js and tailwind.config.js
5. Use the specified colors and typography throughout
6. Implement all interactive elements with proper functionality
7. Use "use client" directive only for components that need interactivity
8. Create responsive, mobile-first design
9. Use semantic HTML and proper accessibility attributes
10. Generate app/globals.css with Tailwind directives

CRITICAL: Return the output as a valid JSON object with file paths as keys and complete file contents as values. Do not use any placeholders or incomplete code.

OUTPUT FORMAT:
{{
  "package.json": "complete package.json content...",
  "next.config.js": "complete next.config.js content...",
  "tailwind.config.js": "complete tailwind.config.js content...",
  "app/layout.jsx": "complete layout component...",
  "app/page.jsx": "complete page component...",
  "app/globals.css": "complete global styles...",
  ... // Additional component files as specified in Components Required
}}

Generate the complete, functional Next.js 14 website now:"""

    def _parse_gemini_response(self, response_text: str) -> Dict[str, str]:
        try:
            clean_text = response_text.strip()
            
            if clean_text.startswith('```json'):
                start = clean_text.find('{')
                end = clean_text.rfind('}') + 1
                if start != -1 and end > start:
                    clean_text = clean_text[start:end]
            elif clean_text.startswith('```'):
                lines = clean_text.split('\n')
                json_lines = []
                in_json = False
                
                for line in lines:
                    if line.strip().startswith('```') and not in_json:
                        in_json = True
                        continue
                    elif line.strip().startswith('```') and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                
                clean_text = '\n'.join(json_lines)
            
            if not clean_text.startswith('{'):
                start = clean_text.find('{')
                end = clean_text.rfind('}') + 1
                if start != -1 and end > start:
                    clean_text = clean_text[start:end]
            
            if not clean_text:
                raise ValueError("Empty or invalid JSON response from Gemini")
            
            files = json.loads(clean_text)
            
            if not isinstance(files, dict):
                raise ValueError("Response is not a valid file structure JSON")
            
            self.logger.info(f"Successfully parsed {len(files)} files from response")
            return files
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse response as JSON: {e}")
            self.logger.debug(f"Response text (first 500 chars): {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing Gemini response: {e}")
            raise

    def _ensure_critical_nextjs_files(self, files: Dict[str, str], analysis: Dict) -> Dict[str, str]:
        critical_files = {
            'package.json': self._create_package_json(analysis),
            'next.config.js': self._create_next_config(),
            'postcss.config.js': self._create_postcss_config(),
            'tailwind.config.js': self._create_tailwind_config(analysis),
            'app/layout.jsx': self._create_layout_jsx(analysis),
            'app/page.jsx': self._create_page_jsx(analysis),
            'app/globals.css': self._create_globals_css(analysis)
        }
        
        for file_path, default_content in critical_files.items():
            if file_path not in files:
                files[file_path] = default_content
                self.logger.info(f"Added missing critical file: {file_path}")
        
        return files

    def _create_package_json(self, analysis: Dict) -> str:
        package_data = {
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
                "react-dom": "^18.2.0",
                "lucide-react": "^0.263.1"
            },
            "devDependencies": {
                "autoprefixer": "^10.4.16",
                "postcss": "^8.4.31",
                "tailwindcss": "^3.3.5"
            }
        }
        
        cloning_reqs = analysis.get("cloning_requirements", {})
        additional_packages = cloning_reqs.get("npm_packages", [])
        
        for package in additional_packages:
            if package not in package_data["dependencies"]:
                package_data["dependencies"][package] = "latest"
        
        return json.dumps(package_data, indent=2)

    def _create_next_config(self) -> str:
        return """/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['images.unsplash.com'],
  },
}

module.exports = nextConfig
"""

    def _create_postcss_config(self) -> str:
        """Create PostCSS configuration file for Tailwind CSS"""
        return """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

    def _create_tailwind_config(self, analysis: Dict) -> str:
        """Create Tailwind CSS configuration file"""
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        
        return """/** @type {import('tailwindcss').Config} */
module.exports = {{
  content: [
    './app/**/*.{{js,ts,jsx,tsx,mdx}}',
    './components/**/*.{{js,ts,jsx,tsx,mdx}}',
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: '{colors.get('primary', '#3b82f6')}',
        secondary: '{colors.get('secondary', '#64748b')}',
        accent: '{colors.get('accent', '#10b981')}',
        background: '{colors.get('background', '#ffffff')}',
        text: '{colors.get('text', '#111827')}',
      }},
      fontFamily: {{
        sans: ['{typography.get('primary_font', 'Inter')}', 'system-ui', 'sans-serif'],
      }},
      fontSize: {{
        'xs': '12px',
        'sm': '14px',
        'base': '16px',
        'lg': '18px',
        'xl': '24px',
        '2xl': '32px',
        '3xl': '48px',
      }},
      fontWeight: {{
        thin: 300,
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
      }},
    }},
  }},
  plugins: [],
}}
"""

    def _create_layout_jsx(self, analysis: Dict) -> str:
        return """import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Cloned Website',
  description: 'Generated by AI Website Cloner',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
"""

    def _create_page_jsx(self, analysis: Dict) -> str:
        components = analysis.get("components", [])
        component_imports = []
        component_jsx = []
        
        for component in components:
            if isinstance(component, dict) and "name" in component:
                component_name = component["name"]
                component_imports.append(f"import {component_name} from '../components/{component_name}'")
                component_jsx.append(f"<{component_name} />")
            elif isinstance(component, str):
                component_imports.append(f"import {component} from '../components/{component}'")
                component_jsx.append(f"<{component} />")
        
        imports_str = "\n".join(component_imports)
        components_str = "\n        ".join(component_jsx)
        
        return f"""{imports_str}

export default function Home() {{
  return (
    <div className="min-h-screen flex flex-col">
      {components_str}
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center mb-8">
          Welcome to Your Cloned Website
        </h1>
        <p className="text-lg text-center text-gray-600">
          This website was generated using AI technology.
        </p>
      </main>
    </div>
  )
}}
"""

    def _create_globals_css(self, analysis: Dict) -> str:
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        
        return f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --primary: {colors.get('primary', '#3b82f6')};
  --secondary: {colors.get('secondary', '#64748b')};
  --accent: {colors.get('accent', '#10b981')};
  --background: {colors.get('background', '#ffffff')};
  --text: {colors.get('text', '#111827')};
}}

body {{
  font-family: {typography.get('primary_font', 'Inter')}, system-ui, sans-serif;
  line-height: 1.6;
  color: var(--text);
  background-color: var(--background);
}}

.container {{
  max-width: 1200px;
  margin: 0 auto;
}}
"""

    def _clean_file_path(self, file_path: str) -> str:
        clean_path = file_path.strip().lstrip('/').replace('..', '').replace('~', '')
        
        if not Path(clean_path).suffix:
            if 'component' in clean_path.lower() or 'app/' in clean_path.lower():
                clean_path += '.jsx'
            elif 'css' in clean_path.lower():
                clean_path += '.css'
            elif 'config' in clean_path.lower():
                clean_path += '.js'
        
        return clean_path

    def _enhance_package_json(self, generated_content: str, analysis_package_json: Dict) -> str:
        try:
            package_data = json.loads(generated_content)
        except json.JSONDecodeError:
            self.logger.warning("Invalid package.json content, using default")
            return self._create_package_json({})
        
        package_data.setdefault("dependencies", {})
        package_data["dependencies"].update({
            "next": "14.0.0",
            "react": "^18.2.0", 
            "react-dom": "^18.2.0",
            "lucide-react": "^0.263.1"
        })
        
        if analysis_package_json.get("dependencies"):
            package_data["dependencies"].update(analysis_package_json["dependencies"])
        
        package_data.setdefault("scripts", {})
        package_data["scripts"].update({
            "dev": "next dev",
            "build": "next build", 
            "start": "next start"
        })
        
        return json.dumps(package_data, indent=2)

    async def batch_generate(self, analyses: List[Dict], output_base_dir: str):
        self.logger.info(f"Starting batch generation for {len(analyses)} analyses")
        results = []
        
        for i, analysis in enumerate(analyses):
            try:
                output_dir = os.path.join(output_base_dir, f"website_{i}")
                result = await self.generate_website(analysis, output_dir)
                result["batch_index"] = i
                results.append(result)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to generate website {i+1}: {str(e)}")
                results.append({
                    "status": "error",
                    "error": str(e),
                    "generated_files": [],
                    "artifact_ids": [],
                    "output_directory": os.path.join(output_base_dir, f"website_{i}"),
                    "batch_index": i
                })
        
        self.logger.info(f"Batch generation completed: {len(results)} results")
        return results

    def save_generation_result(self, result: Dict, output_path: str):
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            self.logger.info(f"Generation result saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save generation result: {e}")
            raise

    def __del__(self):
        try:
            if hasattr(self, 'logger'):
                self.logger.info("GeneratorAgent cleanup completed")
        except:
            pass