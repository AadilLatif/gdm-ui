import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import 'remixicon/fonts/remixicon.css'
import './styles/main.css'
import './styles/power-icons.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Init auth before mounting
const auth = useAuthStore()
auth.init().then(() => {
  app.mount('#app')
})
