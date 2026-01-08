<script setup lang="ts">
import { Primitive, type PrimitiveProps } from 'radix-vue'
import { buttonVariants, type ButtonVariants } from '.'
import { cn } from '@/lib/utils'

interface Props {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  as?: string
  asChild?: boolean
}

withDefaults(defineProps<Props>(), {
  as: 'button',
})
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :class="cn(buttonVariants({ variant, size }), $attrs.class ?? '')"
  >
    <slot />
  </Primitive>
</template>
