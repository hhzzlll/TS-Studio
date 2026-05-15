<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: string
}>()
</script>

<template>
  <div
    :class="cn('card-header flex flex-col space-y-1.5 p-5', props.class)"
  >
    <slot />
  </div>
</template>
