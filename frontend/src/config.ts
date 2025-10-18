export const BACKEND_URL = process.env.NODE_ENV === 'production' 
  ? "https://your-app-name.vercel.app/api" 
  : "http://localhost:3000"