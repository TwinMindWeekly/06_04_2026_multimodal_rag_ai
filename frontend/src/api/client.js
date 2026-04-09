import axios from 'axios';

// Base API URL from environment, fallback to localhost:8000/api
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach language header for localized backend errors
client.interceptors.request.use((config) => {
  const lang = localStorage.getItem('i18nextLng') || 'en';
  config.headers['Accept-Language'] = lang;
  return config;
});

export default client;
