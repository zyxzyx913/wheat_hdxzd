<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, Info, FolderOpen, ImagePlus, ShieldCheck, Wheat, ScanLine, ChartNoAxesCombined, FileText } from 'lucide-vue-next'
import { allModules, moduleDetails } from '../config/modules.js'
import ModelPlaceholder from './ModelPlaceholder.vue'
import WorkspacePage from './WorkspacePage.vue'

// 复用同一状态布局，不提供尚未开放的业务操作或示例结果。
const route = useRoute()
const module = computed(() => allModules.find((item) => item.path === route.path))
const detail = computed(() => moduleDetails[route.path])
// 业务展示预留，所有数值留空，不使用品牌插画伪装用户分析结果。
const display = computed(() => ({
  '/image-recognition': { kind: 'comparison', label: '图像观察档案', title: '一张照片，一份小麦观察记录', text: '原图与识别结果并置留存，识别能力尚未开放。' },
  '/growth-analysis': { kind: 'growth', label: '植株状态档案', title: '观察小麦当下的生长表现', text: '围绕植株、麦穗与生育阶段整理观测，当前暂无经验证的长势结果。' },
  '/growth-prediction': { kind: 'timeline', label: '生长过程档案', title: '沿着时间，理解小麦的生长', text: '预留连续观察与阶段演变展示，当前没有未来生长预测。' },
  '/yield-prediction': { kind: 'yield', label: '田间产出研究', title: '让每一份产量判断有据可循', text: '以地块观测与实测产量为依据，预测能力建设中。' },
  '/market-returns': { kind: 'market', label: '小麦经营档案', title: '连接小麦生产与经营观察', text: '全国小麦价格与收益分析尚未开放，不提供价格或经营结论。' },
  '/reports': { kind: 'report', label: '小麦研究文档', title: '将每一次观察，整理成档案', text: '保留真实图像、观测信息与结果依据，报告读取与生成尚未开放。' },
}[route.path] || { kind: 'general', label: '小麦科研档案', title: module.value.title, text: module.value.description }))
</script>

