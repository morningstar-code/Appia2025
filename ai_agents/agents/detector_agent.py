from google.adk.agents import LlmAgent
from google.adk.tools import BaseTool, ToolContext
from google.adk.runners import InMemoryRunner
from google.adk.artifacts import InMemoryArtifactService
from google.genai.types import Part
from config.system_config import SystemConfig
import os
import cv2
from skimage.metrics import structural_similarity as ssim
import logging
from typing import Dict, Tuple, Any
import google.generativeai as genai
import base64
from PIL import Image
import io
from datetime import datetime
import asyncio

class SSIMTool(BaseTool):
    """Tool for calculating SSIM similarity between two images"""
    
    def __init__(self):
        super().__init__(
            name="ssim_tool",
            description="Calculate visual similarity between two images using SSIM (Structural Similarity Index)"
        )
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """Calculate SSIM similarity between two images"""
        try:
            original_path = kwargs.get('original_screenshot')
            generated_path = kwargs.get('generated_screenshot')
            
            if not original_path or not generated_path:
                return {
                    "success": False,
                    "error": "Both original_screenshot and generated_screenshot paths are required",
                    "similarity_score": 0.0
                }
            
            similarity_score = await self._calculate_ssim(original_path, generated_path)
            
            return {
                "success": True,
                "similarity_score": similarity_score,
                "assessment": self._get_similarity_assessment(similarity_score),
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"SSIM calculation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "similarity_score": 0.0
            }

    async def _calculate_ssim(self, original_path: str, generated_path: str) -> float:
        """Calculate SSIM similarity score"""
        try:
            # Check if files exist
            if not os.path.exists(original_path) or not os.path.exists(generated_path):
                self.logger.warning("Screenshot files not found for comparison")
                return 0.5  # Default similarity score
            
            # Load images in a separate thread to avoid blocking
            def load_and_compare():
                img1 = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
                img2 = cv2.imread(generated_path, cv2.IMREAD_GRAYSCALE)
                
                if img1 is None or img2 is None:
                    self.logger.error("Failed to load images for comparison")
                    return 0.5
                
                # Resize to same dimensions
                height, width = img1.shape
                img2_resized = cv2.resize(img2, (width, height))
                
                # Calculate SSIM
                similarity_score = ssim(img1, img2_resized)
                return float(similarity_score)
            
            loop = asyncio.get_event_loop()
            similarity_score = await loop.run_in_executor(None, load_and_compare)
            
            self.logger.info(f"SSIM Similarity score: {similarity_score}")
            return similarity_score
            
        except Exception as e:
            self.logger.error(f"SSIM calculation failed: {str(e)}")
            return 0.5

    def _get_similarity_assessment(self, score: float) -> str:
        """Get textual assessment of similarity score"""
        if score >= 0.9:
            return "Excellent visual match"
        elif score >= 0.8:
            return "Good visual similarity"
        elif score >= 0.6:
            return "Moderate similarity with noticeable differences"
        else:
            return "Poor visual match with significant differences"

    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for the tool"""
        return {
            "type": "object",
            "properties": {
                "original_screenshot": {
                    "type": "string",
                    "description": "Path to the original screenshot image"
                },
                "generated_screenshot": {
                    "type": "string",
                    "description": "Path to the generated screenshot image"
                }
            },
            "required": ["original_screenshot", "generated_screenshot"]
        }

class VisualAnalysisTool(BaseTool):
    """Tool for detailed visual analysis using Gemini AI"""
    
    def __init__(self):
        super().__init__(
            name="visual_analysis_tool",
            description="Perform detailed visual comparison analysis using Gemini AI"
        )
        self.logger = self._setup_logger()
        self.gemini_model = None
        self._setup_gemini()

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    def _setup_gemini(self):
        """Initialize Gemini AI client"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.logger.info("Gemini AI initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini AI: {str(e)}")
            self.gemini_model = None

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """Perform detailed visual analysis between two images"""
        try:
            original_path = kwargs.get('original_screenshot')
            generated_path = kwargs.get('generated_screenshot')
            
            if not original_path or not generated_path:
                return {
                    "success": False,
                    "error": "Both original_screenshot and generated_screenshot paths are required",
                    "detailed_analysis": None
                }
            
            if not self.gemini_model:
                return {
                    "success": False,
                    "error": "Gemini AI not available",
                    "detailed_analysis": "Unable to perform detailed analysis"
                }
            
            analysis = await self._analyze_with_gemini(original_path, generated_path)
            
            return {
                "success": True,
                "detailed_analysis": analysis,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Visual analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "detailed_analysis": "Unable to perform detailed visual analysis"
            }

    async def _analyze_with_gemini(self, original_path: str, generated_path: str) -> str:
        """Analyze images using Gemini AI"""
        try:
            # Prepare images for Gemini
            original_image = self._prepare_image_for_gemini(original_path)
            generated_image = self._prepare_image_for_gemini(generated_path)
            
            if not original_image or not generated_image:
                raise Exception("Failed to load images for analysis")
            
            # Create detailed prompt for analysis
            prompt = """
Please perform a comprehensive visual comparison between these two images (original vs generated).
Analyze and provide detailed feedback on:

1. LAYOUT & POSITIONING:
   - Element positioning accuracy
   - Alignment issues
   - Spacing discrepancies
   - Container placement

2. TEXT & TYPOGRAPHY:
   - Text placement accuracy
   - Font size/weight differences
   - Text alignment issues
   - Missing or extra text

3. VISUAL ELEMENTS:
   - Color accuracy
   - Image/icon placement
   - Button positioning
   - Border/shadow differences

4. STRUCTURAL ISSUES:
   - Missing elements
   - Extra elements
   - Div/container structure problems
   - Responsive layout issues

5. OVERALL ASSESSMENT:
   - What matches well
   - Critical differences
   - Minor discrepancies
   - Overall fidelity score (1-10)

Please be specific about pixel-level differences, positioning errors, and any visual inconsistencies.
Format your response as a structured analysis with clear sections.
"""
            
            # Generate analysis using Gemini in a separate thread
            def generate_analysis():
                response = self.gemini_model.generate_content([
                    prompt,
                    "Original Image:",
                    original_image,
                    "Generated Image:",
                    generated_image
                ])
                return response.text if response else "No analysis generated"
            
            loop = asyncio.get_event_loop()
            analysis_text = await loop.run_in_executor(None, generate_analysis)
            
            return analysis_text
            
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {str(e)}")
            raise

    def _prepare_image_for_gemini(self, image_path: str):
        """Prepare image for Gemini analysis"""
        try:
            image = Image.open(image_path)
            return image
        except Exception as e:
            self.logger.error(f"Failed to prepare image {image_path}: {str(e)}")
            return None

    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for the tool"""
        return {
            "type": "object",
            "properties": {
                "original_screenshot": {
                    "type": "string",
                    "description": "Path to the original screenshot image"
                },
                "generated_screenshot": {
                    "type": "string",
                    "description": "Path to the generated screenshot image"
                }
            },
            "required": ["original_screenshot", "generated_screenshot"]
        }

class DetectorAgent:
    """Google ADK Detection Agent for visual comparison and analysis"""
    
    def __init__(self, config: SystemConfig = None, model: str = None):
        from google.adk.models import Gemini
        
        self.config = config
        self.logger = self._setup_logger()
        self.artifact_service = InMemoryArtifactService()
        
        # Initialize tools
        self.ssim_tool = SSIMTool()
        self.visual_analysis_tool = VisualAnalysisTool()
        
        # Determine the model to use
        if model is None:
            if config and hasattr(config, 'gemini_model'):
                model_name = getattr(config, 'gemini_model', "gemini-2.0-flash-exp")
            else:
                model_name = "gemini-2.0-flash-exp"
        else:
            model_name = model
        
        # Create Gemini model instance if config has API key
        if config and hasattr(config, 'gemini_api_key'):
            try:
                gemini_model = Gemini(
                    model=model_name,
                    api_key=getattr(config, 'gemini_api_key')
                )
                model_to_use = gemini_model
            except Exception as e:
                self.logger.warning(f"Failed to create Gemini model with API key: {e}")
                model_to_use = model_name
        else:
            model_to_use = None
        
        # Create the ADK agent
        self.agent = LlmAgent(
            name="detector_agent",
            model=model_to_use or model_name,
            instruction="""
            You are a visual detection and analysis agent. Your primary functions are:
            
            1. Calculate visual similarity between images using SSIM (Structural Similarity Index)
            2. Perform detailed visual analysis using AI-powered comparison
            3. Generate comprehensive reports with actionable recommendations
            
            When asked to compare images:
            1. Use the ssim_tool to calculate similarity scores
            2. Use the visual_analysis_tool for detailed AI-powered analysis
            3. Provide structured feedback with specific recommendations
            4. Generate comprehensive reports combining all metrics
            
            Always be thorough in your analysis and provide actionable insights.
            """,
            description="An agent specialized in visual detection, comparison, and analysis",
            tools=[self.ssim_tool, self.visual_analysis_tool]
        )
        
        # Create runner for the agent
        self.runner = InMemoryRunner(agent=self.agent)

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)

    async def validate_similarity(self, original_screenshot: str, generated_screenshot: str) -> Tuple[float, Dict]:
        """Calculate visual similarity using SSIM and perform detailed analysis"""
        try:
            # Calculate SSIM similarity
            ssim_result = await self._calculate_ssim_similarity(original_screenshot, generated_screenshot)
            
            # Perform visual analysis
            analysis_result = await self._analyze_visual_differences(original_screenshot, generated_screenshot)
            
            # Combine results
            complete_result = {
                "similarity_score": ssim_result,
                "visual_analysis": analysis_result,
                "comparison_summary": self._generate_summary(ssim_result, analysis_result)
            }
            
            return ssim_result, complete_result
            
        except Exception as e:
            self.logger.error(f"Similarity validation failed: {str(e)}")
            return 0.0, {"error": str(e)}

    async def _calculate_ssim_similarity(self, original_screenshot: str, generated_screenshot: str) -> float:
        """Calculate SSIM similarity using the tool"""
        try:
            from types import SimpleNamespace
            mock_context = SimpleNamespace()
            
            result = await self.ssim_tool.execute(
                context=mock_context,
                original_screenshot=original_screenshot,
                generated_screenshot=generated_screenshot
            )
            
            if result.get("success"):
                return result.get("similarity_score", 0.0)
            else:
                self.logger.error(f"SSIM tool failed: {result.get('error')}")
                return 0.0
                
        except Exception as e:
            self.logger.error(f"SSIM calculation failed: {str(e)}")
            return 0.0

    async def _analyze_visual_differences(self, original_screenshot: str, generated_screenshot: str) -> Dict:
        """Perform detailed visual analysis using the tool"""
        try:
            from types import SimpleNamespace
            mock_context = SimpleNamespace()
            
            result = await self.visual_analysis_tool.execute(
                context=mock_context,
                original_screenshot=original_screenshot,
                generated_screenshot=generated_screenshot
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Visual analysis failed: {str(e)}")
            return {"error": str(e), "detailed_analysis": "Analysis failed"}

    def _generate_summary(self, similarity_score: float, analysis_result: Dict) -> str:
        """Generate a concise summary of the comparison"""
        try:
            if similarity_score >= 0.9:
                ssim_assessment = "Excellent visual match"
            elif similarity_score >= 0.8:
                ssim_assessment = "Good visual similarity"
            elif similarity_score >= 0.6:
                ssim_assessment = "Moderate similarity with noticeable differences"
            else:
                ssim_assessment = "Poor visual match with significant differences"
            
            summary = f"""
