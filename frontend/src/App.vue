<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Wheat, Search, ChevronRight, ChevronDown, UserRound, Files, ArrowUpRight } from 'lucide-vue-next'
import { navigation } from './config/modules.js'
import './styles/workspace.css'

const route = useRoute()
const userMenu = ref(null)
const searchQuery = ref('')
// 搜索仅查找现有功能页面，不请求或伪造业务数据。
const searchResults = computed(() => searchQuery.value.trim()
  ? navigation.filter(item => (item.title + (item.description || '')).includes(searchQuery.value.trim()))
  : [])
const focusMain = () => {
  const main = document.getElementById('main-content')
  main?.focus()
  main?.scrollIntoView({ block: 'start' })
}
watch(() => route.path, () => { searchQuery.value = ''; userMenu.value?.removeAttribute('open') })
const closeOnEscape = (event) => {
  if (event.key === 'Escape') { searchQuery.value = ''; userMenu.value?.removeAttribute('open') }
}
onMounted(() => window.addEventListener('keydown', closeOnEscape))
onUnmounted(() => window.removeEventListener('keydown', closeOnEscape))
</script>

<template>
  <div class="agtech-shell reference-theme dark-cockpit" :class="route.path === '/' ? 'animated-home-shell' : 'p2-data-shell'">
    <a class="skip-link" href="#main-content" @click.prevent="focusMain">跳转到主内容</a>
    <RouterLink to="/" class="agtech-brand" aria-label="麦视通首页"><span class="agtech-logo"><Wheat :size="27" :stroke-width="1.7" /></span><span><strong>麦视通</strong><small>小麦智能分析与预测平台</small></span></RouterLink>
    <header class="agtech-header">
      
      <div class="cockpit-system-title">小麦智能分析与预测平台<small>{{ route.meta.title }}</small></div>
      <div class="page-search">
        <Search :size="20" :stroke-width="1.6" aria-hidden="true" /><input v-model="searchQuery" type="search" placeholder="搜索功能页面..." aria-label="搜索功能页面" aria-controls="page-search-results" :aria-expanded="Boolean(searchQuery.trim())" autocomplete="off" />
        <span class="search-hint" aria-hidden="true">功能导航</span>
        <div v-if="searchQuery.trim()" id="page-search-results" class="search-results" aria-live="polite">
          <template v-if="searchResults.length"><RouterLink v-for="item in searchResults" :key="item.path" :to="item.path"><component :is="item.icon" :size="17" /><span>{{ item.title }}</span><ArrowUpRight :size="15" /></RouterLink></template>
          <p v-else>没有匹配的功能页面</p>
        </div>
      </div>
      <div class="agtech-header-end">
        <span class="agtech-runtime"><i></i>页面运行正常</span>
        <details ref="userMenu" class="account-menu">
          <summary aria-label="打开用户入口"><span class="account-avatar"><UserRound :size="23" :stroke-width="1.5" /></span><span class="account-name"><strong>本地访客</strong><small>欢迎来到麦视通</small></span><ChevronDown :size="14" /></summary>
          <div class="account-popover"><strong>本地访客</strong><p>当前未启用账号登录</p><RouterLink to="/reports"><Files :size="16" />我的报告<ChevronRight :size="14" /></RouterLink></div>
        </details>
      </div>
    </header>
    <div class="navigation-bar">
      <nav class="pill-navigation" aria-label="主导航"><RouterLink v-for="item in navigation" :key="item.path" :to="item.path" exact-active-class="selected"><component :is="item.icon" :size="17" :stroke-width="1.7" /><span>{{ item.title }}</span></RouterLink></nav>
      <span class="workspace-caption">小麦生长 · 观测档案</span>
    </div>
    <main id="main-content" tabindex="-1" class="agtech-main"><RouterView /></main>
    <footer class="agtech-footer"><span>麦视通 · 让田间观察更有价值</span><span>以真实观测为依据，分析服务逐步开放中</span></footer>
  </div>
</template>



