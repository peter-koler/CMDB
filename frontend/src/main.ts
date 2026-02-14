import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { permission, role } from './directives/permission'
import 'ant-design-vue/dist/reset.css'
import './assets/styles/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)
app.use(i18n)

app.directive('permission', permission)
app.directive('role', role)

app.mount('#app')
