<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, setAuthStorage } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const router = useRouter()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

const handleLogin = async () => {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  try {
    const res: any = await loginUser({
      username: username.value.trim(),
      password: password.value
    })
    setAuthStorage(res.token, res.user.username)
    window.dispatchEvent(new Event('auth-changed'))
    router.push({ name: 'Data' })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || '登录失败，请检查账号密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[70vh] flex items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>用户登录</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">用户名</label>
            <input v-model="username" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="用户名" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium">密码</label>
            <input v-model="password" type="password" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="密码" />
          </div>
          <div v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</div>
          <Button class="w-full" :disabled="loading" @click="handleLogin">
            {{ loading ? '登录中...' : '登录' }}
          </Button>
          <div class="text-sm text-muted-foreground">
            <router-link to="/forgot-password" class="text-primary hover:underline">忘记密码？</router-link>
          </div>
          <div class="text-sm text-muted-foreground">
            没有账号？
            <router-link to="/register" class="text-primary hover:underline">去注册</router-link>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
