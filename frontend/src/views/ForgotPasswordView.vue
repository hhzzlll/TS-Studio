<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { requestPasswordReset, confirmPasswordReset } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const router = useRouter()

const username = ref('')
const code = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const loading = ref(false)
const step = ref<'request' | 'confirm'>('request')

const validatePasswordStrength = (pwd: string): string | null => {
  if (pwd.length < 8) return '密码长度不能少于8位'
  if (!/[a-zA-Z]/.test(pwd)) return '密码必须包含至少一个字母'
  if (!/[0-9]/.test(pwd)) return '密码必须包含至少一个数字'
  return null
}

const handleSendCode = async () => {
  errorMsg.value = ''
  successMsg.value = ''
  if (!username.value) {
    errorMsg.value = '请输入用户名'
    return
  }

  loading.value = true
  try {
    await requestPasswordReset({ username: username.value.trim() })
    successMsg.value = '验证码已发送，请检查邮箱'
    step.value = 'confirm'
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || '发送失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleResetPassword = async () => {
  errorMsg.value = ''
  successMsg.value = ''

  if (!username.value || !code.value || !password.value || !confirmPassword.value) {
    errorMsg.value = '请填写完整信息'
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
    await confirmPasswordReset({
      username: username.value.trim(),
      code: code.value.trim(),
      password: password.value,
      confirm_password: confirmPassword.value
    })
    successMsg.value = '密码已重置，请使用新密码登录'
    setTimeout(() => router.push({ name: 'Auth' }), 800)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || '重置失败，请检查验证码'
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
    <Card class="w-full max-w-md relative z-10 shadow-xl border border-white/60 bg-white/80 backdrop-blur">
      <CardHeader>
        <CardTitle>找回密码</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">用户名</label>
            <input v-model="username" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" placeholder="用户名" />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium">验证码</label>
            <input v-model="code" :disabled="step === 'request'" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm disabled:cursor-not-allowed disabled:opacity-60" placeholder="发送验证码后填写" />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium">新密码</label>
            <div class="text-xs text-muted-foreground">至少8位，包含字母和数字</div>
            <input v-model="password" :disabled="step === 'request'" type="password" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm disabled:cursor-not-allowed disabled:opacity-60"  />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium">确认密码</label>
            <input v-model="confirmPassword" :disabled="step === 'request'" type="password" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm disabled:cursor-not-allowed disabled:opacity-60"  />
          </div>

          <div v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</div>
          <div v-if="successMsg" class="text-sm text-emerald-600">{{ successMsg }}</div>

          <Button v-if="step === 'request'" class="w-full" :disabled="loading" @click="handleSendCode">
            {{ loading ? '发送中...' : '发送验证码' }}
          </Button>
          <Button v-else class="w-full" :disabled="loading" @click="handleResetPassword">
            {{ loading ? '处理中...' : '重置密码' }}
          </Button>

          <div class="text-sm text-muted-foreground text-center">
            <router-link to="/auth" class="text-primary hover:underline">返回登录</router-link>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
