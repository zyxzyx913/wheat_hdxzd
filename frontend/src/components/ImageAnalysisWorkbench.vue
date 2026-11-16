<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Upload, ScanLine, ShieldCheck, LoaderCircle, Image, Leaf, Clock3, AlertCircle, Download, ChevronRight } from 'lucide-vue-next'
import VisualEmpty from './VisualEmpty.vue'
import ModelPlaceholder from './ModelPlaceholder.vue'
import AlgorithmComparison from './AlgorithmComparison.vue'
import AlgorithmHelp from './AlgorithmHelp.vue'
import { backgroundScenes, backgroundStyle } from '../config/backgroundScenes.js'
import { analyzeImage, getImageServiceHealth, imageUrl, normalizeImageFile, segmentationAlgorithms } from '../services/imageApi.js'
import { saveLatestAnalysis } from '../services/analysisSession.js'

const fileInput = ref(null)
const selectedFile = ref(null)
const localPreview = ref('')
const selectedAlgorithm = ref('ExG')
const results = ref({})
const statuses = ref({})
const algorithmErrors = ref({})
const activeAlgorithm = ref('')
const inputHash = ref(null)
const result = computed(() => results.value[selectedAlgorithm.value] || null)
const originalResult = computed(() => result.value || Object.values(results.value)[0] || null)
const busy = ref(false)
const error = ref('')
const imageError = ref(false)
const service = ref('checking')
const limits = ref({ max_file_bytes: 10 * 1024 * 1024, max_pixels: 4000000, max_dimension: 4096 })
const healthController = new AbortController()
let analysisController = null
let generation = 0
let healthTimer = null
const backgroundScene = backgroundScenes['image-recognition']
const serviceLabel = computed(() => ({ checking: '正在连接服务', online: '分析服务已连接', offline: '分析服务未连接' })[service.value])
const statusLabel = computed(() => busy.value ? `正在分析 ${activeAlgorithm.value}` : result.value ? `${selectedAlgorithm.value} 已完成` : statuses.value[selectedAlgorithm.value] === 'failed' ? `${selectedAlgorithm.value} 未完成` : selectedFile.value ? '所选方案待运行' : '等待选择图片')
const ratio = computed(() => result.value ? `${(result.value.vegetation_ratio * 100).toFixed(2)}%` : '—')
const previews = computed(() => [
  { key: 'original', label: '原始图片', src: originalResult.value ? imageUrl(originalResult.value.original_url) : localPreview.value, note: originalResult.value ? '同一图片 · 方向统一' : '本地预览 · 尚未分析' },
  { key: 'mask', label: '分割掩膜', src: result.value ? imageUrl(result.value.mask_url) : '', note: '白色为预测植被，黑色为背景' },
  { key: 'overlay', label: '叠加结果', src: result.value ? imageUrl(result.value.overlay_url) : '', note: '绿色标记预测区域' },
])

function clearCurrent() {
  // 重新选图使旧请求失效；即使服务端仍在执行，也不会覆盖新图片。
  generation += 1
  analysisController?.abort()
  if (localPreview.value) URL.revokeObjectURL(localPreview.value)
  localPreview.value = ''
  selectedFile.value = null
  results.value = {}
  statuses.value = {}
  algorithmErrors.value = {}
  inputHash.value = null
  selectedAlgorithm.value = 'ExG'
  activeAlgorithm.value = ''
  busy.value = false
  error.value = ''
  imageError.value = false
}

function selectImage(event) {
  const file = event.target.files?.[0]
  if (!file) return
  clearCurrent()
  if (!/\.(jpg|jpeg|png)$/i.test(file.name) && !['image/png', 'image/jpeg'].includes(file.type)) {
    error.value = '仅支持 JPG、JPEG 或 PNG 图片。'
  } else if (!file.size) {
    error.value = '图片内容为空，请重新选择。'
  } else if (file.size > limits.value.max_file_bytes) {
    error.value = `图片不能超过 ${(limits.value.max_file_bytes / 1024 / 1024).toFixed(0)} MiB。`
  } else {
    selectedFile.value = normalizeImageFile(file)
    localPreview.value = URL.createObjectURL(selectedFile.value)
  }
  // 允许再次选择同一文件。
  event.target.value = ''
}

function startAnalysis() {
  return runAlgorithms([selectedAlgorithm.value])
}

