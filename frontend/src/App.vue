<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { Button } from './components/ui/button'
import { clearAuthStorage, getAuthState, logoutUser, getSavedSessions, switchToSession, removeSession } from './api'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)
const isAuthRoute = computed(() => route.name === 'Auth')
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
  try {
    await logoutUser()
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
  <div v-if="isAuthRoute" class="min-h-screen bg-background">
    <router-view />
  </div>
  <div v-else class="min-h-screen bg-background flex">
    <!-- Sidebar -->
    <aside class="w-64 border-r bg-card flex flex-col">
      <div class="h-16 flex items-center px-6 border-b">
        <h1 class="font-bold text-xl flex items-center gap-2">
          <Icon icon="lucide:activity" class="h-6 w-6 text-primary" />
          TS-Studio
        </h1>
      </div>
      
      <div class="flex-1 py-4 px-3 space-y-1">
        <template v-for="item in menuItems" :key="item.path">
          <router-link :to="item.path" custom v-slot="{ navigate }">
            <Button 
              :variant="activePath === item.path ? 'secondary' : 'ghost'" 
              class="w-full justify-start gap-2"
              @click="navigate"
            >
              <Icon :icon="item.icon" class="h-4 w-4" />
              {{ item.label }}
            </Button>
          </router-link>
        </template>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-16 border-b flex items-center px-6 bg-card justify-between">
        <h2 class="font-semibold text-lg">{{ currentPageTitle }}</h2>
        <div class="flex items-center gap-4">
          <router-link v-if="!isAuthed" to="/auth">
            <Button variant="outline" size="sm">登录 / 注册</Button>
          </router-link>
          
          <div v-if="isAuthed" class="relative group cursor-pointer flex items-center gap-2">
            <!-- 头像和用户名 -->
            <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
              {{ authUsername.charAt(0).toUpperCase() }}
            </div>
            <span class="text-sm font-medium">{{ authUsername }}</span>
            <Icon icon="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-hover:rotate-180" />
            
            <!-- 下拉菜单 -->
            <div class="absolute right-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <div class="bg-popover text-popover-foreground rounded-md shadow-md border overflow-hidden w-32 flex flex-col">
                <!-- 保存的其他账号 -->
                <div v-if="savedSessions.length > 0" class="py-1 border-b">
                  <div class="px-3 py-1.5 text-xs text-muted-foreground">切换账号</div>
                  <button 
                    v-for="session in savedSessions" 
                    :key="session.username" 
                    @click="handleSwitchAccount(session.username)" 
                    class="w-full px-4 py-2 text-sm text-left hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    <div class="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center text-[10px] text-primary font-bold">
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
      
      <main class="flex-1 p-6 overflow-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>
<style>
</style>
