<script setup>
import { ref, onMounted } from 'vue'
import { ArrowUpRight, ArrowRight, ScanLine, Sprout, ShieldCheck, Wheat, Files, CircleCheck, Clock3, ChartNoAxesCombined, Camera, Leaf, MoveUpRight, Pause, Play } from 'lucide-vue-next'
import { navigation, additionalModules } from '../config/modules.js'
import wheatField from '../assets/wheat-field-brand.png'
import cardScenes from '../assets/agtech-card-scenes.png'
import '../styles/home.css'
import ModelPlaceholder from '../components/ModelPlaceholder.vue'
import { backgroundScenes, backgroundStyle } from '../config/backgroundScenes.js'

// 恢复动态麦田看板；动画仅作品牌展示，不产生监测读数。
const motionPaused = ref(false)
onMounted(() => { motionPaused.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches })
const periods = ['近 7 天', '近 30 天', '近 90 天']
const selectedPeriod = ref(periods[0])
const modules = navigation.slice(1, 6)
const displayDate = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const progress = [
  { name: '工作台与页面导航', note: '页面浏览已开放', state: '已完成', tone: 'complete' },
  { name: '图像识别与长势分析', note: '页面已建立，分析能力完善中', state: '开发中', tone: 'developing' },
  { name: '生长、产量与经营预测', note: '等待数据与研究验证', state: '待启用', tone: 'pending' },
]
</script>

