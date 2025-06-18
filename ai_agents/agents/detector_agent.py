from config.system_config import SystemConfig
import os
import cv2
from skimage.metrics import structural_similarity as ssim
import logging
from typing import Dict, Tuple
import google.generativeai as genai
import base64
from PIL import Image
import io

class DetectorAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self._setup_gemini()
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    def _setup_gemini(self):
        """Initialize Gemini AI client"""
        try:
            # Make sure to set your API key in environment variables
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.logger.info("Gemini AI initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini AI: {str(e)}")
            self.gemini_model = None
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 for Gemini API"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to encode image {image_path}: {str(e)}")
            return None
    
    def _prepare_image_for_gemini(self, image_path: str):
        """Prepare image for Gemini analysis"""
        try:
            image = Image.open(image_path)
            return image
        except Exception as e:
            self.logger.error(f"Failed to prepare image {image_path}: {str(e)}")
            return None
    
    async def analyze_visual_differences(self, original_screenshot: str, generated_screenshot: str) -> Dict:
        """Perform detailed visual analysis using Gemini 2.0 Flash"""
        if not self.gemini_model:
            return {"error": "Gemini AI not available", "analysis": "Unable to perform detailed analysis"}
        
        try:
            # Prepare images for Gemini
            original_image = self._prepare_image_for_gemini(original_screenshot)
            generated_image = self._prepare_image_for_gemini(generated_screenshot)
            
            if not original_image or not generated_image:
                return {"error": "Failed to load images", "analysis": "Unable to analyze images"}
            
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
            
            # Generate analysis using Gemini
            response = self.gemini_model.generate_content([
                prompt,
                "Original Image:",
                original_image,
                "Generated Image:",
                generated_image
            ])
            
            analysis_text = response.text if response else "No analysis generated"
            
            return {
                "detailed_analysis": analysis_text,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {str(e)}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "detailed_analysis": "Unable to perform detailed visual analysis"
            }
    
    async def validate_similarity(self, original_screenshot: str, generated_screenshot: str) -> Tuple[float, Dict]:
        """Calculate visual similarity using SSIM and perform detailed analysis"""
        similarity_result = await self._calculate_ssim_similarity(original_screenshot, generated_screenshot)
        analysis_result = await self.analyze_visual_differences(original_screenshot, generated_screenshot)
        
        # Combine results
        complete_result = {
            "similarity_score": similarity_result,
            "visual_analysis": analysis_result,
            "comparison_summary": self._generate_summary(similarity_result, analysis_result)
        }
        
        return similarity_result, complete_result
    
    async def _calculate_ssim_similarity(self, original_screenshot: str, generated_screenshot: str) -> float:
        """Calculate visual similarity using SSIM (original method)"""
        try:
            # Check if files exist
            if not os.path.exists(original_screenshot) or not os.path.exists(generated_screenshot):
                self.logger.warning("Screenshot files not found for comparison")
                return 0.5  # Default similarity score
            
            # Load images
            img1 = cv2.imread(original_screenshot, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(generated_screenshot, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                self.logger.error("Failed to load images for comparison")
                return 0.5
            
            # Resize to same dimensions
            height, width = img1.shape
            img2_resized = cv2.resize(img2, (width, height))
            
            # Calculate SSIM
            similarity_score = ssim(img1, img2_resized)
            self.logger.info(f"SSIM Similarity score: {similarity_score}")
            
            return float(similarity_score)
            
        except Exception as e:
            self.logger.error(f"SSIM calculation failed: {str(e)}")
            return 0.5  # Return default score on error
    
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
            - Detailed Analysis: {'Available' if 'detailed_analysis' in analysis_result else 'Failed'}
            - Status: {analysis_result.get('status', 'Unknown')}
            """
            
            return summary.strip()
            
        except Exception as e:
            return f"Summary generation failed: {str(e)}"
    
    async def get_comprehensive_report(self, original_screenshot: str, generated_screenshot: str) -> Dict:
        """Get a complete comparison report with all metrics and analysis"""
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
        from datetime import datetime
        return datetime.now().isoformat()

