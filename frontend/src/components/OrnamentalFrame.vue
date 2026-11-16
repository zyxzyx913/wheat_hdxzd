<script setup>
// 原创卷叶角花，只作装饰，不拦截页面交互。
</script>
<template>
  <span class="ornamental-frame" aria-hidden="true">
    <svg v-for="corner in ['tl','tr','bl','br']" :key="corner" :class="'ornament-'+corner" viewBox="0 0 100 100" fill="none">
      <path d="M8 94V8H94M15 78V15H78" stroke="currentColor" stroke-width=".8" />
      <path d="M22 73C25 55 55 57 56 36C57 24 43 20 37 29C32 38 48 45 49 34M23 74C37 54 55 66 67 50C77 36 68 24 58 25M25 66C21 47 38 45 32 30C26 18 16 25 22 34M32 53C43 48 42 39 39 35M49 57C51 44 63 45 64 37" stroke="currentColor" stroke-width="1.1" />
      <path d="M22 69C13 58 15 49 24 44C30 56 23 61 22 69ZM38 54C35 41 43 37 51 39C50 48 44 48 38 54ZM54 58C61 44 71 45 74 53C68 61 63 58 54 58ZM36 27C34 15 41 12 46 17C46 25 41 24 36 27Z" fill="currentColor" fill-opacity=".3" stroke="currentColor" stroke-width=".5" />
      <path d="M8 8L23 23M18 18L25 15L29 19L26 26L19 29L15 25Z" fill="currentColor" fill-opacity=".4" stroke="currentColor" stroke-width=".7" />
      <circle cx="8" cy="8" r="2.6" fill="currentColor" /><circle cx="78" cy="15" r="1.5" fill="currentColor" />
    </svg>
  </span>
</template>
