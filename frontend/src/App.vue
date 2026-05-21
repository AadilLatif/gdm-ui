<template>
  <router-view />
  <div class="toast-container">
    <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]">
      <i :class="toastIcon(t.type)"></i>
      <span class="toast-msg">{{ t.message }}</span>
      <button v-if="t.type === 'error'" class="toast-copy" title="Copy error" @click="copyError(t.message)">
        <i :class="copied === t.id ? 'ri-check-line' : 'ri-file-copy-line'"></i>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from './composables/useToast'

const { toasts } = useToast()
const copied = ref<number | null>(null)

async function copyError(message: string) {
  await navigator.clipboard.writeText(message)
  const id = toasts.value.find(t => t.message === message)?.id ?? null
  copied.value = id
  setTimeout(() => { copied.value = null }, 1500)
}

function toastIcon(type: string) {
  const icons: Record<string, string> = {
    success: 'ri-checkbox-circle-line',
    error: 'ri-error-warning-line',
    info: 'ri-information-line',
  }
  return icons[type] || 'ri-information-line'
}
</script>
