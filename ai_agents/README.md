# AI-Powered Website Cloning System

## Overview
This project is an advanced, modular AI-powered website cloning system. It leverages FastAPI, Playwright, Google Gemini (Generative AI), and a suite of specialized agents to analyze, describe, and generate runnable clones of websites. The system is designed for robustness, extensibility, and production-readiness.

## Features
- **Automated Website Cloning**: Analyze and clone any website into a runnable project.
- **Modular Agent Architecture**: AnalyzerAgent, GeneratorAgent, ScreenshotAgent, and more, each with a focused responsibility.
- **AI-Powered Analysis**: Uses Gemini (Google Generative AI) for deep vision and code analysis.
- **Dynamic Code Generation**: Generates real, production-quality code for React, Next.js, Vue, Angular, and vanilla JS/CSS/HTML.
- **Robust Fallbacks**: Ensures every project is runnable, with minimal templates for missing essentials.
- **Centralized Config**: All configuration and core data classes are centralized for maintainability.
- **Extensive Logging**: Debug and info logs for every step of the process.

## Architecture
- **FastAPI**: Provides a REST API for submitting clone requests and managing the system.
- **Playwright**: Used for website automation and screenshot capture.
- **Gemini (Google Generative AI)**: Powers the AnalyzerAgent and GeneratorAgent for vision and code generation.
- **Agents**: Modular Python classes for each step (analysis, code generation, screenshot, etc.).
- **Output Structure**: Each cloned project is saved in a unique subfolder under `cloned_sites/`.

## Requirements
- Python 3.8+
- See `requirements.txt` for all dependencies.
- Tesseract OCR (for pytesseract):
  - Ubuntu: `sudo apt-get install tesseract-ocr`
  - Arch: `sudo pacman -S tesseract`

## Setup
1. **Clone the repository**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install Playwright browsers**:
   ```bash
   playwright install
   ```
4. **Set up environment variables** (e.g., Gemini API key) in a `.env` file:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key
   ```
5. **(Optional) Install Tesseract for OCR**

## Running the API Server
From the `ai_clone_system` directory:
```bash
uvicorn main:app --reload
```
The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Usage Example
Send a POST request to `/clone`:
```bash
curl -X POST "http://127.0.0.1:8000/clone" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```
- The system will analyze the site, generate code, and save the result in `cloned_sites/`.

## Output
- Each cloned project is saved in a unique subfolder under `cloned_sites/`.
- Logs and analysis results are available in `analyzer_agent.log`.

## Troubleshooting
- **Gemini API errors**: Ensure your API key is valid and set in `.env`.
- **Playwright errors**: Run `playwright install` and ensure browsers are installed.
- **Tesseract errors**: Make sure Tesseract is installed and in your PATH.
- **Permission errors**: Run with appropriate permissions or adjust output directory.

## Extending the System
- Add new agents in `agents/` for additional functionality.
- Update prompts and logic in `AnalyzerAgent` and `GeneratorAgent` for improved results.
- Centralize new config/data classes in `config/system_config.py`.

## License
MIT License (or specify your license here) 