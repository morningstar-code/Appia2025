from config.system_config import SystemConfig, CloneResult, GeneratedProject
from agents.explorer_agent import ExplorerAgent
from agents.screenshot_agent import ScreenshotAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.generator_agent import GeneratorAgent
from agents.detector_agent import DetectorAgent
from fastapi import HTTPException
from datetime import datetime
from typing import Dict
import os
from typing import Dict

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
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    async def clone_website(self, url: str, framework: str = "react", options: Dict = {}) -> CloneResult:
        """Main cloning pipeline"""
        start_time = datetime.now()
        
        try:
            # Step 1: Explore and capture
            self.logger.info(f"Starting clone process for: {url}")
            page_data = await self.explorer.navigate_to_url(url)
            
            # Step 2: Screenshot
            timestamp = int(start_time.timestamp())
            screenshot_path = f"{getattr(self.config, 'output_dir', 'generated_project')}/original_{timestamp}.png"
            await self.screenshot_agent.capture_full_page(self.explorer.page, screenshot_path)
            
            # Step 3: Analyze
            self.logger.info("Analyzing website structure...")
            analysis = await self.analyzer.analyze_screenshot(screenshot_path, page_data["html_content"])
            
            # Step 4: Generate code
            self.logger.info("Generating code...")
            generated_project = await self.generator.generate_code(analysis, framework)
            
            # Step 5: Validate generated code
            if not self._validate_generated_code(generated_project):
                raise HTTPException(status_code=400, detail="Generated code validation failed")
            
            # Step 6: Compare visual similarity
            generated_url = options.get('generated_url', 'http://localhost:3000')
            generated_screenshot = f"{getattr(self.config, 'output_dir', 'generated_project')}/generated_{timestamp}.png"
            if hasattr(self.screenshot_agent, 'capture_full_page_url'):
                await self.screenshot_agent.capture_full_page_url(generated_url, generated_screenshot)
                similarity_score = await self.detector.validate_similarity(screenshot_path, generated_screenshot)
            else:
                similarity_score = 0.0
            
            # Step 7: Run Lighthouse audit (optional)
            lighthouse_score = await self._run_lighthouse_audit(generated_url) if options.get('run_lighthouse', False) else None
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Cleanup
            await self.explorer.cleanup()
            
            self.logger.info(f"Clone process completed in {generation_time:.2f} seconds")
            
            return CloneResult(
                status="success",
                similarity_score=similarity_score,
                generation_time=generation_time,
                lighthouse_score=lighthouse_score
            )
            
        except Exception as e:
            self.logger.error(f"Clone process failed: {str(e)}")
            await self.explorer.cleanup()
            raise HTTPException(status_code=500, detail=str(e))
    
    def _validate_generated_code(self, generated_project: GeneratedProject) -> bool:
        """Validate the generated code for completeness and correctness"""
        try:
            # Check for essential files
            required_files = ['package.json', '.gitignore', 'README.md']
            for file in required_files:
                if file not in generated_project.config_files and file not in generated_project.project_structure:
                    self.logger.warning(f"Missing required file: {file}")
                    return False

            # Validate package.json
            if not generated_project.package_json.get('dependencies'):
                self.logger.warning("package.json missing dependencies")
                return False

            # Check for at least one page component
            has_page = any('page' in path.lower() or 'index' in path.lower() for path in generated_project.project_structure.keys())
            if not has_page:
                self.logger.warning("No page components found")
                return False

            self.logger.info("Generated code validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False

    async def _run_lighthouse_audit(self, url: str) -> Dict:
        """Run Lighthouse audit on the generated website"""
        # Placeholder for Lighthouse audit logic
        return {}

    async def _compare_visual_similarity(self, original_screenshot: str, generated_url: str) -> float:
        """Compare visual similarity using DetectorAgent"""
        try:
            # Capture screenshot of generated website
            generated_screenshot = f"{getattr(self.config, 'output_dir', 'generated_project')}/generated_{int(datetime.now().timestamp())}.png"
            await self.screenshot_agent.capture_full_page_url(generated_url, generated_screenshot)
            return await self.detector.validate_similarity(original_screenshot, generated_screenshot)
        except Exception as e:
            self.logger.error(f"Visual comparison failed: {str(e)}")
            return 0.5  # Default score on error
   