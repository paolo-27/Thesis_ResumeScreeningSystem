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

// Request interceptor – attach the JWT from sessionStorage
api.interceptors.request.use((config) => {
    const token = sessionStorage.getItem('veridian_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor – on 401 (expired / invalid token), clear the
// session and force the user back to the login page.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            sessionStorage.removeItem('veridian_token');
            sessionStorage.removeItem('veridian_user');
            window.location.href = '/admin/login';
        }
        return Promise.reject(error);
    }
);

export default api;
