# AI Website Cloning System
# Core implementation with Agent Development Kit (ADK) integration

import asyncio
import json
import re
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import base64
import hashlib
import logging

from dotenv import load_dotenv
load_dotenv() 

# Core dependencies
import google.generativeai as genai
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import requests
from pathlib import Path

# FastAPI for API wrapper
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from logging.handlers import RotatingFileHandler

# Import your config and orchestrator
from config.system_config import SystemConfig, CloneRequest, CloneResult
from agents.website_clone import WebsiteCloneOrchestrator

def setup_logging(log_file: str = "website_clone.log", log_level: int = logging.INFO) -> None:
    """
    Configure logging to capture all events, including custom 'extra' fields, during the website cloning process.

    Args:
        log_file (str): Path to the log file.
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
    """
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Prevent duplicate logs if setup is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    # Custom formatter to include extra fields
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            # Default format for standard fields
            base_format = '%(asctime)s:%(name)s:%(levelname)s:%(message)s'
            # Add extra fields if they exist
            extra_fields = [
                f"{key}={value}"
                for key, value in sorted(record.__dict__.items())
                if key in ['framework', 'components_count', 'layout_type']
            ]
            if extra_fields:
                base_format += ' ' + ' '.join(extra_fields)
            self._style._fmt = base_format
            return super().format(record)

    # Create format for log messages
    formatter = CustomFormatter(datefmt='%Y-%m-%d %H:%M:%S')

    # Console handler for printing to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ScreenshotRequest(BaseModel):
    url: str
    output_path: Optional[str] = None
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    wait_time: Optional[int] = 2000

class ScreenshotResponse(BaseModel):
    status: str
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    capture_time: float
    file_size: Optional[int] = None

class AnalysisRequest(BaseModel):
    screenshot_path: str
    html_content: Optional[str] = ""
    analysis_config: Optional[Dict] = {}

class AnalysisResponse(BaseModel):
    status: str
    analysis: Optional[Dict] = None
    error: Optional[str] = None
    analysis_time: float
    framework_detected: Optional[str] = None
    components_count: Optional[int] = None

class ComparisonRequest(BaseModel):
    original_screenshot: str
    generated_screenshot: str
    detailed_analysis: Optional[bool] = True

class ComparisonResponse(BaseModel):
    status: str
    similarity_score: float
    detailed_analysis: Optional[Dict] = None
    error: Optional[str] = None
    comparison_time: float
    assessment: Optional[str] = None

class GenerationRequest(BaseModel):
    analysis: Dict
    output_dir: str
    framework: Optional[str] = "react"

class GenerationResponse(BaseModel):
    status: str
    generated_files: List[str]
    output_directory: str
    error: Optional[str] = None
    generation_time: float
    framework_used: Optional[str] = None

class PipelineRequest(BaseModel):
    url: str
    framework: Optional[str] = "react"
    output_dir: Optional[str] = None
    save_intermediate: Optional[bool] = True

class PipelineResponse(BaseModel):
    status: str
    steps_completed: List[str]
    final_result: Optional[Dict] = None
    error: Optional[str] = None
    total_time: float
    intermediate_files: Optional[Dict] = None

class AgentStatusResponse(BaseModel):
    screenshot_agent: Dict
    analyzer_agent: Dict
    detector_agent: Dict
    generator_agent: Dict
    orchestrator: Dict

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================

# FastAPI Application
app = FastAPI(
    title="AI Website Cloning System", 
    version="1.0.0",
    description="Comprehensive API for testing all agents in the website cloning system"
)

# Global config
config = SystemConfig(
    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", "demo-project")
)

# Initialize agents
from agents.screenshot_agent import ScreenshotAgent
screenshot_agent = ScreenshotAgent(config)

# Import other agents only when needed to avoid circular imports
def get_analyzer_agent():
    from agents.analyzer_agent import AnalyzerAgent
    return AnalyzerAgent(config)

def get_detector_agent():
    from agents.detector_agent import DetectorAgent
    return DetectorAgent(config)

def get_generator_agent():
    from agents.generator_agent import GeneratorAgent
    return GeneratorAgent(config)

def get_orchestrator():
    return WebsiteCloneOrchestrator(config)

# ============================================================================
# INDIVIDUAL AGENT TEST ENDPOINTS
# ============================================================================

