export const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  (process.env.NODE_ENV === 'production' ? 'https://ichapterwise.com' : 'http://localhost:8000')
