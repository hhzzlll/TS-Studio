<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: string
}>()
</script>

<template>
  <h3
    :class="
      cn(
        'text-xl font-bold leading-tight tracking-normal text-slate-900',
        props.class
      )
    "
  >
    <slot />
  </h3>
</template>