<template>
  <WorkspacePage v-if="['/image-recognition','/growth-analysis','/growth-prediction','/yield-prediction','/market-returns','/reports'].includes(route.path)" />
  <div v-else class="page-container archive-page">
    <div class="page-heading">
      <div><div class="eyebrow">麦视通 / {{ display.label }}</div><h1>{{ module.title }}</h1><p>{{ module.description }}</p></div>
      <span class="badge"><span class="pending-dot"></span>功能建设中</span>
    </div>
    <div class="notice" role="note"><Info :size="18" /><p>{{ detail.note }}</p></div>
    <section class="archive-showcase">
      <div class="archive-showcase-title"><div><span>{{ display.label }}</span><h2>{{ display.title }}</h2><p>{{ display.text }}</p></div><Wheat :size="37" :stroke-width="1" aria-hidden="true" /></div>
      <div v-if="display.kind === 'comparison'" class="archive-comparison"><div v-for="label in ['小麦原图', '识别结果']" :key="label" class="archive-image-slot"><span>{{ label }}</span><ImagePlus v-if="label==='小麦原图'" :size="31" :stroke-width="1" /><ScanLine v-else :size="31" :stroke-width="1" /><h3>{{ label === '小麦原图' ? '等待图像入口开放' : '等待真实识别结果' }}</h3><p>{{ label === '小麦原图' ? '上传功能建设中，当前未接收图片' : '尚未运行分析，不展示示例掩膜' }}</p></div></div>
      <div v-else-if="display.kind === 'growth'" class="archive-metrics"><article v-for="label in ['当前长势', '植株与麦穗状态', '生育阶段']" :key="label"><span>{{ label }}</span><strong>待观测</strong><p>暂无已验证的分析记录</p></article></div>
      <div v-else-if="display.kind === 'timeline'" class="archive-timeline"><div v-for="(label,index) in ['连续观测', '环境记录', '趋势研究', '结果核验']" :key="label"><span>0{{ index+1 }}</span><h3>{{ label }}</h3><p>功能建设中</p></div><small>研究流程规划 · 非实际生育阶段或预测结果</small></div>
      <template v-else-if="display.kind === 'yield' || display.kind === 'market'"><div class="archive-metrics"><article v-for="label in (display.kind === 'yield' ? ['小麦产量预测', '实测产量参考', '预测适用范围'] : ['全国小麦均价', '生产成本', '收益分析'])" :key="label"><span>{{ label }}</span><strong>待接入</strong><p>暂无可展示的真实数据</p></article></div><div class="archive-chart-empty"><ChartNoAxesCombined :size="28" :stroke-width="1" /><h3>{{ display.kind === 'yield' ? '小麦产量趋势展示预留' : '小麦价格与收益趋势展示预留' }}</h3><p>数据与模型尚未接入，当前不绘制结果曲线。</p></div></template>
      <div v-else-if="display.kind === 'report'" class="archive-report"><FileText :size="40" :stroke-width="1" /><div><span>小麦分析报告 / 档案展示预留</span><h3>暂无可查看的研究档案</h3><p>待接入真实分析记录后呈现报告，当前没有生成文档。</p></div><span class="archive-status">功能建设中</span></div>
    </section>
    <section class="section-block">
      <div class="section-heading"><div><h2>功能概览</h2><p>围绕真实观测，逐步完善分析能力</p></div><component :is="module.icon" :size="21" class="muted-icon" /></div>
      <div class="capability-grid">
        <article v-for="([title, description], index) in detail.items" :key="title" class="capability">
          <span class="capability-number">0{{ index + 1 }}</span>
          <div><h3>{{ title }}</h3><p>{{ description }}</p><span class="small-status">功能建设中</span></div>
        </article>
      </div>
    </section>
    <div class="module-bottom">
      <section v-if="route.path === '/image-recognition'" class="panel image-entry">
        <div class="section-heading"><div><h2>{{ detail.emptyTitle }}</h2><p>从清晰的田间照片开始</p></div></div>
        <div class="upload-placeholder" aria-label="图片上传功能建设中">
          <span class="empty-icon"><ImagePlus :size="30" /></span>
          <h3>上传小麦图片</h3><p>{{ detail.emptyText }}</p>
          <button class="button disabled-button" disabled>选择图片 · 暂未开放</button>
          <small>当前不接收图片，不生成识别结果</small>
        </div>
      </section>
      <section v-else class="panel empty-panel">
        <div class="section-heading"><h2>分析记录</h2><span class="small-status">尚未开放</span></div>
        <div class="empty-state"><span class="empty-icon"><FolderOpen :size="28" /></span><h3>{{ detail.emptyTitle }}</h3><p>{{ detail.emptyText }}</p><RouterLink to="/" class="text-link">返回首页 <ArrowRight :size="15" /></RouterLink></div>
      </section>
      <aside class="panel tips-panel"><span class="tips-icon"><ShieldCheck :size="22" /></span><h2>使用提示</h2><ul><li v-for="tip in detail.tips" :key="tip">{{ tip }}</li></ul>
        <div v-if="detail.links?.length" class="related-links"><RouterLink v-for="link in detail.links" :key="link.path" :to="link.path" class="text-link">{{ link.title }}<ArrowRight :size="15" /></RouterLink></div>
      </aside>
    </div>
    <ModelPlaceholder v-if="route.path === '/image-recognition' || route.path === '/growth-analysis'" />
    <section class="panel workflow"><div class="section-heading"><div><h2>使用流程</h2><p>功能开放后，可按以下步骤开展分析</p></div><span class="small-status">流程规划</span></div><ol class="steps"><li v-for="(step, index) in detail.steps" :key="step"><span class="step-number">{{ index + 1 }}</span><span>{{ step }}</span><ArrowRight v-if="index < detail.steps.length - 1" :size="15" /></li></ol></section>
  </div>
</template>