<template>
  <div class="field-dashboard reference-home" :style="backgroundStyle(backgroundScenes.home)">
    <header class="cockpit-welcome"><div><span>麦视通 · 农业智能工作台</span><h2>欢迎来到你的智慧麦田</h2><p>从田间图像到生产与经营观察</p></div><div class="cockpit-date"><span>{{ displayDate }}</span><small>分析服务已接入 · 结果以真实数据为准</small></div></header>
    <section class="cockpit-shortcuts" aria-label="分析快捷入口"><RouterLink v-for="item in modules.slice(0,4)" :key="item.path" :to="item.path"><span><component :is="item.icon" :size="23" :stroke-width="1.5" /></span><div><strong>{{ item.title }}</strong><small>{{ item.status }}</small></div><ArrowUpRight :size="17" /></RouterLink></section>
    <div class="dashboard-primary">
      <section class="field-observation animated-field" :class="{ 'motion-paused': motionPaused }" aria-labelledby="observation-title">
        <img class="observation-photo moving-wheat" :src="wheatField" alt="" aria-hidden="true" width="1983" height="793" fetchpriority="high" />
        <div class="observation-shade" aria-hidden="true"></div><div class="field-grain" aria-hidden="true"></div>
        <div class="observation-heading"><div><span class="field-eyebrow"><Wheat :size="17" />麦视通 · 智慧麦田</span><h1 id="observation-title">看见麦田变化，<br />让决策更有依据。</h1><p>从小麦图像识别出发，连接长势监测、生长预测与农业经营分析。</p></div><span class="preview-pill"><i></i>视觉演示</span></div>
        <div class="observation-tags"><span><Camera :size="14" />图像观察</span><span><Sprout :size="14" />生长研究</span><span><ShieldCheck :size="14" />真实数据为依据</span></div>
        <div class="field-focus" aria-hidden="true"><span class="focus-ring"></span><span class="focus-inner-ring"></span><span class="focus-cross cross-left"></span><span class="focus-cross cross-right"></span><span class="focus-topline"></span><span class="focus-bottomline"></span><span class="field-scan-beam"></span><span class="focus-caption"><ScanLine :size="15" />麦穗主题扫描 · 视觉演示</span></div>
        <span class="field-label label-one"><span class="label-icon"><Leaf :size="14" /></span>观察小麦生长</span>
        <span class="field-label label-two"><span class="label-icon gold"><Wheat :size="14" /></span>扎根田间，智见生长</span>
        <div class="observation-bottom"><div class="observation-actions"><RouterLink to="/image-recognition" class="field-button primary">开始图像分析<ArrowUpRight :size="16" /></RouterLink><RouterLink to="/growth-analysis" class="field-button secondary">查看长势分析<ArrowRight :size="16" /></RouterLink></div><p><span></span>品牌视觉动效，非实时监测；分析功能建设中</p></div>
        <button class="field-motion-toggle" :aria-label="motionPaused ? '播放麦田动效' : '暂停麦田动效'" :aria-pressed="motionPaused" @click="motionPaused = !motionPaused"><Play v-if="motionPaused" :size="14" /><Pause v-else :size="14" />{{ motionPaused ? '播放动效' : '暂停动效' }}</button>
      </section>
      <section class="quick-tools" aria-labelledby="quick-tools-title">
        <div class="dashboard-section-heading"><h2 id="quick-tools-title">探索你的智慧麦田</h2><span>从观察到决策</span></div>
        <div class="photo-tools"><RouterLink v-for="(item,index) in modules" :key="item.path" :to="item.path" class="photo-tool" :class="'photo-tool-'+index"><img v-if="index===0" :src="wheatField" alt="" aria-hidden="true" loading="lazy" /><span v-else class="photo-scene" :class="'scene-'+index" :style="{ backgroundImage: `url(${cardScenes})` }" aria-hidden="true"></span><span class="photo-tool-state"><i></i>建设中</span><span class="photo-tool-symbol"><component :is="item.icon" :size="25" :stroke-width="1.4" /></span><span class="photo-tool-name">{{ item.title }}<MoveUpRight :size="15" /></span></RouterLink></div>
      </section>
      <section class="analysis-history" aria-labelledby="history-title"><div class="dashboard-section-heading"><div><h2 id="history-title">最近分析记录</h2><p>让每一次田间观察，都有迹可循</p></div><RouterLink to="/reports" class="dashboard-link">我的报告<ArrowUpRight :size="14" /></RouterLink></div><div class="history-empty"><span class="history-empty-icon"><Files :size="25" :stroke-width="1.3" /></span><div><h3>你的下一份田间记录，从这里开始</h3><p>尚未接入可查看的历史记录，不展示示例分析结果。</p></div><RouterLink to="/image-recognition" class="history-action">前往图像识别<ArrowRight :size="15" /></RouterLink></div></section>
    </div>
    <aside class="dashboard-insights" aria-label="观测信息与功能状态">
      <section class="insight-card growth-observations" aria-labelledby="growth-panel-title"><div class="dashboard-section-heading"><h2 id="growth-panel-title">生长观测</h2><span class="insight-icon"><ChartNoAxesCombined :size="19" :stroke-width="1.5" /></span></div><div class="observation-chart-empty" role="note" aria-label="尚未接入生长观测数据"><div class="empty-grid" aria-hidden="true"><span></span><span></span><span></span><span></span></div><span class="chart-empty-icon"><Sprout :size="30" :stroke-width="1.2" /></span><h3>等待第一份生长观测</h3><p>尚未接入连续观测数据<br />不生成趋势曲线或预测结论</p><span class="period-caption">{{ selectedPeriod }} · 数据待接入</span></div><div class="period-tabs" role="group" aria-label="观测时间范围"><button v-for="period in periods" :key="period" :class="{active:selectedPeriod===period}" :aria-pressed="selectedPeriod===period" @click="selectedPeriod=period">{{ period }}</button></div></section>
      <section class="insight-card observation-advice" aria-labelledby="advice-title"><div class="dashboard-section-heading"><h2 id="advice-title">让观察更有价值</h2><Camera :size="19" :stroke-width="1.5" /></div><p class="advice-intro">从一张清晰的小麦照片开始</p><div class="advice-links"><RouterLink to="/image-recognition" class="advice-pill pale"><span>了解照片拍摄与识别说明</span><ArrowRight :size="15" /></RouterLink><RouterLink to="/growth-analysis" class="advice-pill sage"><span>观察覆盖与颜色，关注生长变化</span><ArrowRight :size="15" /></RouterLink><RouterLink to="/reports" class="advice-pill green"><span>整理真实记录，留存每一次观察</span><ArrowRight :size="15" /></RouterLink></div><span class="advice-footnote">通用观测提示，不是个性化农事诊断</span></section>
      <section class="insight-card function-readiness" aria-labelledby="readiness-title"><div class="dashboard-section-heading"><h2 id="readiness-title">系统功能进度</h2><span class="subtle-label">真实呈现</span></div><div class="readiness-list"><div v-for="item in progress" :key="item.name" class="readiness-row"><span class="readiness-dot" :class="item.tone"><CircleCheck v-if="item.tone==='complete'" :size="17" /><Clock3 v-else-if="item.tone==='developing'" :size="17" /><span v-else></span></span><div><h3>{{ item.name }}</h3><p>{{ item.note }}</p></div><span class="readiness-label" :class="item.tone">{{ item.state }}</span></div></div><div class="readiness-note"><ShieldCheck :size="15" /><p>功能进度不代表分析效果。当前不提供长势、产量或市场价格预测。</p></div></section>
      <ModelPlaceholder />
      <section class="insight-card cockpit-stage"><div class="dashboard-section-heading"><h2>小麦生长阶段</h2><Sprout :size="19" /></div><div class="stage-points" aria-hidden="true"><i></i><i></i><i></i><i></i></div><p>等待生育阶段数据接入</p></section>
      <RouterLink to="/market-returns" class="insight-card cockpit-market"><Wheat :size="23" /><div><h2>全国小麦市场</h2><p>价格与收益 · 等待数据接入</p></div><ArrowUpRight :size="18" /></RouterLink>
    </aside>
    <section class="dashboard-research"><span><Wheat :size="16" />扎根田间，智见生长</span><div><RouterLink v-for="item in additionalModules" :key="item.path" :to="item.path">{{ item.title }}<ArrowUpRight :size="12" /></RouterLink></div></section>
    <div class="reference-photo-credit"><span>背景：农田全景 · AI 生成的品牌场景</span><span>装饰背景 · 非用户地块观测</span></div>
  </div>
</template>

