<script setup>
import { computed, ref } from 'vue'
import { Layers, LoaderCircle, Image, AlertCircle, Info } from 'lucide-vue-next'
import { imageUrl, segmentationAlgorithms } from '../services/imageApi.js'
import AlgorithmHelp from './AlgorithmHelp.vue'

const props = defineProps({
  results: { type: Object, required: true },
  statuses: { type: Object, required: true },
  errors: { type: Object, required: true },
  selectedAlgorithm: { type: String, required: true },
})
const emit = defineEmits(['select', 'image-error'])
const imageMode = ref('overlay')
// 只以本次图片的真实结果绘制，不填补未执行或失败的方案。
const percent = result => `${(result.vegetation_ratio * 100).toFixed(2)}%`
const stateLabel = state => ({ running: '运行中', queued: '等待运行', failed: '运行失败', succeeded: '已完成' })[state] || '尚未运行'

// 只汇总同一输入、相同尺寸的已完成结果；用百分点描述面积比例的差值。
const comparisonSummary = computed(() => {
  const values = segmentationAlgorithms.map(item => props.results[item.name]).filter(Boolean)
  if (values.length < 2 || !values[0].input_sha256) return null
  if (values.some(value => value.input_sha256 !== values[0].input_sha256 || value.width !== values[0].width || value.height !== values[0].height)) return null
  const fractions = values.map(value => value.vegetation_ratio)
  const minimum = Math.min(...fractions)
  const maximum = Math.max(...fractions)
  return { count: values.length, minimum, maximum, gap: (maximum - minimum) * 100 }
})

const thresholdExplanation = computed(() => {
  const exg = props.results.ExG
  const otsu = props.results['Otsu-ExG']
  // 无连通域后处理时，两者仅有 ExG 阈值不同，才可据此解释计数差异。
  if (!exg || !otsu || !exg.input_sha256 || exg.input_sha256 !== otsu.input_sha256
    || exg.width !== otsu.width || exg.height !== otsu.height || exg.parameters?.min_component_area !== 0) return ''
  const fixed = exg.parameters?.exg_threshold
  const automatic = otsu.algorithm_metadata?.computed_exg_threshold
  if (!Number.isInteger(fixed) || !Number.isInteger(automatic)) return ''
  const difference = exg.vegetation_pixel_count - otsu.vegetation_pixel_count
  const count = Math.abs(difference).toLocaleString('zh-CN')
  const prefix = `本图 ExG 固定阈值为 ${fixed}，Otsu 自动阈值为 ${automatic}。`
  if (automatic > fixed && difference > 0) return `${prefix}Otsu 的门槛更高，少计入 ${count} 个像素；这解释了两者的面积差异。`
  if (automatic < fixed && difference < 0) return `${prefix}Otsu 的门槛更低，多计入 ${count} 个像素；这解释了两者的面积差异。`
  if (difference === 0) return `${prefix}本图两者计入的前景像素数量相同。`
  return ''
})

const methodNotes = [
  { name: 'ExG', text: '用固定门槛判断绿色相对红、蓝的强度。浅绿、偏绿背景和光照变化都可能影响结果。' },
  { name: 'HSV', text: '颜色范围、饱和度和亮度需同时通过；浅色、暗色与偏色区域可能得到不同判定。' },
  { name: 'Otsu-ExG', text: '按当前图片的颜色分布自动确定门槛，每张图可能不同。自动阈值不等于最准确的植被边界。' },
  { name: 'ExG-HSV Fusion', text: '需同时满足两类条件。本方案使用自己的冻结参数，与独立 ExG、HSV 的参数不完全相同，不能直接认定面积一定更小。' },
]
</script>

