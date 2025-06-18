from config.system_config import SystemConfig, CloneResult, GeneratedProject
from agents.explorer_agent import ExplorerAgent
from agents.screenshot_agent import ScreenshotAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.generator_agent import GeneratorAgent
from agents.detector_agent import DetectorAgent
from fastapi import HTTPException
from datetime import datetime
from typing import Dict, Optional
import os
import logging
import json
import traceback

class WebsiteCloneOrchestrator:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.explorer = ExplorerAgent(config)
        self.screenshot_agent = ScreenshotAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.generator = GeneratorAgent(config)
        self.detector = DetectorAgent(config)

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        return logging.getLogger(self.__class__.__name__)

    async def clone_website(self, url: str, framework: str = "react", options: Dict = {}) -> CloneResult:
        """Main cloning pipeline with enhanced analyzer and generator integration"""
        start_time = datetime.now()
        analysis_result = None
        generated_project = None
        
        try:
            # Step 1: Explore and capture
            self.logger.info(f"Starting clone process for: {url}")
            page_data = await self.explorer.navigate_to_url(url)
            
            # Step 2: Screenshot
            timestamp = int(start_time.timestamp())
            screenshot_path = f"{getattr(self.config, 'output_dir', 'generated_project')}/original_{timestamp}.png"
            await self.screenshot_agent.capture_full_page(self.explorer.page, screenshot_path)
            
            # Step 3: Enhanced Analysis
            self.logger.info("Analyzing website structure...")
            analysis_config = {
                'include_styles': options.get('analyze_styles', True),
                'include_components': options.get('analyze_components', True),
                'include_assets': options.get('analyze_assets', True),
                'depth': options.get('analysis_depth', 2)
            }
            # Add analysis config as metadata to HTML content
            html_with_config = {
                'content': page_data["html_content"],
                'analysis_config': analysis_config
            }
            analysis_result = await self.analyzer.analyze_screenshot(
                screenshot_path, 
                json.dumps(html_with_config)
            )
            
            # Validate analysis results
            if not self._validate_analysis(analysis_result):
                raise HTTPException(status_code=400, detail="Website analysis failed to produce valid results")
            
            # Log framework detection and requested framework
            detected_framework = analysis_result.get('framework', {}).get('primary', 'unknown').lower()
            if detected_framework != framework.lower():
                self.logger.warning(f"Framework mismatch: Requested '{framework}', Detected '{detected_framework}'. Using requested framework '{framework}'.")
            
            # Step 4: Enhanced Code Generation
            self.logger.info("Generating code...")
            generated_project = await self.generator.generate_code(
                analysis_result, 
                framework
            )
            
            # Step 5: Validate generated code
            if not self._validate_generated_code(generated_project, framework):
                raise HTTPException(status_code=400, detail="Generated code validation failed")
            
            # Step 6: Compare visual similarity
            generated_url = options.get('generated_url', 'http://localhost:3000')
            generated_screenshot = f"{getattr(self.config, 'output_dir', 'generated_project')}/generated_{timestamp}.png"
            similarity_score = 0.0
            if hasattr(self.screenshot_agent, 'capture_full_page_url'):
                await self.screenshot_agent.capture_full_page_url(generated_url, generated_screenshot)
                similarity_score = await self.detector.validate_similarity(screenshot_path, generated_screenshot)
            
            # Step 7: Run Lighthouse audit (optional)
            lighthouse_score = await self._run_lighthouse_audit(generated_url) if options.get('run_lighthouse', False) else None
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Clone process completed in {generation_time:.2f} seconds")
            
            return CloneResult(
                status="success",
                similarity_score=similarity_score,
                generation_time=generation_time,
                lighthouse_score=lighthouse_score,
                deployed_url=generated_url
            )
            
        except Exception as e:
            tb_str = traceback.format_exc()
            error_detail = {
                'error': str(e),
                'traceback': tb_str,
                'analysis_result': bool(analysis_result),
                'generated_project': bool(generated_project)
            }
            self.logger.error(f"Clone process failed: {json.dumps(error_detail, indent=2)}")
            await self.explorer.cleanup()
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=json.dumps(error_detail))
        finally:
            await self.explorer.cleanup()
    
    def _validate_analysis(self, analysis: Dict) -> bool:
        """Validate analysis results for required components"""
        try:
            # Check for basic structure
            if not analysis:
                self.logger.warning("Analysis result is empty")
                return False

            # Check for framework information
            if 'framework' not in analysis:
                self.logger.warning("Missing framework information in analysis")
                return False

            # Check for components
            if 'components' not in analysis:
                self.logger.warning("Missing components in analysis")
                return False

            # Check for styles
            if 'styles' not in analysis:
                self.logger.warning("Missing styles in analysis")
                return False

            # Check if component analysis has minimum required data
            if not analysis.get('components'):
                self.logger.warning("No components identified in analysis")
                return False

            # Check if styles analysis has minimum required data
            if not analysis.get('styles'):
                self.logger.warning("No styles identified in analysis")
                return False

            self.logger.info("Analysis validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Analysis validation failed: {str(e)}")
            return False

    def _validate_generated_code(self, generated_project: GeneratedProject, framework: str) -> bool:
        """Validate the generated code for completeness and correctness"""
        try:
            # Check for essential files
            required_files = ['package.json', '.gitignore', 'README.md'] if framework.lower() != 'vanilla' else ['index.html', '.gitignore', 'README.md']
            for file in required_files:
                if file not in generated_project.config_files and file not in generated_project.project_structure:
                    self.logger.warning(f"Missing required file: {file}")
                    return False

            # Validate package.json for non-vanilla frameworks
            if framework.lower() != 'vanilla':
                if not generated_project.package_json.get('dependencies'):
                    self.logger.warning(f"package.json missing dependencies: {json.dumps(generated_project.package_json, indent=2)}")
                    return False

            # Check for at least one page component
            has_page = any('page' in path.lower() or 'index' in path.lower() for path in generated_project.project_structure.keys())
            if not has_page:
                self.logger.warning("No page components found")
                return False

            # Additional validation for framework-specific files
            if framework.lower() == 'react':
                if not any(path.endswith('.jsx') or path.endswith('.tsx') for path in generated_project.project_structure.keys()):
                    self.logger.warning("No React component files found")
                    return False

            self.logger.info("Generated code validation passed")
            return True
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False

    async def _run_lighthouse_audit(self, url: str) -> Optional[Dict]:
        """Run Lighthouse audit on the generated website"""
        try:
            # Placeholder for Lighthouse audit implementation
            return {}
        except Exception as e:
            self.logger.error(f"Lighthouse audit failed: {str(e)}")
            return None

    async def _compare_visual_similarity(self, original_screenshot: str, generated_url: str) -> float:
        """Compare visual similarity using DetectorAgent"""
        try:
            generated_screenshot = f"{getattr(self.config, 'output_dir', 'generated_project')}/generated_{int(datetime.now().timestamp())}.png"
            await self.screenshot_agent.capture_full_page_url(generated_url, generated_screenshot)
            return await self.detector.validate_similarity(original_screenshot, generated_screenshot)
        except Exception as e:
            self.logger.error(f"Visual comparison failed: {str(e)}")
            return 0.5