<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { Button } from './components/ui/button'
import { clearAuthStorage, getAuthState, logoutUser, getSavedSessions, switchToSession, removeSession, deleteAccount } from './api'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)
const isMinimalRoute = computed(() => route.name === 'Auth' || route.name === 'ForgotPassword')
const isAuthed = ref(false)
const authUsername = ref('')
const savedSessions = ref<any[]>([])

const menuItems = [
  { path: '/', icon: 'lucide:file-up', label: '数据管理' },
  { path: '/analysis', icon: 'lucide:bar-chart-2', label: '统计分析' },
  { path: '/train', icon: 'lucide:brain-circuit', label: '模型训练' },
  { path: '/predict', icon: 'lucide:line-chart', label: '预测分析' },
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(i => i.path === activePath.value)
  return item ? item.label : 'TS Studio'
})

const syncAuth = () => {
  const { token, username } = getAuthState()
  isAuthed.value = !!token
  authUsername.value = username || ''
  const allSessions = getSavedSessions()
  // filter out current user from savedSessions to show effectively "other" accounts
  savedSessions.value = allSessions.filter((s: any) => s.username !== username)
}

const handleSwitchAccount = (targetUsername: string) => {
  const success = switchToSession(targetUsername)
  if (success) {
    syncAuth()
    window.dispatchEvent(new Event('auth-changed'))
    router.push('/')
  }
}

const handleLogout = async (completelyRemove: boolean = false) => {
  if (completelyRemove) {
    const confirmed = window.confirm('确定要注销账号吗？此操作不可恢复。')
    if (!confirmed) {
      return
    }
  }
  try {
    if (completelyRemove) {
      await deleteAccount()
    } else {
      await logoutUser()
    }
  } catch (e) {
    // Ignore API errors and clear local auth state anyway
  } finally {
    if (completelyRemove && authUsername.value) {
      removeSession(authUsername.value)
    }
    clearAuthStorage()
    syncAuth()
    window.dispatchEvent(new Event('auth-changed'))
    router.push({ name: 'Auth' })
  }
}

onMounted(() => {
  syncAuth()
  window.addEventListener('auth-changed', syncAuth)
})

onUnmounted(() => {
  window.removeEventListener('auth-changed', syncAuth)
})
</script>

<template>
  <div v-if="isMinimalRoute" class="min-h-screen bg-background">
    <router-view />
  </div>
  <div v-else class="app-shell min-h-screen bg-background flex">
    <!-- Sidebar -->
    <aside class="app-sidebar relative w-64 border-r border-white/10 flex flex-col overflow-hidden">
      <div class="relative z-10 h-20 flex items-center px-5 border-b border-white/10">
        <h1 class="font-bold text-xl flex items-center gap-3">
          <span class="app-brand-mark flex h-10 w-10 items-center justify-center rounded-lg">
            <Icon icon="lucide:activity" class="h-5 w-5 text-white" />
          </span>
          <span class="leading-tight">
            <span class="block text-white">TS-Studio</span>
          </span>
        </h1>
      </div>
      
      <div class="relative z-10 flex-1 py-5 px-3 space-y-2">
        <template v-for="item in menuItems" :key="item.path">
          <router-link :to="item.path" custom v-slot="{ navigate }">
            <Button 
              variant="ghost"
              :class="['app-nav-button w-full justify-start gap-3', activePath === item.path ? 'is-active' : '']"
              @click="navigate"
            >
              <Icon :icon="item.icon" class="h-4 w-4 shrink-0" />
              {{ item.label }}
            </Button>
          </router-link>
        </template>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-w-0">
      <header class="app-topbar sticky top-0 z-20 h-16 border-b flex items-center px-7 justify-between">
        <div>
          <h2 class="font-bold text-xl text-slate-900">{{ currentPageTitle }}</h2>
          <p class="text-xs text-muted-foreground">时间序列预测实验平台</p>
        </div>
        <div class="flex items-center gap-4">
          <router-link v-if="!isAuthed" to="/auth">
            <Button variant="outline" size="sm">登录 / 注册</Button>
          </router-link>
          
          <div v-if="isAuthed" class="relative group cursor-pointer flex items-center gap-2 rounded-lg border bg-white/70 px-2 py-1 shadow-sm">
            <!-- 头像和用户名 -->
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold">
              {{ authUsername.charAt(0).toUpperCase() }}
            </div>
            <span class="text-sm font-medium">{{ authUsername }}</span>
            <Icon icon="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-hover:rotate-180" />
            
            <!-- 下拉菜单 -->
            <div class="absolute right-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <div class="bg-popover text-popover-foreground rounded-lg shadow-xl border overflow-hidden w-36 flex flex-col">
                <!-- 保存的其他账号 -->
                <div v-if="savedSessions.length > 0" class="py-1 border-b">
                  <div class="px-3 py-1.5 text-xs text-muted-foreground">切换账号</div>
                  <button 
                    v-for="session in savedSessions" 
                    :key="session.username" 
                    @click="handleSwitchAccount(session.username)" 
                    class="w-full px-4 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    <div class="w-5 h-5 rounded-md bg-primary/20 flex items-center justify-center text-[10px] text-primary font-bold">
                      {{ session.username.charAt(0).toUpperCase() }}
                    </div>
                    <span class="truncate">{{ session.username }}</span>
                  </button>
                  <div class="h-px bg-border my-1"></div>
                </div>
                
                <button @click="handleLogout(false)" class="px-4 py-2 text-sm text-left hover:bg-muted transition-colors">退出账号</button>
                <div class="h-px bg-border"></div>
                <button @click="handleLogout(true)" class="px-4 py-2 text-sm text-left text-destructive hover:bg-destructive/10 transition-colors">注销账号</button>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      <main class="content-surface flex-1 p-7 overflow-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>
<style>
</style>
