<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser, setAuthStorage } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const loading = ref(false)

const validatePasswordStrength = (pwd: string): string | null => {
  if (pwd.length < 8) return '密码长度不能少于8位'
  if (!/[a-zA-Z]/.test(pwd)) return '密码必须包含至少一个字母'
  if (!/[0-9]/.test(pwd)) return '密码必须包含至少一个数字'
  return null
}

const handleRegister = async () => {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

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

  loading.value = true
  try {
    const res: any = await registerUser({
      username: username.value.trim(),
      password: password.value,
      email: email.value.trim()
    })
    setAuthStorage(res.token, res.user.username)
    window.dispatchEvent(new Event('auth-changed'))
    router.push({ name: 'Data' })
  } catch (e: any) {
    const message = e?.response?.data?.username?.[0]
    errorMsg.value = message || '注册失败，请检查输入信息'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[70vh] flex items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>用户注册</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">用户名</label>
            <input v-model="username" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="用户名" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium">邮箱</label>
            <input v-model="email" type="email" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="邮箱" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium">密码</label>
            <input v-model="password" type="password" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="至少8位，包含字母和数字" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium">确认密码</label>
            <input v-model="confirmPassword" type="password" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="请再次输入密码" />
          </div>
          <div v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</div>
          <Button class="w-full" :disabled="loading" @click="handleRegister">
            {{ loading ? '注册中...' : '注册' }}
          </Button>
          <div class="text-sm text-muted-foreground">
            已有账号？
            <router-link to="/login" class="text-primary hover:underline">去登录</router-link>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
