import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import AppShell from './components/AppShell.vue'
import LoginView from './views/LoginView.vue'
import ChatView from './views/ChatView.vue'
import SettingsView from './views/SettingsView.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', component: ChatView },
        { path: 'settings', component: SettingsView },
      ],
    },
  ],
})

createApp(App).use(router).mount('#app')
