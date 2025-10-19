export const BACKEND_URL = process.env.NODE_ENV === 'production'
  ? '/api'
  : 'http://localhost:3000';