function compareAll() {
  return runAlgorithms(segmentationAlgorithms.map(item => item.name))
}

async function runAlgorithms(names) {
  if (!selectedFile.value) {
    error.value = '请先选择一张小麦图片。'
    return
  }
  if (busy.value) return
  const current = ++generation
  analysisController?.abort()
  // 同一 File 顺序提交，后端每次独立计时；单项失败仍继续其余方案。
  const file = selectedFile.value
  const nextResults = { ...results.value }
  for (const name of names) {
    delete nextResults[name]
    statuses.value[name] = 'queued'
    delete algorithmErrors.value[name]
  }
  results.value = nextResults
  error.value = ''
  imageError.value = false
  busy.value = true
  try {
    for (const name of names) {
      if (current !== generation) return
      activeAlgorithm.value = name
      statuses.value[name] = 'running'
      const controller = new AbortController()
      analysisController = controller
      const timer = setTimeout(() => controller.abort(), 120000)
      try {
        const response = await analyzeImage(file, controller.signal, name)
        if (current !== generation) return
        if (inputHash.value && response.input_sha256 !== inputHash.value) throw new Error('图片摘要不一致，本次结果不纳入对比，请重新上传。')
        const previous = Object.values(results.value)[0]
        if (previous && (response.width !== previous.width || response.height !== previous.height)) throw new Error('结果尺寸不一致，本次结果不纳入对比。')
        inputHash.value = response.input_sha256
        results.value = { ...results.value, [name]: response }
        saveLatestAnalysis({ result: response, results: { ...results.value, [name]: response }, algorithm: name, fileName: file.name })
        statuses.value[name] = 'succeeded'
        service.value = 'online'
      } catch (caught) {
        if (current !== generation) return
        if (caught.connectionFailed) service.value = 'offline'
        statuses.value[name] = 'failed'
        algorithmErrors.value[name] = caught.name === 'AbortError'
          ? '等待超时，服务端任务可能仍在运行，请稍后重试。'
          : caught.message
      } finally {
        clearTimeout(timer)
      }
    }
    const failed = names.filter(name => statuses.value[name] === 'failed')
    error.value = failed.map(name => `${name}：${algorithmErrors.value[name]}`).join('；')
  } finally {
    if (current === generation) {
      busy.value = false
      activeAlgorithm.value = ''
    }
  }
}

onMounted(async () => {
  healthTimer = setTimeout(() => healthController.abort(), 5000)
  try {
    const response = await getImageServiceHealth(healthController.signal)
    service.value = ['ok', 'degraded'].includes(response.status) ? 'online' : 'offline'
    if (response.limits) limits.value = response.limits
  } catch {
    service.value = 'offline'
  } finally {
    clearTimeout(healthTimer)
  }
})

onUnmounted(() => {
  clearCurrent()
  healthController.abort()
  clearTimeout(healthTimer)
})
</script>

