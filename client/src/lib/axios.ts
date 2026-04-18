import axios from 'axios';

const api = axios.create({
    // Ensure this uses the variable, and if you use a fallback, 
    // make sure it doesn't break the protocol logic.
    baseURL: import.meta.env.VITE_API_URL,
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
