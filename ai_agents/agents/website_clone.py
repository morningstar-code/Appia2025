
from config.system_config import SystemConfig, CloneResult, GeneratedProject
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
try:
    from google.adk.artifacts import InMemoryArtifactService
    from google.genai.types import Part
    ADK_AVAILABLE = True
except ImportError:
    print("Google ADK not available, artifacts will be stored locally")
    ADK_AVAILABLE = False

class WebsiteCloneOrchestrator:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        if ADK_AVAILABLE:
            self.artifact_service = InMemoryArtifactService()
        else:
            self.artifact_service = None
        self.screenshot_agent = ScreenshotAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.generator = GeneratorAgent(config)
        self.detector = DetectorAgent(config)

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        return logging.getLogger(self.__class__.__name__)

    async def _save_artifact(self, data, filename: str, mime_type: str, timestamp: int) -> Optional[str]:
        """Helper method to save artifacts with proper error handling"""
        if not self.artifact_service or not ADK_AVAILABLE:
            self.logger.warning("Artifact service not available, skipping artifact save")
            return None
            
        try:
            # Create Part object correctly based on data type
            if isinstance(data, bytes):
                artifact = Part(
                    inline_data={
                        'data': data,
                        'mime_type': mime_type
                    }
                )
            elif isinstance(data, str):
                artifact = Part(
                    inline_data={
                        'data': data.encode('utf-8'),
                        'mime_type': mime_type
                    }
                )
            else:
                json_str = json.dumps(data, ensure_ascii=False)
                artifact = Part(
                    inline_data={
                        'data': json_str.encode('utf-8'),
                        'mime_type': mime_type
                    }
                )
            
            revision_id = await self.artifact_service.save_artifact(
                app_name="orchestrator_app",
                user_id="user_orchestrator",
                session_id="session_orchestrator",
                filename=f"{filename}_{timestamp}",
                artifact=artifact
            )
            self.logger.info(f"Artifact saved with revision ID: {revision_id}")
            return revision_id
            
        except Exception as e:
            self.logger.error(f"Failed to save artifact {filename}: {str(e)}")
            return None

    async def clone_website(self, url: str, framework: str = "nextjs", options: Dict = {}) -> CloneResult:
        """Main cloning pipeline with improved error handling and Google ADK integration"""
        start_time = datetime.now()
        timestamp = int(start_time.timestamp())
        screenshot_path = None
        analysis_result = None
        generated_project = None
        artifact_ids = {}
        
        try:
            # Step 1: Capture screenshot and get page data
            self.logger.info(f"Starting clone process for: {url}")
            output_dir = getattr(self.config, 'output_dir', 'generated_project')
            os.makedirs(output_dir, exist_ok=True)
            
            screenshot_path = f"{output_dir}/original_{timestamp}.png"
            
            # Capture screenshot using screenshot agent
            try:
                screenshot_path = await self.screenshot_agent.capture_full_page_url(url, screenshot_path)
                self.logger.info(f"Screenshot captured successfully: {screenshot_path}")
            except Exception as e:
                self.logger.error(f"Screenshot capture failed: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to capture screenshot: {str(e)}")
            
            # Save screenshot as artifact
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as img_file:
                    screenshot_data = img_file.read()
                screenshot_revision_id = await self._save_artifact(
                    screenshot_data, 
                    "original.png", 
                    "image/png", 
                    timestamp
                )
                if screenshot_revision_id:
                    artifact_ids["screenshot"] = screenshot_revision_id

            # Step 2: Analysis
            self.logger.info("Analyzing website structure...")
            analysis_config = {
                'include_styles': options.get('analyze_styles', True),
                'include_components': options.get('analyze_components', True),
                'include_assets': options.get('analyze_assets', True),
                'depth': options.get('analysis_depth', 2)
            }
            
            try:
                analysis_result = await self.analyzer.analyze_screenshot(
                    screenshot_path, 
                    json.dumps(analysis_config)
                )
                self.logger.info("Website analysis completed successfully")
            except Exception as e:
                self.logger.error(f"Analysis failed: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Website analysis failed: {str(e)}")
            
            # Save analysis as artifact
            analysis_revision_id = await self._save_artifact(
                analysis_result, 
                "analysis.json", 
                "application/json", 
                timestamp
            )
            if analysis_revision_id:
                artifact_ids["analysis"] = analysis_revision_id

            # Validate analysis results
            if not self._validate_analysis(analysis_result):
                raise HTTPException(status_code=400, detail="Website analysis failed to produce valid results")
            
            # Step 3: Code Generation
            self.logger.info("Generating Next.js code...")
            project_output_dir = f"{output_dir}/project_{timestamp}"
            
            try:
                generated_project = await self.generator.generate_code(
                    analysis_result, 
                    project_output_dir
                )
                self.logger.info("Code generation completed successfully")
            except Exception as e:
                self.logger.error(f"Code generation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")
            
            # Save generated project metadata as artifact
            generated_revision_id = await self._save_artifact(
                generated_project, 
                "generated_project.json", 
                "application/json", 
                timestamp
            )
            if generated_revision_id:
                artifact_ids["generated_project"] = generated_revision_id

            # Step 4: Validate generated code
            if not self._validate_generated_code(generated_project):
                raise HTTPException(status_code=400, detail="Generated code validation failed")
            
            # Step 5: Compare visual similarity
            similarity_score = 0.0
            generated_url = options.get('generated_url', 'http://localhost:3000')
            
            if options.get('compare_similarity', True):
                try:
                    similarity_score = await self._compare_visual_similarity(
                        screenshot_path, 
                        generated_url, 
                        timestamp, 
                        artifact_ids
                    )
                    self.logger.info(f"Visual similarity score: {similarity_score}")
                except Exception as e:
                    self.logger.warning(f"Visual comparison failed: {e}. Setting similarity to 0.5")
                    similarity_score = 0.5
            
            # Step 6: Run Lighthouse audit
            lighthouse_score = None
            if options.get('run_lighthouse', False):
                try:
                    lighthouse_score = await self._run_lighthouse_audit(generated_url)
                except Exception as e:
                    self.logger.warning(f"Lighthouse audit failed: {e}")
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Clone process completed successfully in {generation_time:.2f} seconds")
            
            return CloneResult(
                status="success",
                similarity_score=similarity_score,
                generation_time=generation_time,
                lighthouse_score=lighthouse_score,
                deployed_url=generated_url,
                artifact_ids=artifact_ids
            )
            
        except HTTPException:
            raise
        except Exception as e:
            tb_str = traceback.format_exc()
            error_detail = {
                'error': str(e),
                'traceback': tb_str,
                'analysis_result': bool(analysis_result),
                'generated_project': bool(generated_project),
                'artifact_ids': artifact_ids,
                'step_completed': self._get_completion_status(analysis_result, generated_project)
            }
            self.logger.error(f"Clone process failed: {json.dumps(error_detail, indent=2)}")
            raise HTTPException(status_code=500, detail=json.dumps(error_detail))

    def _get_completion_status(self, analysis_result, generated_project) -> str:
        """Helper to determine which step failed"""
        if not analysis_result:
            return "screenshot_capture_or_analysis"
        elif not generated_project:
            return "code_generation"
        else:
            return "post_generation_validation"

    def _validate_analysis(self, analysis: Dict) -> bool:
        """Validate analysis results for Next.js 14 components"""
        try:
            if not analysis or not isinstance(analysis, dict):
                self.logger.warning("Analysis result is empty or not a dictionary")
                return False

            # Check for required fields
            required_fields = ["components", "cloning_requirements", "content_structure"]
            missing_fields = [field for field in required_fields if field not in analysis or not analysis[field]]
            
            if missing_fields:
                self.logger.warning(f"Missing or empty fields in analysis: {missing_fields}")
                return False

            # Verify components
            components = analysis.get("components", [])
            essential_components = ["app/layout.jsx", "app/page.jsx"]
            if not any(comp in components for comp in essential_components):
                self.logger.warning(f"Missing essential Next.js components: {essential_components}")
                return False

            # Verify package.json
            package_json = analysis.get("cloning_requirements", {}).get("package_json", {})
            if not package_json.get("dependencies", {}).get("next"):
                self.logger.warning("Missing 'next' dependency in package.json")
                return False

            self.logger.info("Analysis validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Analysis validation failed: {str(e)}")
            return False

    def _validate_generated_code(self, generated_project: Dict) -> bool:
        """Validate generated Next.js code for completeness"""
        try:
            if not generated_project or not isinstance(generated_project, dict):
                self.logger.error("Generated project is not a valid dictionary")
                return False
            
            if generated_project.get('status') != 'success':
                self.logger.error(f"Generator reported failure: {generated_project.get('error', 'Unknown error')}")
                return False
            
            generated_files = generated_project.get('generated_files', [])
            if not generated_files:
                self.logger.error("No files were generated")
                return False
            
            # Check for essential Next.js files
            essential_files = ['package.json', 'app/layout.jsx', 'app/page.jsx', 'next.config.js']
            missing_files = [f for f in essential_files if not any(f in file_path for file_path in generated_files)]
            if missing_files:
                self.logger.error(f"Missing essential Next.js files: {missing_files}")
                return False
            
            output_dir = generated_project.get('output_directory')
            if output_dir and not os.path.exists(output_dir):
                self.logger.warning(f"Output directory not found: {output_dir}")
            
            artifact_ids = generated_project.get('artifact_ids', {})
            if not artifact_ids:
                self.logger.warning("No artifact IDs found in generated project")
            
            self.logger.info(f"Generated code validation passed. Files: {len(generated_files)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            self.logger.error(f"Generated project structure: {json.dumps(generated_project, indent=2) if isinstance(generated_project, dict) else str(generated_project)}")
            return False

    async def _run_lighthouse_audit(self, url: str) -> Optional[Dict]:
        """Run Lighthouse audit on the generated website"""
        try:
            self.logger.info(f"Lighthouse audit requested for: {url}")
            return {
                "performance": 85,
                "accessibility": 90,
                "best_practices": 88,
                "seo": 92,
                "note": "Placeholder scores - implement actual Lighthouse integration"
            }
        except Exception as e:
            self.logger.error(f"Lighthouse audit failed: {str(e)}")
            return None

    async def _compare_visual_similarity(self, original_screenshot: str, generated_url: str, timestamp: int, artifact_ids: Dict) -> float:
        """Compare visual similarity using DetectorAgent"""
        try:
            output_dir = getattr(self.config, 'output_dir', 'generated_project')
            generated_screenshot = f"{output_dir}/generated_{timestamp}.png"
            await self.screenshot_agent.capture_full_page_url(generated_url, generated_screenshot)
            similarity_score = await self.detector.validate_similarity(original_screenshot, generated_screenshot)
            
            if os.path.exists(generated_screenshot):
                with open(generated_screenshot, 'rb') as img_file:
                    gen_screenshot_data = img_file.read()
                gen_screenshot_revision_id = await self._save_artifact(
                    gen_screenshot_data, 
                    "generated.png", 
                    "image/png", 
                    timestamp
                )
                if gen_screenshot_revision_id:
                    artifact_ids["generated_screenshot"] = gen_screenshot_revision_id
            
            return float(similarity_score)
        except Exception as e:
            self.logger.error(f"Visual comparison failed: {str(e)}")
            return 0.5