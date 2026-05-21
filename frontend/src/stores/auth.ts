import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/client'
import type { User } from '../types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)

  async function login(username: string, password: string) {
    const { data } = await authApi.login({ username, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchUser()
  }

  async function register(email: string, username: string, password: string) {
    await authApi.register({ email, username, password })
  }

  async function fetchUser() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      user.value = null
    }
  }

  function logout() {
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function init() {
    const token = localStorage.getItem('access_token')
    if (token) {
      loading.value = true
      await fetchUser()
      loading.value = false
    }
  }

  return { user, loading, isAuthenticated, isAdmin, login, register, fetchUser, logout, init }
})
