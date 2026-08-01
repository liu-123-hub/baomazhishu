import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)

// 全局错误处理器：捕获未处理的组件异常，避免渲染树整棵卸载导致白屏
app.config.errorHandler = (err, instance, info) => {
  console.error('[GlobalError]', info, err)
}

app.use(createPinia())
app.use(router)

app.mount('#app')
