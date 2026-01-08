<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Icon } from '@iconify/vue'
</script>

<template>
  <div class="h-full flex items-center justify-center p-10">
    <Card class="w-full h-full border-dashed flex flex-col items-center justify-center text-muted-foreground p-10">
      <Icon icon="lucide:wrench" class="w-16 h-16 mb-4 opacity-20" />
      <h3 class="text-lg font-semibold mb-2">开发中</h3>
      <p class="text-sm">预测结果可视化模块正在构建...</p>
      <p class="text-xs mt-4 opacity-50">将在后续版本集成 ECharts 折线对比图</p>
    </Card>
  </div>
</template>
