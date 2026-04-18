import axios from 'axios';

// Get the URL from env, default to local if missing
let baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// SAFETY FILTER: If we are not on localhost, force the URL to be https
if (!baseURL.includes('127.0.0.1') && !baseURL.includes('localhost')) {
    baseURL = baseURL.replace('http://', 'https://');
}

const api = axios.create({
    baseURL: baseURL,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('veridian_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;
