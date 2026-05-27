import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AppLayout.vue'),
      meta: { auth: true },
      children: [
        { path: '', redirect: '/model' },
        { path: 'model', name: 'model', component: () => import('../views/ModelLoaderView.vue') },
        { path: 'warehouse', name: 'warehouse', component: () => import('../views/WarehouseView.vue') },
        { path: 'network', name: 'network', component: () => import('../views/NetworkView.vue') },
        { path: 'scenarios', name: 'scenarios', component: () => import('../views/ScenariosView.vue') },
        { path: 'simulations', name: 'simulations', component: () => import('../views/SimulationView.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
