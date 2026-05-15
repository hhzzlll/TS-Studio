<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, registerUser, setAuthStorage } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const loading = ref(false)

const title = computed(() => (mode.value === 'login' ? '用户登录' : '用户注册'))

const validatePasswordStrength = (pwd: string): string | null => {
  if (pwd.length < 8) return '密码长度不能少于8位'
  if (!/[a-zA-Z]/.test(pwd)) return '密码必须包含至少一个字母'
  if (!/[0-9]/.test(pwd)) return '密码必须包含至少一个数字'
  return null
}
const switchMode = (nextMode: 'login' | 'register') => {
  if (mode.value === nextMode) return
  mode.value = nextMode
  errorMsg.value = ''
  confirmPassword.value = ''
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

  if (mode.value === 'register') {
    if (!email.value) {
      errorMsg.value = '请输入邮箱'
      return
    }
    if (!confirmPassword.value) {
      errorMsg.value = '请再次输入密码'
      return
    }
    if (password.value !== confirmPassword.value) {
      errorMsg.value = '两次输入的密码不一致'
      return
    }
    const strengthError = validatePasswordStrength(password.value)
    if (strengthError) {
      errorMsg.value = strengthError
      return
    }
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
        password: password.value,
        email: email.value.trim()
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
  <div class="auth-stage min-h-screen flex items-center justify-center p-6">
    <div class="absolute inset-0 pointer-events-none opacity-60">
      <div class="absolute left-12 top-12 h-px w-72 bg-gradient-to-r from-primary/40 to-transparent"></div>
      <div class="absolute bottom-16 right-10 h-px w-80 bg-gradient-to-l from-orange-400/40 to-transparent"></div>
    </div>

    <div class="relative z-10 grid w-full max-w-5xl grid-cols-1 gap-8 lg:grid-cols-2">
      <div class="hidden lg:flex flex-col justify-center gap-5">
        <div class="inline-flex w-fit items-center gap-2 rounded-lg border border-teal-200/70 bg-white/60 px-3 py-2 text-sm font-semibold text-teal-800 shadow-sm">
          <Icon icon="lucide:activity" class="h-4 w-4" />
          Time Series Forecasting
        </div>
        <h1 class="text-5xl font-black text-slate-950 leading-tight">
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

      <Card class="w-full max-w-md mx-auto shadow-xl border border-white/70 bg-white/85 backdrop-blur">
        <CardHeader class="pb-2">
          <CardTitle class="text-2xl">{{ title }}</CardTitle>
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
              <div class="text-xs text-slate-500">至少8位，包含字母和数字</div>
              <input
                v-model="password"
                type="password"
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                :placeholder="mode === 'register' ? '至少8位，包含字母和数字' : '密码'"
              />
            </div>

            <div v-if="mode === 'register'" class="space-y-2">
              <label class="text-sm font-medium">邮箱</label>
              <input
                v-model="email"
                type="email"
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                placeholder="邮箱"
              />
            </div>

            <div v-if="mode === 'register'" class="space-y-2">
              <label class="text-sm font-medium">确认密码</label>
              <input
                v-model="confirmPassword"
                type="password"
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                placeholder="请再次输入密码"
              />
            </div>

            <div v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</div>

            <Button class="w-full" :disabled="loading" @click="handleSubmit">
              {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
            </Button>
            <div v-if="mode === 'login'" class="text-sm text-slate-500 text-center">
              <router-link to="/forgot-password" class="text-emerald-700 hover:text-emerald-800 underline">
                忘记密码？
              </router-link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
