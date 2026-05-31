<!-- 自定义 SVG 图标组件 — 简洁几何风格，无AI味 -->
<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 22 },
  color: { type: String, default: 'currentColor' },
})
</script>

<template>
  <!-- 持有 - 简洁钱包 -->
  <svg v-if="name === 'wallet'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <path d="M16 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" fill="currentColor" stroke="none" opacity="0.15" />
    <path d="M16 10a2 2 0 1 1 0 4" />
  </svg>

  <!-- 持有建议 - 灯泡/分析 -->
  <svg v-else-if="name === 'bulb'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 18h6M10 22h4" />
    <path d="M12 2a7 7 0 0 0-4.5 12.26c.32.27.5.67.5 1.09V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-1.65c0-.42.18-.82.5-1.09A7 7 0 0 0 12 2Z" />
    <path d="M12 7v3" stroke-width="2" />
    <circle cx="12" cy="13" r="0.5" fill="currentColor" stroke="none" />
  </svg>

  <!-- 我的 - 简洁人像 -->
  <svg v-else-if="name === 'person'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
  </svg>

  <!-- 返回箭头 -->
  <svg v-else-if="name === 'arrow-back'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>

  <!-- 添加 -->
  <svg v-else-if="name === 'plus'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>

  <!-- 删除/关闭 -->
  <svg v-else-if="name === 'close'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>

  <!-- 右箭头 -->
  <svg v-else-if="name === 'chevron-right'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="m9 18 6-6-6-6" />
  </svg>

  <!-- 搜索 -->
  <svg v-else-if="name === 'search'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.3-4.3" />
  </svg>

  <!-- 涨/上升 -->
  <svg v-else-if="name === 'trend-up'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>

  <!-- 跌/下降 -->
  <svg v-else-if="name === 'trend-down'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
    <polyline points="17 18 23 18 23 12" />
  </svg>

  <!-- 图表 -->
  <svg v-else-if="name === 'chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
    <path d="M3 3v18h18" />
    <path d="m7 16 4-7 3 5 4-6" />
  </svg>

  <!-- 饼图 -->
  <svg v-else-if="name === 'pie-chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
    <path d="M22 12A10 10 0 0 0 12 2v10l10-10Z" />
  </svg>

  <!-- 默认占位 -->
  <span v-else>{{ name }}</span>
</template>
