<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, registerUser, setAuthStorage } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

const title = computed(() => (mode.value === 'login' ? '用户登录' : '用户注册'))
const description = computed(() =>
  mode.value === 'login' ? '请输入账号和密码以继续' : '创建新账号以使用系统功能'
)

const switchMode = (nextMode: 'login' | 'register') => {
  if (mode.value === nextMode) return
  mode.value = nextMode
  errorMsg.value = ''
}

const getErrorMessage = (error: any) => {
  const data = error?.response?.data
  if (!data) {
    return error?.message || '请求失败，请稍后重试'
  }

  if (typeof data === 'string') return data
  if (data.error) return data.error
  if (data.detail) return data.detail

  const fieldKeys = ['username', 'password', 'email', 'non_field_errors']
  for (const key of fieldKeys) {
    const value = data[key]
    if (Array.isArray(value) && value.length > 0) {
      return value[0]
    }
    if (typeof value === 'string') {
      return value
    }
  }

  const firstKey = Object.keys(data)[0]
  if (firstKey) {
    const value = data[firstKey]
    if (Array.isArray(value) && value.length > 0) return value[0]
    if (typeof value === 'string') return value
  }

  return '操作失败，请检查输入信息'
}

const handleSubmit = async () => {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  try {
    if (mode.value === 'login') {
      const res: any = await loginUser({
        username: username.value.trim(),
        password: password.value
      })
      setAuthStorage(res.token, res.user.username)
    } else {
      const res: any = await registerUser({
        username: username.value.trim(),
        password: password.value
      })
      setAuthStorage(res.token, res.user.username)
    }

    window.dispatchEvent(new Event('auth-changed'))
    router.push({ name: 'Data' })
  } catch (e: any) {
    errorMsg.value = getErrorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50 to-amber-50 flex items-center justify-center p-6">
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute -top-20 -left-20 h-64 w-64 rounded-full bg-emerald-200/40 blur-3xl"></div>
      <div class="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-amber-200/40 blur-3xl"></div>
    </div>

    <div class="relative z-10 grid w-full max-w-5xl grid-cols-1 gap-8 lg:grid-cols-2">
      <div class="hidden lg:flex flex-col justify-center gap-4">
        <h1 class="text-4xl font-serif font-semibold text-slate-900 leading-tight">
          TS Studio
        </h1>
        <p class="text-slate-600 leading-relaxed">
          TS Studio 是面向时序数据预测的毕业设计项目，集成数据管理、模型训练与预测可视化能力，支持从数据准备到结果展示的一体化流程。
        </p>
        <div class="flex items-center gap-2 text-sm text-slate-500">
          <Icon icon="lucide:github" class="h-4 w-4" /> TS-Studio 仓库：
          <a
            class="text-emerald-700 hover:text-emerald-800 underline"
            href="https://github.com/hhzzlll/TS-Studio"
            target="_blank"
            rel="noreferrer"
          >
            github.com/hhzzlll/TS-Studio
          </a>
        </div>
        <div class="text-sm text-slate-600">
          合肥工业大学 物联网工程22-2班 胡子龙 2022217577 本科毕业设计
        </div>
      </div>

      <Card class="w-full max-w-md mx-auto shadow-xl border border-white/60 bg-white/80 backdrop-blur">
        <CardHeader class="pb-2">
          <CardTitle class="text-2xl">{{ title }}</CardTitle>
          <CardDescription>{{ description }}</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex gap-2 mb-6">
            <Button
              class="flex-1"
              :variant="mode === 'login' ? 'default' : 'outline'"
              @click="switchMode('login')"
            >
              登录
            </Button>
            <Button
              class="flex-1"
              :variant="mode === 'register' ? 'default' : 'outline'"
              @click="switchMode('register')"
            >
              注册
            </Button>
          </div>

          <div class="space-y-4">
            <div class="space-y-2">
              <label class="text-sm font-medium">用户名</label>
              <input
                v-model="username"
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                placeholder="用户名"
              />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium">密码</label>
              <input
                v-model="password"
                type="password"
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                placeholder="密码"
              />
            </div>

            <div v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</div>

            <Button class="w-full" :disabled="loading" @click="handleSubmit">
              {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