<template>
  <section class="wb-panel algorithm-comparison" aria-label="四算法结果对比">
    <div class="wb-panel-heading comparison-heading"><div><h2><Layers :size="18" />四方案对比</h2><p>同一图片 · 面积差异不代表准确率差异</p></div><div class="comparison-modes" role="group" aria-label="对比图类型"><button v-for="mode in [{value:'overlay',label:'叠加'},{value:'mask',label:'掩膜'}]" :key="mode.value" :aria-pressed="imageMode===mode.value" @click="imageMode=mode.value">{{ mode.label }}</button></div></div>
    <section class="comparison-explanation" aria-label="植被占比差异说明">
      <h3><Info :size="17" />为什么植被占比不同？</h3>
      <p>各方案对颜色和明暗的判定条件不同，浅绿、阴影、偏绿背景及边缘像素可能被分别计入或排除。这些是常见影响因素，尚未逐像素核实本图差异来自哪些区域。</p>
      <div v-if="comparisonSummary" class="comparison-gap" aria-live="polite"><span>本图已完成 {{ comparisonSummary.count }} 种方案</span><strong>{{ (comparisonSummary.minimum * 100).toFixed(2) }}%–{{ (comparisonSummary.maximum * 100).toFixed(2) }}%</strong><span>最大相差 {{ comparisonSummary.gap.toFixed(2) }} 个百分点</span></div>
      <p v-if="thresholdExplanation" class="threshold-evidence">{{ thresholdExplanation }}</p>
      <details><summary>查看四种方案的判定差异</summary><div class="method-notes"><article v-for="note in methodNotes" :key="note.name"><h4>{{ note.name }}</h4><p>{{ note.text }}</p></article></div><p class="comparison-guidance">先切换掩膜与叠加图检查边缘、阴影和背景。占比高低或相同都不能说明谁更准确；判断对错需要人工标注对照评价。</p></details>
    </section>
    <div class="comparison-grid">
      <div v-for="item in segmentationAlgorithms" :key="item.name" class="comparison-card-shell"><button class="algorithm-result-card" :class="{active:selectedAlgorithm===item.name,failed:statuses[item.name]==='failed'}" :aria-label="`查看 ${item.name} 结果`" :aria-pressed="selectedAlgorithm===item.name" @click="emit('select',item.name)">
        <span class="comparison-card-title"><strong>{{ item.name }}</strong><small>{{ stateLabel(statuses[item.name]) }}</small></span>
        <span v-if="results[item.name]" class="comparison-image"><img :src="imageUrl(results[item.name][`${imageMode}_url`])" :alt="`${item.name} ${imageMode==='mask'?'分割掩膜':'叠加结果'}`" @error="emit('image-error')" /></span>
        <span v-else class="comparison-image comparison-empty"><LoaderCircle v-if="statuses[item.name]==='running'" class="comparison-spinner" :size="25" /><AlertCircle v-else-if="statuses[item.name]==='failed'" :size="25" /><Image v-else :size="25" /><span>{{ stateLabel(statuses[item.name]) }}</span></span>
        <span class="comparison-readings"><span>植被占比<strong>{{ results[item.name] ? percent(results[item.name]) : '—' }}</strong></span><span>植被像素<b>{{ results[item.name] ? results[item.name].vegetation_pixel_count.toLocaleString() : '—' }}</b></span><span>分析耗时<b>{{ results[item.name] ? `${results[item.name].analysis_time_seconds.toFixed(3)} 秒` : '—' }}</b></span></span>
        <span v-if="errors[item.name]" class="comparison-error">{{ errors[item.name] }}</span>
      </button><AlgorithmHelp class="comparison-card-help" :algorithm="item.name" /></div>
    </div>
    <div class="comparison-bars" aria-label="真实植被占比对照">
      <div v-for="item in segmentationAlgorithms" :key="item.name" class="comparison-bar-row"><span>{{ item.name }}</span><div class="comparison-track"><i v-if="results[item.name]" :style="{width:percent(results[item.name])}"></i></div><strong>{{ results[item.name] ? percent(results[item.name]) : '待运行' }}</strong></div>
      <small>图中比例是预测区域占画面的面积，不是分割精度。</small>
    </div>
  </section>
</template>

