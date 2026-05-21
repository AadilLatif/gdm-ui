<template>
  <router-view />
  <div class="toast-container">
    <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]">
      <i :class="toastIcon(t.type)"></i> {{ t.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToast } from './composables/useToast'

const { toasts } = useToast()

function toastIcon(type: string) {
  const icons: Record<string, string> = {
    success: 'ri-checkbox-circle-line',
    error: 'ri-error-warning-line',
    info: 'ri-information-line',
  }
  return icons[type] || 'ri-information-line'
}
</script>