@app.post("/test/screenshot", response_model=ScreenshotResponse)
async def test_screenshot_agent(request: ScreenshotRequest):
    """Test the ScreenshotAgent by capturing a screenshot from a URL"""
    start_time = time.time()
    
    try:
        # Validate URL
        if not request.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Generate output path if not provided
        if not request.output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_screenshot_{timestamp}.png"
            request.output_path = f"./screenshots/{filename}"
        
        # Ensure screenshots directory exists
        Path(request.output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Capture screenshot
        try:
            screenshot_path = await screenshot_agent.capture_full_page_url(
                request.url, 
                request.output_path
            )
        except Exception as capture_error:
            # If there's an error but the file was created, we can still return success
            if os.path.exists(request.output_path):
                screenshot_path = request.output_path
                print(f"Warning: Screenshot saved but with error: {capture_error}")
            else:
                raise capture_error
        
        # Get file size
        file_size = None
        if os.path.exists(screenshot_path):
            try:
                file_size = os.path.getsize(screenshot_path)
            except Exception as size_error:
                print(f"Warning: Could not get file size: {size_error}")
        
        capture_time = time.time() - start_time
        
        return ScreenshotResponse(
            status="success",
            screenshot_path=screenshot_path,
            capture_time=capture_time,
            file_size=file_size
        )
        
    except Exception as e:
        capture_time = time.time() - start_time
        print(f"Error in screenshot endpoint: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        return ScreenshotResponse(
            status="error",
            error=str(e),
            capture_time=capture_time
        )

@app.post("/test/analyzer", response_model=AnalysisResponse)
async def test_analyzer_agent(request: AnalysisRequest):
    """Test the AnalyzerAgent by analyzing a screenshot"""
    start_time = time.time()
    
    try:
        # Validate screenshot path
        if not os.path.exists(request.screenshot_path):
            raise HTTPException(status_code=400, detail="Screenshot file not found")
        
        # Get analyzer agent and analyze screenshot
        analyzer_agent = get_analyzer_agent()
        analysis = await analyzer_agent.analyze_screenshot(
            request.screenshot_path,
            request.html_content
        )
        
        analysis_time = time.time() - start_time
        
        # Extract key metrics
        framework_detected = analysis.get("framework", {}).get("primary", "unknown")
        components_count = len(analysis.get("components", []))
        
        return AnalysisResponse(
            status="success",
            analysis=analysis,
            analysis_time=analysis_time,
            framework_detected=framework_detected,
            components_count=components_count
        )
        
    except Exception as e:
        analysis_time = time.time() - start_time
        return AnalysisResponse(
            status="error",
            error=str(e),
            analysis_time=analysis_time
        )

@app.post("/test/detector", response_model=ComparisonResponse)
async def test_detector_agent(request: ComparisonRequest):
    """Test the DetectorAgent by comparing two screenshots"""
    start_time = time.time()
    
    try:
        # Validate screenshot paths
        if not os.path.exists(request.original_screenshot):
            raise HTTPException(status_code=400, detail="Original screenshot file not found")
        if not os.path.exists(request.generated_screenshot):
            raise HTTPException(status_code=400, detail="Generated screenshot file not found")
        
        # Get detector agent and compare screenshots
        detector_agent = get_detector_agent()
        similarity_score, detailed_result = await detector_agent.validate_similarity(
            request.original_screenshot,
            request.generated_screenshot
        )
        
        comparison_time = time.time() - start_time
        
        # Generate assessment
        if similarity_score >= 0.9:
            assessment = "Excellent match"
        elif similarity_score >= 0.8:
            assessment = "Good match"
        elif similarity_score >= 0.6:
            assessment = "Moderate match"
        else:
            assessment = "Poor match"
        
        return ComparisonResponse(
            status="success",
            similarity_score=similarity_score,
            detailed_analysis=detailed_result if request.detailed_analysis else None,
            comparison_time=comparison_time,
            assessment=assessment
        )
        
    except Exception as e:
        comparison_time = time.time() - start_time
        return ComparisonResponse(
            status="error",
            error=str(e),
            comparison_time=comparison_time,
            similarity_score=0.0
        )

@app.post("/test/generator", response_model=GenerationResponse)
async def test_generator_agent(request: GenerationRequest):
    """Test the GeneratorAgent by generating code from analysis"""
    start_time = time.time()
    
    try:
        # Validate analysis
        if not request.analysis:
            raise HTTPException(status_code=400, detail="Analysis data is required")
        
        # Ensure output directory exists
        Path(request.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Get generator agent and generate code
        generator_agent = get_generator_agent()
        result = await generator_agent.generate_code(
            request.analysis,
            request.output_dir
        )
        
        generation_time = time.time() - start_time
        
        return GenerationResponse(
            status=result.get("status", "success"),
            generated_files=result.get("generated_files", []),
            output_directory=result.get("output_directory", request.output_dir),
            generation_time=generation_time,
            framework_used=result.get("framework", request.framework)
        )
        
    except Exception as e:
        generation_time = time.time() - start_time
        return GenerationResponse(
            status="error",
            error=str(e),
            generated_files=[],
            output_directory=request.output_dir,
            generation_time=generation_time
        )

# ============================================================================
# PIPELINE TEST ENDPOINTS
# ============================================================================

@app.post("/test/pipeline", response_model=PipelineResponse)
async def test_full_pipeline(request: PipelineRequest):
    """Test the complete website cloning pipeline"""
    start_time = time.time()
    steps_completed = []
    intermediate_files = {}
    
    try:
        # Step 1: Capture screenshot
        steps_completed.append("screenshot_capture")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"./screenshots/pipeline_{timestamp}.png"
        
        screenshot_result = await screenshot_agent.capture_full_page_url(
            request.url, 
            screenshot_path
        )
        intermediate_files["screenshot"] = screenshot_path
        
        # Step 2: Analyze screenshot
        steps_completed.append("analysis")
        analyzer_agent = get_analyzer_agent()
        analysis = await analyzer_agent.analyze_screenshot(screenshot_path)
        intermediate_files["analysis"] = analysis
        
        # Step 3: Generate code
        steps_completed.append("code_generation")
        if not request.output_dir:
            request.output_dir = f"./generated/pipeline_{timestamp}"
        
        generator_agent = get_generator_agent()
        generation_result = await generator_agent.generate_code(
            analysis,
            request.output_dir
        )
        intermediate_files["generation"] = generation_result
        
        total_time = time.time() - start_time
        
        return PipelineResponse(
            status="success",
            steps_completed=steps_completed,
            final_result=generation_result,
            total_time=total_time,
            intermediate_files=intermediate_files if request.save_intermediate else None
        )
        
    except Exception as e:
        total_time = time.time() - start_time
        return PipelineResponse(
            status="error",
            steps_completed=steps_completed,
            error=str(e),
            total_time=total_time,
            intermediate_files=intermediate_files if request.save_intermediate else None
        )

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/test/agents/status", response_model=AgentStatusResponse)
async def get_agents_status():
    """Check the status and configuration of all agents"""
    try:
        return AgentStatusResponse(
            screenshot_agent={
                "status": "available" if screenshot_agent.firecrawl_api_key else "no_api_key",
                "api_key_configured": bool(screenshot_agent.firecrawl_api_key)
            },
            analyzer_agent={
                "status": "available" if config.gemini_api_key else "no_api_key",
                "model_initialized": bool(config.gemini_api_key)
            },
            detector_agent={
                "status": "available" if config.gemini_api_key else "no_api_key",
                "model_initialized": bool(config.gemini_api_key)
            },
            generator_agent={
                "status": "available" if config.gemini_api_key else "no_api_key",
                "model_initialized": bool(config.gemini_api_key)
            },
            orchestrator={
                "status": "available",
                "config_loaded": bool(config.gemini_api_key)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/test/files/list")
async def list_test_files():
    """List all test files generated by the system"""
    try:
        files = {
            "screenshots": [],
            "generated": [],
            "logs": []
        }
        
        # List screenshots
        screenshots_dir = Path("./screenshots")
        if screenshots_dir.exists():
            files["screenshots"] = [str(f) for f in screenshots_dir.glob("*.png")]
        
        # List generated projects
        generated_dir = Path("./generated")
        if generated_dir.exists():
            files["generated"] = [str(f) for f in generated_dir.iterdir() if f.is_dir()]
        
        # List log files
        log_files = list(Path(".").glob("*.log"))
        files["logs"] = [str(f) for f in log_files]
        
        return files
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File listing failed: {str(e)}")

@app.delete("/test/files/cleanup")
async def cleanup_test_files():
    """Clean up all test files generated by the system"""
    try:
        cleaned_files = []
        
        # Clean screenshots
        screenshots_dir = Path("./screenshots")
        if screenshots_dir.exists():
            for file in screenshots_dir.glob("*.png"):
                file.unlink()
                cleaned_files.append(str(file))
        
        # Clean generated projects
        generated_dir = Path("./generated")
        if generated_dir.exists():
            for project_dir in generated_dir.iterdir():
                if project_dir.is_dir():
                    import shutil
                    shutil.rmtree(project_dir)
                    cleaned_files.append(str(project_dir))
        
        return {
            "status": "success",
            "cleaned_files": cleaned_files,
            "count": len(cleaned_files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# ============================================================================
# EXISTING ENDPOINTS (KEPT FOR COMPATIBILITY)
# ============================================================================

@app.post("/clone", response_model=CloneResult)
async def clone_website(request: CloneRequest):
    """Clone a website endpoint"""
    try:
        orchestrator = get_orchestrator()
        return await orchestrator.clone_website(
            request.url, 
            request.framework, 
            request.options
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Website Cloning System",
        "version": "1.0.0",
        "endpoints": {
            "clone": "POST /clone",
            "health": "GET /health",
            "test_screenshot": "POST /test/screenshot",
            "test_analyzer": "POST /test/analyzer", 
            "test_detector": "POST /test/detector",
            "test_generator": "POST /test/generator",
            "test_pipeline": "POST /test/pipeline",
            "agents_status": "GET /test/agents/status",
            "list_files": "GET /test/files/list",
            "cleanup_files": "DELETE /test/files/cleanup"
        }
    }

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Set up logging
    setup_logging()
    
    # Ensure output directories exist
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs("./screenshots", exist_ok=True)
    os.makedirs("./generated", exist_ok=True)
    
    print("🚀 Starting AI Website Cloning System with Test Endpoints")
    print("📋 Available test endpoints:")
    print("   POST /test/screenshot - Test screenshot capture")
    print("   POST /test/analyzer - Test screenshot analysis")
    print("   POST /test/detector - Test screenshot comparison")
    print("   POST /test/generator - Test code generation")
    print("   POST /test/pipeline - Test full pipeline")
    print("   GET /test/agents/status - Check agent status")
    print("   GET /test/files/list - List test files")
    print("   DELETE /test/files/cleanup - Clean up test files")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)