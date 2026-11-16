<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, ScanLine, Download, Eye, ShieldCheck, Clock3, CalendarDays, SlidersHorizontal, ArrowUpRight } from 'lucide-vue-next'
import { allModules } from '../config/modules.js'
import VisualEmpty from './VisualEmpty.vue'
import ModelPlaceholder from './ModelPlaceholder.vue'
import { backgroundScenes, backgroundStyle } from '../config/backgroundScenes.js'
const route = useRoute()
const module = computed(() => allModules.find(item => item.path === route.path))
const kind = computed(() => route.path.slice(1))
const backgroundScene = computed(() => backgroundScenes[kind.value] || backgroundScenes.home)
const settings = {
  'image-recognition': {description:'从一张照片，开始一次田间观察。',status:'开发中',control:'图像与分析',main:'图像结果对照',metrics:['图像尺寸','植被覆盖率','分析耗时'],side:'分析状态'},
  'growth-analysis': {description:'以可见观测，了解小麦当前表现。',status:'开发中',control:'观测条件',main:'小麦当前状态',metrics:['植被覆盖率','生长阶段','状态等级'],side:'观测指标'},
  'growth-prediction': {description:'沿着时间，关注下一阶段的生长变化。',status:'待启用',control:'预测条件',main:'生长变化趋势',metrics:['预计成熟时间','预测时间范围','数据更新时间'],side:'预测概况'},
  'yield-prediction': {description:'结合真实观测，研究小麦田间产出。',status:'待启用',control:'地块条件',main:'产量变化趋势',metrics:['预计亩产','实测亩产','评估状态'],side:'产量概况'},
  'market-returns': {description:'连接全国市场与农业经营记录。',status:'待启用',control:'经营条件',main:'未来 30 天价格趋势',metrics:['全国小麦均价','预计收益','生产成本'],side:'经营概况'},
  'reports': {description:'让每一次观察，都有迹可循。',status:'待启用',control:'报告筛选',main:'我的分析报告',metrics:['报告状态','数据来源','最近更新时间'],side:'报告概况'},
}
const config = computed(() => settings[kind.value])
// 所有读数使用空值；禁用尚未接通的业务操作，不绘制示例成绩。
</script>
<template>
  <div class="p2-workspace reference-extension" :data-scene="kind" :style="backgroundStyle(backgroundScene)">
    <header class="workbench-heading"><span class="reference-title-icon"><component :is="module.icon" :size="30" :stroke-width="1.5" /></span><div><span class="workbench-breadcrumb">麦视通工作台 / {{ module.title }}</span><h1>{{ module.title }}</h1><p>{{ config.description }}</p></div><span class="workbench-status" :class="{developing:config.status==='开发中'}"><i></i>{{ config.status }}</span></header>
    <div class="workbench-layout">
      <aside class="workbench-control wb-panel">
        <div class="wb-panel-heading"><h2>{{ config.control }}</h2><SlidersHorizontal :size="17" /></div>
        <template v-if="kind==='image-recognition'"><div class="workbench-upload"><Upload :size="28" :stroke-width="1.2" /><strong>上传小麦图像</strong><small>等待图像入口开放</small><button disabled class="wb-button">选择图片</button></div><div class="condition-field"><span>分析方式</span><div>植被区域观察<span>待启用</span></div></div><button disabled class="wb-button primary"><ScanLine :size="15" />开始分析</button></template>
        <template v-else><div v-for="label in (kind==='market-returns' ? ['价格口径','成本记录','经营面积'] : kind==='reports' ? ['报告类型','记录日期','数据来源'] : ['地块记录','观测日期','生育阶段'])" :key="label" class="condition-field"><span>{{ label }}</span><div>{{ label === '价格口径' ? '全国平均小麦价格' : '等待数据接入' }}</div></div><button disabled class="wb-button primary">{{ kind==='reports' ? '查询报告' : '开始分析' }}</button></template>
        <div class="wb-control-note"><ShieldCheck :size="15" /><span>功能建设中<br />当前不接收或处理业务数据</span></div>
        <RouterLink to="/reports" v-if="kind!=='reports'" class="wb-related">我的报告<ArrowUpRight :size="14" /></RouterLink>
      </aside>
      <div class="workbench-main">
        <section v-if="kind==='yield-prediction'" class="yield-main-card wb-panel"><span>预计亩产</span><div><strong>—</strong><small>千克 / 亩</small></div><span class="metric-wait">等待数据接入</span></section>
        <section v-if="kind==='market-returns'" class="economy-top"><article v-for="label in ['当前全国小麦价格','收益估算']" :key="label" class="wb-panel metric-tile"><span>{{ label }}</span><strong>—</strong><small>等待数据接入</small></article></section>
        <section class="wb-panel main-visual-panel">
          <div class="wb-panel-heading"><h2>{{ config.main }}</h2><span class="metric-wait">等待数据接入</span></div>
          <div v-if="kind==='image-recognition'" class="image-comparison"><div v-for="label in ['原图预览','识别结果']" :key="label"><span class="image-preview-label">{{ label }}</span><VisualEmpty kind="image" :title="label==='原图预览' ? '等待小麦图像' : '等待真实识别结果'" :note="label==='原图预览' ? '上传功能建设中' : '尚未运行分析'" /></div></div>
          <template v-else-if="kind==='reports'"><div class="report-toolbar"><span>报告列表</span><div><button disabled class="wb-button small"><Eye :size="14" />查看</button><button disabled class="wb-button small"><Download :size="14" />导出</button></div></div><VisualEmpty kind="report" title="暂无可查看的报告" note="等待真实分析记录接入" /><div class="report-table-heading" aria-label="报告字段预留"><span>报告名称</span><span>分析类型</span><span>生成日期</span><span>状态</span></div></template>
          <VisualEmpty v-else :kind="kind==='growth-analysis' ? 'plant' : 'chart'" :title="kind==='growth-analysis' ? '等待当前小麦观测' : '等待趋势数据'" note="功能建设中 · 当前无可展示的分析结果" />
        </section>
        <div class="secondary-visuals">
          <section v-if="kind==='yield-prediction'" class="wb-panel"><div class="wb-panel-heading"><h2>地区产量对比</h2></div><VisualEmpty compact kind="chart" title="等待地区产量记录" note="无真实数据，不绘制对比柱状图" /></section>
          <section v-if="kind==='market-returns'" class="wb-panel"><div class="wb-panel-heading"><h2>收获期价格预测</h2></div><VisualEmpty compact kind="chart" title="等待收获期与市场记录" note="预测服务待启用" /></section>
          <section v-if="kind==='reports'" class="wb-panel"><div class="wb-panel-heading"><h2>报告预览</h2></div><VisualEmpty compact kind="report" title="等待选择真实报告" note="暂无报告接入" /></section>
          <section v-if="kind==='growth-analysis' || kind==='image-recognition'" class="wb-panel"><div class="wb-panel-heading"><h2>{{ kind==='growth-analysis' ? '近期变化趋势' : '分析任务' }}</h2><Clock3 :size="16" /></div><VisualEmpty compact :kind="kind==='growth-analysis' ? 'chart' : 'plant'" title="等待数据接入" note="暂无真实记录" /></section>
          <section v-if="kind==='market-returns'" class="wb-panel"><div class="wb-panel-heading"><h2>成本结构</h2><span class="metric-wait">待接入</span></div><VisualEmpty compact kind="ring" title="等待成本记录" note="暂不绘制成本占比" /></section>
          <section v-if="kind==='yield-prediction'" class="wb-panel"><div class="wb-panel-heading"><h2>产量对比</h2></div><div class="comparison-metrics"><div v-for="label in ['预测亩产','实测亩产']" :key="label"><span>{{ label }}</span><strong>—</strong><small>待接入</small></div></div></section>
          <section v-if="kind==='growth-prediction'" class="wb-panel stage-timeline"><div class="wb-panel-heading"><h2>生长观测时间线</h2><CalendarDays :size="16" /></div><div class="empty-timeline"><i></i><span>等待连续观测记录</span><i></i></div><p>尚无实际生育阶段或日期</p></section>
          <section class="wb-panel wb-result-note"><ShieldCheck :size="22" :stroke-width="1.3" /><h2>{{ kind==='reports' ? '报告来源' : '风险提示' }}</h2><strong>{{ kind==='reports' ? '等待数据来源核验' : '暂无已验证的风险判断' }}</strong><p>仅呈现有来源、可核验的真实记录。</p></section>
        </div>
      </div>
      <aside class="workbench-state">
        <section class="wb-panel"><div class="wb-panel-heading"><h2>{{ config.side }}</h2></div><div v-for="label in config.metrics" :key="label" class="side-metric"><span>{{ label }}</span><strong>—</strong><small>等待数据接入</small></div></section>
        <section class="wb-panel connection-status"><h2>数据状态</h2><div><i></i><span>等待数据接入</span></div><div><i></i><span>分析服务待启用</span></div><small>当前页面为功能展示</small></section>
      </aside>
    </div>
    <details class="workbench-more"><summary>功能说明与展示预留</summary><div class="workbench-more-links"><RouterLink to="/research-center">科研实验中心<ArrowUpRight :size="14" /></RouterLink><RouterLink to="/phenotype-analysis">表型指标分析<ArrowUpRight :size="14" /></RouterLink></div><ModelPlaceholder v-if="kind==='image-recognition' || kind==='growth-analysis'" /></details>
    <div class="reference-photo-credit"><a v-if="backgroundScene.source" :href="backgroundScene.source" target="_blank" rel="noopener noreferrer">背景：{{ backgroundScene.credit }}<ArrowUpRight :size="11" /></a><span v-else>背景：{{ backgroundScene.credit }}</span><span>{{ backgroundScene.label }} · 装饰背景，非用户地块观测</span></div>
  </div>
</template>

