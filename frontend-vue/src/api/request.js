import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const RETRY_SYMBOL = Symbol('isRetrying')

request.interceptors.request.use(
  (config) => {
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== undefined && res.code !== 200) {
      const message = res.message || '请求失败'
      if (!response.config[RETRY_SYMBOL]) {
        ElMessage.error(message)
      }
      return Promise.reject(new Error(message))
    }
    return res
  },
  (error) => {
    if (error.message.includes('timeout')) {
      ElMessage.error('请求超时，请检查网络连接')
    } else if (error.message.includes('Network Error')) {
      ElMessage.error('网络连接失败，请检查后端服务是否运行')
    } else if (error.response?.status === 401) {
      ElMessage.error('未授权，请重新登录')
    } else if (error.response?.status === 403) {
      ElMessage.error('拒绝访问')
    } else if (error.response?.status === 404) {
      ElMessage.error('请求的资源不存在')
    } else if (error.response?.status >= 500) {
      ElMessage.error('服务器内部错误')
    } else if (!error.config?.[RETRY_SYMBOL]) {
      ElMessage.error(error.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config

    if (!config || !config.retryCount) {
      config.retryCount = 0
    }

    const maxRetryCount = config.maxRetryCount ?? 2
    const retryDelay = config.retryDelay ?? 1000

    const isIdempotent = ['get', 'head', 'options'].includes(config.method?.toLowerCase())
    const isRetryable = config.retryable === true

    if (config.retryCount < maxRetryCount && (isIdempotent || isRetryable)) {
      config.retryCount++
      config[RETRY_SYMBOL] = true

      await new Promise((resolve) => setTimeout(resolve, retryDelay * config.retryCount))

      return request(config)
    }

    return Promise.reject(error)
  }
)

export default request