<template>
  <div class="p2-workspace reference-extension image-analysis-workbench" data-scene="image-recognition" :style="backgroundStyle(backgroundScene)">
    <header class="workbench-heading">
      <span class="reference-title-icon"><ScanLine :size="30" :stroke-width="1.5" /></span>
      <div><h1>图像识别</h1><p>上传一张小麦照片，观察画面中的可见植被区域。</p></div>
      <span class="workbench-status" :class="{ developing: service !== 'online' }">{{ serviceLabel }}</span>
    </header>

    <div v-if="error" class="analysis-error" role="alert"><AlertCircle :size="19" /><span>{{ error }}</span></div>
    <div v-if="imageError" class="analysis-error" role="alert"><AlertCircle :size="19" /><span>图片预览读取失败，请重新选择图片或重试分析。</span></div>

    <div class="workbench-layout">
      <aside class="workbench-control wb-panel">
        <div class="wb-panel-heading"><h2>图像与分析</h2><Upload :size="17" /></div>
        <div class="workbench-upload">
          <Upload :size="32" :stroke-width="1.3" />
          <strong>{{ selectedFile ? '图片已选择' : '上传小麦图像' }}</strong>
          <small>JPG / JPEG / PNG</small>
          <input ref="fileInput" class="file-input" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" aria-label="选择小麦图片文件" @change="selectImage" />
          <button class="wb-button" @click="fileInput.click()">{{ selectedFile ? '重新选择图片' : '选择图片' }}</button>
        </div>
        <div v-if="selectedFile" class="selected-file"><Image :size="16" /><span>{{ selectedFile.name }}</span><small>{{ (selectedFile.size / 1024).toFixed(1) }} KB</small></div>
        <p class="upload-limit">单张不超过 {{ (limits.max_file_bytes / 1024 / 1024).toFixed(0) }} MiB<br />最多 {{ (limits.max_pixels / 10000).toFixed(0) }} 万像素，不自动缩图</p>
        <div class="algorithm-choices" role="group" aria-label="识别方案"><span>选择识别方案</span><div v-for="item in segmentationAlgorithms" :key="item.name" class="algorithm-choice-row"><button class="algorithm-choice" :aria-label="`选择 ${item.name}`" :aria-pressed="selectedAlgorithm===item.name" @click="selectedAlgorithm=item.name"><strong>{{ item.name }}</strong><small>{{ item.description }}</small></button><AlgorithmHelp :algorithm="item.name" /></div></div>
        <button class="wb-button primary analyze-button" :disabled="busy || !selectedFile" :aria-busy="busy" @click="startAnalysis">
          <LoaderCircle v-if="busy" class="is-spinning" :size="17" /><ScanLine v-else :size="17" />{{ busy ? '正在分析…' : '开始分析' }}
        </button>
        <button class="wb-button compare-all-button" :disabled="busy || !selectedFile" @click="compareAll">四方案对比</button>
        <div class="wb-control-note"><ShieldCheck :size="17" /><span>结果来自实际图片计算<br />仅表示画面可见植被比例</span></div>
        <details v-if="result" class="analysis-details"><summary>科研参数与记录</summary><dl><dt>算法</dt><dd>{{ result.algorithm }}</dd><template v-for="(value,key) in result.parameters" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></template><template v-if="result.algorithm_metadata.computed_exg_threshold!==undefined"><dt>实算自动阈值</dt><dd>{{ result.algorithm_metadata.computed_exg_threshold }}</dd></template><dt>任务 ID</dt><dd>{{ result.task_id }}</dd><dt>参数版本</dt><dd>{{ result.profile_id }}</dd></dl></details>
      </aside>

      <div class="workbench-main">
        <section class="wb-panel main-visual-panel">
          <div class="wb-panel-heading"><h2>{{ selectedAlgorithm }} · 图像对照</h2><span class="metric-wait" aria-live="polite">{{ statusLabel }}</span></div>
          <div class="analysis-preview-grid" :aria-busy="busy">
            <figure v-for="preview in previews" :key="preview.key" class="analysis-preview" :class="preview.key">
              <figcaption><span>{{ preview.label }}</span><a v-if="preview.src && (preview.key==='original' ? originalResult : result)" :href="preview.src" :download="`${(preview.key==='original' ? originalResult : result).task_id}-${preview.key}.png`" :aria-label="`下载${preview.label}`"><Download :size="15" /></a></figcaption>
              <div v-if="preview.src" class="analysis-image-frame"><img :src="preview.src" :alt="preview.label" @error="imageError = true" /></div>
              <VisualEmpty v-else compact kind="image" :title="preview.key === 'original' ? '选择一张小麦图片' : busy ? '正在生成真实结果' : '等待分析结果'" :note="preview.key === 'original' ? '仅使用你选择的照片' : '分析完成后展示'" />
              <small>{{ preview.note }}</small>
            </figure>
          </div>
        </section>
        <section class="wb-panel analysis-task" aria-live="polite">
          <div class="wb-panel-heading"><h2>分析任务</h2><Clock3 :size="17" /></div>
          <div class="task-state"><LoaderCircle v-if="busy" class="is-spinning" :size="22" /><ShieldCheck v-else :size="22" /><div><strong>{{ statusLabel }}</strong><p>{{ busy ? '按方案依次独立计算，已完成的结果可切换查看。' : Object.keys(results).length ? `本图已有 ${Object.keys(results).length} 种真实结果，可切换查看或运行四方案对比。` : '选择图片与识别方案后，点击开始分析。' }}</p></div></div>
          <p v-if="result?.vegetation_pixel_count === 0" class="zero-foreground-note">本图未检出前景，不能据此判断小麦死亡或长势不良。</p>
          <RouterLink v-if="result" class="continue-growth-link" to="/growth-analysis">继续进行长势分析 <ChevronRight :size="14" /></RouterLink>
        </section>
        <AlgorithmComparison :results="results" :statuses="statuses" :errors="algorithmErrors" :selected-algorithm="selectedAlgorithm" @select="selectedAlgorithm=$event" @image-error="imageError=true" />
      </div>

      <aside class="workbench-state">
        <section class="wb-panel">
          <div class="wb-panel-heading"><h2>当前方案指标</h2><Leaf :size="18" /></div><p class="current-algorithm">{{ selectedAlgorithm }}</p>
          <div class="side-metric ratio-metric"><span>画面植被占比</span><strong data-testid="vegetation-ratio">{{ ratio }}</strong><small>前景像素 / 总有效像素</small></div>
          <div class="side-metric"><span>图像尺寸</span><strong class="compact-value">{{ result ? `${result.width} × ${result.height}` : '—' }}</strong><small>像素 · 方向已统一</small></div>
          <div class="side-metric"><span>植被像素数量</span><strong class="compact-value">{{ result ? result.vegetation_pixel_count.toLocaleString() : '—' }}</strong><small>{{ result ? `总有效像素 ${result.total_valid_pixels.toLocaleString()}` : '等待真实计算' }}</small></div>
          <div class="side-metric"><span>分析耗时</span><strong class="compact-value" data-testid="analysis-time">{{ result ? `${result.analysis_time_seconds.toFixed(3)} 秒` : '—' }}</strong><small>解码、分割、特征与图片保存</small></div>
        </section>
        <section class="wb-panel scope-note"><ShieldCheck :size="22" /><h2>结果说明</h2><p>不同植被占比不代表不同准确率。</p><p>仅区分可见植被与背景，不区分叶、茎、穗，不判断长势等级。</p><RouterLink to="/research-center">科研实验中心<ChevronRight :size="14" /></RouterLink></section>
      </aside>
    </div>
    <details class="workbench-more"><summary>功能说明与展示预留</summary><ModelPlaceholder /></details>
    <div class="reference-photo-credit"><span>背景：{{ backgroundScene.credit }}</span><span>装饰背景，非用户观测或识别结果</span></div>
  </div>
