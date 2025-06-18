from config.system_config import SystemConfig
import os
import cv2
from skimage.metrics import structural_similarity as ssim
import logging
from typing import Dict

class DetectorAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    async def validate_similarity(self, original_screenshot: str, generated_screenshot: str) -> float:
        """Calculate visual similarity using SSIM"""
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
            
            self.logger.info(f"Similarity score: {similarity_score}")
            return float(similarity_score)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.5  # Return default score on error
