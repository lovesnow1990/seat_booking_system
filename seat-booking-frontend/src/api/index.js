// seat-booking-frontend/src/api/index.js
import axios from "axios";

// 從環境變數中讀取 API 基礎 URL
const API_BASE_URL = process.env.VUE_APP_API_BASE_URL;

// 創建一個 Axios 實例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    // 您也可以在這裡添加其他通用的標頭，例如認證 token
    // 'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
  timeout: 10000, // 請求超時時間 (例如 10 秒)
});

// 您也可以添加請求或響應攔截器 (interceptors)
apiClient.interceptors.request.use(
  (config) => {
    // 在這裡可以對請求進行一些處理，例如添加認證 token
    // const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    // 在這裡可以對響應進行一些處理
    return response;
  },
  (error) => {
    // 在這裡可以對響應錯誤進行統一處理
    if (error.response) {
      console.error("API Error:", error.response.status, error.response.data);
      // 可以根據 status code 處理不同的錯誤，例如 401 導向登入頁
    }
    return Promise.reject(error);
  }
);

export default apiClient;
