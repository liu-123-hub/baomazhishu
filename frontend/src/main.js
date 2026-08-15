import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)


app.config.errorHandler = (err, instance, info) => {
  console.error('[GlobalError]', info, err)
}

app.use(createPinia())
app.use(router)

app.mount('#app')
