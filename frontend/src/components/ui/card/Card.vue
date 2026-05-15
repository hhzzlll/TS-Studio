<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: string
}>()
</script>

<template>
  <div
    :class="
      cn(
        'data-card rounded-lg border bg-card text-card-foreground shadow-sm transition-shadow duration-200',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
