import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import './styles.css'
import './styles/botanical.css'
import './styles/classical-oil.css'

// 注册共享界面与路由；仅图像识别页调用独立的 Python 分析服务。
createApp(App).use(router).mount('#app')
import './styles/field-motion.css'
import './styles/product-layers.css'
import './styles/glass-theme.css'
import './styles/dark-cockpit.css'
import './styles/agriculture-scenes.css'
import './styles/ui-unification.css'
import './styles/reference-unified.css'
