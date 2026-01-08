<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Icon } from '@iconify/vue'
import { Button } from './components/ui/button'

const route = useRoute()
const activePath = computed(() => route.path)

const menuItems = [
  { path: '/', icon: 'lucide:file-up', label: '数据管理' },
  { path: '/train', icon: 'lucide:brain-circuit', label: '模型训练' },
  { path: '/predict', icon: 'lucide:line-chart', label: '预测分析' },
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(i => i.path === activePath.value)
  return item ? item.label : 'TS Studio'
})
</script>

<template>
  <div class="min-h-screen bg-background flex">
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
      <header class="h-16 border-b flex items-center px-6 bg-card">
        <h2 class="font-semibold text-lg">{{ currentPageTitle }}</h2>
      </header>
      
      <main class="flex-1 p-6 overflow-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>
<style>
</style>
