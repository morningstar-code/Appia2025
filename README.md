# Appia2025 - AI Website Builder

An AI-powered website builder that uses Claude 3.5 Sonnet to generate React and Node.js applications with live preview capabilities.

## Features

- **AI-Powered Generation**: Uses Claude 3.5 Sonnet to analyze prompts and generate appropriate project structures
- **Live Preview**: WebContainer integration for real-time code execution in the browser
- **Step-by-Step Development**: AI breaks down website creation into manageable steps
- **Modern Tech Stack**: React, TypeScript, Tailwind CSS, Monaco Editor
- **Full-Stack Architecture**: Separate backend API and frontend application

## Tech Stack

### Backend
- Node.js with Express
- TypeScript
- Anthropic Claude 3.5 Sonnet API
- CORS enabled for frontend communication

### Frontend
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Monaco Editor for code editing
- WebContainer API for live code execution
- Lucide React for icons

## Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Claude API key from Anthropic

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Appia2025
   ```

2. **Backend Setup**
   ```bash
   cd be
   npm install
   # Create .env file with your Claude API key
   echo "ANTHROPIC_API_KEY=your_claude_api_key_here" > .env
   npm run build
   npm run dev
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:3000

### Environment Variables

Create a `.env` file in the `be` directory:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

## Deployment to Vercel

### 1. Prepare for Deployment

The project is already configured for Vercel deployment with:
- `vercel.json` configuration file
- API routes in `be/api/` directory
- Frontend build configuration

### 2. Deploy to Vercel

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will automatically detect the configuration

3. **Set Environment Variables**
   In your Vercel dashboard:
   - Go to Project Settings → Environment Variables
   - Add: `ANTHROPIC_API_KEY` with your Claude API key
   - Redeploy the project

4. **Update Frontend Configuration**
   After deployment, update the backend URL in `frontend/src/config.ts`:
   ```typescript
   export const BACKEND_URL = process.env.NODE_ENV === 'production' 
     ? "https://your-app-name.vercel.app/api" 
     : "http://localhost:3000"
   ```

### 3. API Endpoints

- `POST /api/template` - Determines project type (React/Node.js) based on prompt
- `POST /api/chat` - Handles AI conversations for code generation

## Project Structure

```
Appia2025/
├── be/                    # Backend API
│   ├── api/              # Vercel API routes
│   │   ├── template.ts   # Project type detection
│   │   └── chat.ts       # AI chat endpoint
│   ├── src/              # Backend source code
│   │   ├── index.ts      # Main server file
│   │   ├── prompts.ts    # AI prompts configuration
│   │   └── defaults/     # Default templates
│   └── package.json
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Application pages
│   │   ├── hooks/        # Custom React hooks
│   │   └── types/        # TypeScript types
│   └── package.json
├── vercel.json           # Vercel deployment config
└── README.md
```

## Usage

1. **Describe Your Website**: Enter a description of the website you want to build
2. **AI Analysis**: The system determines if it's a React or Node.js project
3. **Step Generation**: AI creates a structured development plan
4. **Live Development**: Watch as files are created and code is generated
5. **Real-time Preview**: See your website being built step by step

## API Configuration

The backend uses Anthropic's Claude 3.5 Sonnet model with the following configuration:
- Model: `claude-3-5-sonnet-20241022`
- Max tokens: 200 (template detection), 8000 (chat)
- System prompts for WebContainer environment

## Troubleshooting

### Common Issues

1. **Backend not starting**: Check if port 3000 is available
2. **API timeouts**: Claude API calls can take time; increase timeout values
3. **Build errors**: Ensure all dependencies are installed
4. **Environment variables**: Verify your Claude API key is correctly set

### Development Tips

- Use `npm run dev` for backend development
- Frontend hot-reloads automatically with Vite
- Check browser console for WebContainer errors
- Monitor network tab for API call issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

This project is licensed under the ISC License.

## Latest Update
- Fixed Claude model name to claude-3-5-haiku-20241022
- Updated frontend configuration for Vercel deployment
- Added proper error handling and debugging
- Configured Vercel API timeouts
- Version 1.0.2 - Production Ready