</template>

<style scoped>
/* 仅精修图像工作台；继续复用已确认的麦田背景与深色玻璃主题。 */
.image-analysis-workbench .workbench-layout{grid-template-columns:210px minmax(0,1fr) 230px;gap:18px;align-items:start}
.file-input{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.image-analysis-workbench .workbench-upload{padding:25px 12px;gap:13px}
.workbench-upload .wb-button{margin-top:8px;justify-content:center}
.selected-file{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:15px 0;color:#d2e5c7;font-size:11px}
.selected-file>span{overflow-wrap:anywhere;flex:1;min-width:0}.selected-file small{flex-basis:100%;padding-left:24px;color:#a7c59a}
.upload-limit{font-size:10px;line-height:1.9;color:#bdd2b0;margin:15px 0}
.analyze-button{width:100%;justify-content:center;min-height:42px;gap:8px}
.algorithm-choices{display:flex;flex-direction:column;gap:8px;margin:18px 0}.algorithm-choices>span{font-size:11px;color:#bfd7ac;margin-bottom:3px}.algorithm-choices button{text-align:left;padding:11px 12px;border:1px solid #b4d69f28;border-radius:8px;background:#14362360;color:#d3e6c8}.algorithm-choices button[aria-pressed=true]{background:#89bc5940;border-color:#a5e58a77}.algorithm-choices strong{display:block;font-size:11px;font-weight:500;overflow-wrap:anywhere}.algorithm-choices small{display:block;font-size:9px;color:#b3cfa0;margin-top:5px}.compare-all-button{width:100%;justify-content:center;min-height:39px;margin-top:10px}.current-algorithm{font-size:11px;color:#bfe49f;margin:-3px 0 15px;overflow-wrap:anywhere}
.algorithm-choice-row{display:flex;align-items:center;gap:7px}.algorithm-choice-row>.algorithm-choice{flex:1;min-width:0}
.image-analysis-workbench .wb-button:not(:disabled):hover{border-color:#b4df9170;background:#77ac513e;box-shadow:0 0 15px #75d66b10}
.image-analysis-workbench .wb-button:disabled{cursor:not-allowed}
.analysis-preview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
.analysis-preview{margin:0;min-width:0;background:#08241955;border:1px solid #c1dfac26;border-radius:10px;overflow:hidden}
.analysis-preview.original{grid-column:1/-1}
.analysis-preview figcaption{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;color:#deecd4;font-size:12px;background:#142f2180}
.analysis-preview figcaption a{display:grid;place-items:center;color:#b3d898;padding:3px;border-radius:4px}
.analysis-preview figcaption a:hover{color:#ecf8dd;background:#a5e58a20}
.analysis-image-frame{height:190px;position:relative;background:#061a13;overflow:hidden}
.analysis-preview.original .analysis-image-frame{height:245px}
.analysis-image-frame img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;display:block}
.analysis-preview>small{display:block;padding:9px 12px;color:#b9cfae;font-size:9px;line-height:1.6}
.analysis-preview :deep(.visual-empty){min-height:180px;border:0;border-radius:0;margin:0}
.analysis-preview.original :deep(.visual-empty){min-height:245px}
.image-analysis-workbench .analysis-task{margin-top:18px}
.task-state{display:flex;gap:12px;align-items:center;color:#b4d996}.task-state strong{font-size:12px;color:#dfecd5;font-weight:500}.task-state p{font-size:10px;line-height:1.9;margin-top:6px;color:#b1c6a6}
.continue-growth-link{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:14px;padding:9px 12px;border:1px solid #a5e58a45;border-radius:8px;color:#c7eeae;background:#75d66b14;font-size:10px;text-decoration:none}.continue-growth-link:hover{background:#75d66b2b;border-color:#a5e58a72}
.zero-foreground-note{color:#e2cc9c;font-size:11px;line-height:1.8;margin-top:13px}
.image-analysis-workbench .side-metric .compact-value{font-size:21px;overflow-wrap:anywhere}
.image-analysis-workbench .ratio-metric strong{font-size:36px;color:#b1e78f}
.scope-note{margin-top:18px;color:#c3ddb0}.scope-note h2{font-size:14px;margin:12px 0}.scope-note p{font-size:11px;line-height:1.9;color:#bed1b3;margin:8px 0}.scope-note a{display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#bfdfa6;margin-top:17px}
.analysis-error{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding:15px 18px;border:1px solid #d8b65c60;border-radius:10px;background:#3a301bd1;color:#f0dfb2;font-size:12px;line-height:1.8;backdrop-filter:blur(10px)}
.analysis-error svg{flex-shrink:0}.analysis-details{margin-top:18px;font-size:10px;color:#b4cca3;line-height:1.8}.analysis-details summary{cursor:pointer}.analysis-details dl{margin-top:12px}.analysis-details dt{color:#99b48c;margin-top:8px}.analysis-details dd{margin:2px 0;overflow-wrap:anywhere;color:#d5e6c8}
.image-analysis-workbench :is(button,a,input):focus-visible{outline:2px solid #a5e58a;outline-offset:3px}
.is-spinning{animation:analysis-spin 1.1s linear infinite}@keyframes analysis-spin{to{transform:rotate(360deg)}}
@media(min-width:1700px){.analysis-image-frame{height:225px}.analysis-preview.original .analysis-image-frame{height:285px}}
@media(max-width:1400px){.image-analysis-workbench .workbench-layout{grid-template-columns:180px minmax(0,1fr) 190px;gap:13px}.image-analysis-workbench .wb-panel{padding:16px}.image-analysis-workbench .workbench-heading p{font-size:11px}.analysis-preview-grid{gap:10px}.image-analysis-workbench .side-metric .compact-value{font-size:18px}.image-analysis-workbench .ratio-metric strong{font-size:30px}}
@media(max-width:1100px){.image-analysis-workbench .workbench-layout{grid-template-columns:180px minmax(0,1fr)}.image-analysis-workbench .workbench-state{grid-column:1/-1;display:grid!important;grid-template-columns:1fr 1fr;gap:15px}.scope-note{margin-top:0}}
@media(max-width:760px){.image-analysis-workbench .workbench-layout{grid-template-columns:1fr}.image-analysis-workbench .workbench-state{grid-template-columns:1fr}.analysis-image-frame{height:170px}.analysis-preview.original .analysis-image-frame{height:220px}.image-analysis-workbench .workbench-upload{padding:20px}.image-analysis-workbench .workbench-heading{flex-wrap:wrap}.image-analysis-workbench .workbench-status{margin-left:69px}}
@media(prefers-reduced-motion:reduce){.is-spinning{animation:none}}
</style>