COMPARISON SUMMARY:
- SSIM Score: {similarity_score:.3f} ({ssim_assessment})
- Detailed Analysis: {'Available' if analysis_result.get('success') else 'Failed'}
- Status: {analysis_result.get('status', 'Unknown')}
"""
            return summary.strip()
            
        except Exception as e:
            return f"Summary generation failed: {str(e)}"

    async def get_comprehensive_report(self, original_screenshot: str, generated_screenshot: str) -> Dict:
        """Get a complete comparison report with all metrics and analysis"""
        try:
            similarity_score, detailed_results = await self.validate_similarity(
                original_screenshot, generated_screenshot
            )
            
            return {
                "timestamp": self._get_timestamp(),
                "files_compared": {
                    "original": original_screenshot,
                    "generated": generated_screenshot
                },
                "metrics": {
                    "ssim_score": similarity_score,
                    "visual_analysis": detailed_results["visual_analysis"]
                },
                "summary": detailed_results["comparison_summary"],
                "recommendations": self._generate_recommendations(similarity_score, detailed_results)
            }
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {"error": str(e)}

    def _generate_recommendations(self, similarity_score: float, analysis_results: Dict) -> list:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        if similarity_score < 0.8:
            recommendations.append("Consider reviewing layout positioning and element alignment")
            recommendations.append("Check for missing or misplaced visual elements")
        
        if similarity_score < 0.6:
            recommendations.append("Significant visual differences detected - major revision needed")
            recommendations.append("Review CSS styling and responsive design implementation")
        
        if "error" in analysis_results.get("visual_analysis", {}):
            recommendations.append("Manual visual inspection recommended due to analysis limitations")
        
        return recommendations

    def _get_timestamp(self) -> str:
        """Get current timestamp for reporting"""
        return datetime.now().isoformat()

    def get_agent(self) -> LlmAgent:
        """Get the underlying ADK agent"""
        return self.agent

    def get_runner(self) -> InMemoryRunner:
        """Get the runner instance"""
        return self.runner