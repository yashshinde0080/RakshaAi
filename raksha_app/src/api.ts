// src/api.ts
import axios from 'axios';
import Constants from 'expo-constants';

// Retrieve API URL from Expo config extra field or environment variable
const API_URL = Constants.expoConfig?.extra?.apiUrl ?? process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_URL}/v1`,
  timeout: 10000,
});

export const get = (url: string, params?: any) => api.get(url, { params });
export const post = (url: string, data?: any) => api.post(url, data);
export const put = (url: string, data?: any) => api.put(url, data);
export const del = (url: string) => api.delete(url);

export default api;
