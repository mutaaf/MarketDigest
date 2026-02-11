import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 120s for digest runs
})

export default api