<style scoped>
.algorithm-comparison{margin-top:18px}.comparison-heading{align-items:start!important}.comparison-heading h2{display:flex;align-items:center;gap:8px}.comparison-heading p{color:#b5cda6;font-size:10px;line-height:1.7;margin-top:7px}
.comparison-modes{display:flex;border:1px solid #b5d8a43a;border-radius:8px;padding:3px;background:#09241866;flex-shrink:0}.comparison-modes button{padding:6px 9px;border:0;background:none;color:#bdd6ad;font-size:10px;border-radius:5px}.comparison-modes button[aria-pressed=true]{background:#8bc2682f;color:#dff5ce}
.comparison-explanation{margin-bottom:17px;padding:15px;border:1px solid #b5d8a431;border-radius:10px;background:#0c291d70}.comparison-explanation h3{display:flex;align-items:center;gap:8px;color:#d8edcb;font-size:12px;font-weight:500}.comparison-explanation h3 svg{color:#b5dd98;flex-shrink:0}.comparison-explanation p{font-size:10px;line-height:1.9;color:#bed3b3;margin-top:9px}.comparison-gap{display:flex;align-items:center;flex-wrap:wrap;gap:7px 12px;margin-top:12px;font-size:10px;color:#b8cfa7}.comparison-gap strong{font-size:15px;color:#b9e89a;font-weight:500}.comparison-explanation .threshold-evidence{padding:10px 12px;background:#a5d17a0c;border-left:2px solid #c4b2766b;border-radius:4px;color:#e2d7b4}.comparison-explanation details{margin-top:13px}.comparison-explanation summary{font-size:10px;color:#c4dfad;cursor:pointer;line-height:1.8}.comparison-explanation summary:focus-visible{outline:2px solid #a5e58a;outline-offset:3px}.method-notes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.method-notes article{padding:12px;border-radius:8px;background:#15372555;border:1px solid #bad7a51a}.method-notes h4{color:#d5e8c7;font-size:11px;font-weight:500}.method-notes p{margin-top:6px}.comparison-explanation .comparison-guidance{color:#d1dec3}
.comparison-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.algorithm-result-card{padding:0;overflow:hidden;min-width:0;text-align:left;border-radius:10px;border:1px solid #b5d8a42b;background:#0a251c70;color:#d7e9cb;transition:border-color .18s,transform .18s}.algorithm-result-card.active{border-color:#a5e58a8c;box-shadow:inset 0 0 0 1px #a5e58a1a}.algorithm-result-card:hover{border-color:#b3de8b80;transform:translateY(-2px)}.algorithm-result-card.failed{border-color:#d8b65c55}
.comparison-card-title{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:12px 11px;background:#173a2a75}.comparison-card-title strong{font-size:11px;font-weight:500;overflow-wrap:anywhere}.comparison-card-title small{font-size:9px;color:#b4ca9f;white-space:nowrap}
.comparison-card-shell{position:relative;min-width:0}.comparison-card-shell>.algorithm-result-card{width:100%;height:100%}.comparison-card-shell .comparison-card-title{padding-right:40px;min-height:44px;box-sizing:border-box}.comparison-card-help{position:absolute;right:8px;top:9px;z-index:1}
.comparison-image{height:160px;position:relative;display:block;background:#061b13}.comparison-image img{position:absolute;inset:0;height:100%;width:100%;object-fit:contain}.comparison-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#a7c292;font-size:10px}
.comparison-readings{display:flex;flex-direction:column;padding:13px;gap:10px}.comparison-readings>span{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#b5cda6;font-size:10px}.comparison-readings strong{color:#b9eb97;font-size:23px;font-weight:500}.comparison-readings b{color:#dfecd6;font-weight:400;font-size:11px}.comparison-error{display:block;color:#e2c68f;font-size:10px;line-height:1.7;padding:0 13px 13px}
.comparison-bars{margin-top:21px;padding:17px 13px 13px;background:#0b291b50;border:1px solid #bad7a527;border-radius:10px}.comparison-bar-row{display:grid;grid-template-columns:114px minmax(0,1fr) 58px;gap:9px;align-items:center;margin-bottom:12px;font-size:10px;color:#d5e7c8}.comparison-bar-row>span{font-size:9px}.comparison-bar-row strong{text-align:right;color:#bae99d;font-weight:400;white-space:nowrap}.comparison-track{height:8px;background:#c1dfac13;border-radius:4px;overflow:hidden}.comparison-track i{display:block;height:100%;border-radius:4px;background:#95d67c}.comparison-bars>small{display:block;color:#b1c79f;font-size:9px;line-height:1.8;margin-top:16px}
.algorithm-comparison button:focus-visible{outline:2px solid #a5e58a;outline-offset:3px}.comparison-spinner{animation:comparison-spin 1.1s linear infinite}@keyframes comparison-spin{to{transform:rotate(360deg)}}
@media(max-width:760px){.comparison-heading{gap:12px}.comparison-grid{gap:10px}.comparison-card-title{flex-wrap:wrap}.comparison-readings{padding:10px}.comparison-bar-row{grid-template-columns:104px minmax(0,1fr) 53px}.comparison-image{height:145px}.comparison-explanation{padding:12px}.method-notes{grid-template-columns:1fr}}@media(max-width:420px){.comparison-grid{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){.comparison-spinner{animation:none}.algorithm-result-card{transition:none}}
</style>
