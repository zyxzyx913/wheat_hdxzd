<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, CheckCircle2, ClipboardCheck, Download, Image as ImageIcon, LoaderCircle, Minus, Plus, ShieldCheck, SkipForward } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { exportAnnotations, getAnnotationConsistency, getAnnotationImage, getAnnotationStatus, getAnnotationTasks, submitAdjudication, submitAnnotation } from '../services/annotationApi'

const router = useRouter()
const tasks = ref([])
const index = ref(0)
const imageUrl = ref('')
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')
const zoom = ref(1)
const annotatorId = ref(localStorage.getItem('maishitong.annotator-id') || '')
const label = ref('')
const growthStage = ref('')
const qualityFlags = ref([])
const rationale = ref('')
const confidence = ref(null)
const reviewerId = ref(localStorage.getItem('maishitong.reviewer-id') || '')
const finalLabel = ref('')
const reviewStatus = ref('待复核')
const reviewNote = ref('')
const completed = ref(new Set())
const status = ref(null)
const consistency = ref(null)
const currentTask = computed(() => tasks.value[index.value] || null)
const completedCount = computed(() => completed.value.size)
const qualityOptions = ['偏暗', '过曝', '模糊', '遮挡', '拍摄角度不佳', '背景复杂']

function resetForm() { label.value = ''; growthStage.value = ''; qualityFlags.value = []; rationale.value = ''; confidence.value = null; zoom.value = 1; message.value = '' }
async function loadImage() { if (imageUrl.value) URL.revokeObjectURL(imageUrl.value); imageUrl.value = ''; if (!currentTask.value) return; try { imageUrl.value = await getAnnotationImage(currentTask.value.anonymous_id) } catch (caught) { error.value = caught.message } }
function chooseTask(nextIndex) { index.value = Math.max(0, Math.min(tasks.value.length - 1, nextIndex)); resetForm() }
async function saveAnnotation() {
  if (!currentTask.value) return
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(annotatorId.value)) { error.value = '请填写字母、数字、下划线或短横线组成的匿名标注者 ID。'; return }
  if (!label.value) { error.value = '请选择较好、一般、较弱或无法判断。'; return }
  saving.value = true; error.value = ''; message.value = ''
  try {
    localStorage.setItem('maishitong.annotator-id', annotatorId.value)
    await submitAnnotation({ anonymous_id: currentTask.value.anonymous_id, annotator_id: annotatorId.value, label: label.value, growth_stage: growthStage.value || null, quality_flags: qualityFlags.value, rationale: rationale.value, confidence: confidence.value, review_round: 1 })
    completed.value = new Set([...completed.value, currentTask.value.anonymous_id]); message.value = '标注已追加保存，不会覆盖其他标注者的记录。';
    status.value = await getAnnotationStatus(); consistency.value = status.value.consistency
  } catch (caught) { error.value = caught.message } finally { saving.value = false }
}
async function downloadCsv() { try { const url = await exportAnnotations(); const link = document.createElement('a'); link.href = url; link.download = 'annotations.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) } catch (caught) { error.value = caught.message } }
async function refreshConsistency() { try { consistency.value = await getAnnotationConsistency() } catch (caught) { error.value = caught.message } }
async function saveAdjudication() { if (!currentTask.value) return; if (!/^[A-Za-z0-9_-]{1,64}$/.test(reviewerId.value)) { error.value = '请填写复核者匿名 ID。'; return }; if (reviewStatus.value === '已复核' && !finalLabel.value) { error.value = '已复核状态必须选择最终标签。'; return }; saving.value = true; error.value = ''; try { localStorage.setItem('maishitong.reviewer-id', reviewerId.value); await submitAdjudication({ anonymous_id: currentTask.value.anonymous_id, final_label: finalLabel.value, review_status: reviewStatus.value, reviewer_id: reviewerId.value, review_note: reviewNote.value }); message.value = '复核记录已追加保存。'; } catch (caught) { error.value = caught.message } finally { saving.value = false } }
onMounted(async () => { try { tasks.value = await getAnnotationTasks(); status.value = await getAnnotationStatus(); consistency.value = status.value.consistency; await loadImage() } catch (caught) { error.value = caught.message } finally { loading.value = false } })
watch(currentTask, loadImage)
onBeforeUnmount(() => { if (imageUrl.value) URL.revokeObjectURL(imageUrl.value) })
</script>

<template>
  <div class="annotation-page">
    <header class="annotation-heading"><div><span class="eyebrow">RESEARCH ANNOTATION WORKSPACE</span><h1>小麦长势人工标注管理</h1><p>只记录图片可观察到的表观长势，不预填标签，不替代农学真值。</p></div><button class="annotation-back" @click="router.push('/research-center')"><ArrowLeft :size="16" />返回科研中心</button></header>
    <div v-if="loading" class="annotation-state"><LoaderCircle class="spin" :size="22" />正在读取候选样本库</div>
    <div v-else-if="error && !tasks.length" class="annotation-state error-state"><ShieldCheck :size="22" />{{ error }}</div>
    <template v-else>
      <section class="annotation-toolbar"><div><strong>候选图片 {{ tasks.length }} 张</strong><span>已完成本地标注 {{ completedCount }} 张</span><span v-if="status">服务器记录 {{ status.annotation_record_count }} 条</span></div><div><button class="tool-button" @click="downloadCsv"><Download :size="15" />导出 CSV</button><button class="tool-button" @click="refreshConsistency"><ClipboardCheck :size="15" />刷新一致性</button></div></section>
      <p v-if="message" class="annotation-message"><CheckCircle2 :size="16" />{{ message }}</p><p v-if="error" class="annotation-error"><ShieldCheck :size="16" />{{ error }}</p>
      <section v-if="currentTask" class="annotation-layout">
        <article class="annotation-image-panel"><div class="panel-title"><h2><ImageIcon :size="18" />匿名样本 {{ currentTask.anonymous_id }}</h2><span>{{ index + 1 }} / {{ tasks.length }}</span></div><div class="image-toolbar"><button @click="zoom=Math.max(.5,zoom-.1)" aria-label="缩小"><Minus :size="15" /></button><span>{{ Math.round(zoom * 100) }}%</span><button @click="zoom=Math.min(2,zoom+.1)" aria-label="放大"><Plus :size="15" /></button></div><div class="annotation-image-frame"><img v-if="imageUrl" :src="imageUrl" alt="待人工标注的小麦 RGB 图片" :style="{ transform: `scale(${zoom})` }" /><div v-else class="image-loading"><LoaderCircle class="spin" :size="20" />读取图片</div></div><div class="image-meta"><span>{{ currentTask.dataset }} · {{ currentTask.split }}</span><span>{{ currentTask.width }} × {{ currentTask.height }}</span><span>来源标签不在此页面展示</span></div></article>
        <article class="annotation-form-panel"><div class="panel-title"><h2>独立标注记录</h2><span>追加写入</span></div><label>匿名标注者 ID<input v-model="annotatorId" placeholder="例如 annotator_A" maxlength="64" /></label><fieldset><legend>表观长势标签</legend><label v-for="item in ['较好','一般','较弱','无法判断']" :key="item" class="radio-label"><input v-model="label" type="radio" name="vigor-label" :value="item" />{{ item }}</label></fieldset><label>生育期（可留空）<input v-model="growthStage" placeholder="例如 分蘖期；不确定可留空" maxlength="80" /></label><fieldset><legend>图像质量问题（可多选）</legend><label v-for="item in qualityOptions" :key="item" class="check-label"><input v-model="qualityFlags" type="checkbox" :value="item" />{{ item }}</label></fieldset><label>判断依据<textarea v-model="rationale" rows="4" maxlength="500" placeholder="只描述图像可观察依据，不推断根系、产量或未来长势。" /></label><label>标注置信度<select v-model="confidence"><option :value="null">未填写</option><option :value="1">1 · 较低</option><option :value="2">2 · 中等</option><option :value="3">3 · 较高</option></select></label><button class="save-button" :disabled="saving" @click="saveAnnotation"><LoaderCircle v-if="saving" class="spin" :size="16" /><CheckCircle2 v-else :size="16" />{{ saving ? '保存中' : '追加保存标注' }}</button><div class="form-note">每次保存都会生成新记录，不覆盖其他标注者或之前轮次。</div></article>
      </section>
      <section class="annotation-navigation"><button class="tool-button" :disabled="index===0" @click="chooseTask(index-1)"><ArrowLeft :size="15" />上一张</button><button class="tool-button" :disabled="index>=tasks.length-1" @click="chooseTask(index+1)">下一张<SkipForward :size="15" /></button></section>
      <section class="consistency-panel"><div class="panel-title"><h2><ClipboardCheck :size="18" />标注一致性状态</h2><span>{{ consistency?.status === 'ready' ? '可计算' : '等待多位标注' }}</span></div><div class="consistency-grid"><div><strong>{{ consistency?.annotation_record_count || 0 }}</strong><small>标注记录</small></div><div><strong>{{ consistency?.annotator_count || 0 }}</strong><small>标注者</small></div><div><strong>{{ consistency?.conflict_image_count || 0 }}</strong><small>冲突图片</small></div><div><strong>{{ consistency?.fleiss_kappa == null ? '—' : consistency.fleiss_kappa.toFixed(3) }}</strong><small>Fleiss κ</small></div></div><p>当前系统不会自动多数投票或生成最终标签；冲突意见会完整保留，需人工复核后写入 adjudicated_labels.csv。</p></section>
      <section class="consistency-panel adjudication-panel"><div class="panel-title"><h2><ShieldCheck :size="18" />人工复核记录</h2><span>追加写入，不覆盖独立标注</span></div><div class="adjudication-grid"><label>复核者匿名 ID<input v-model="reviewerId" placeholder="例如 reviewer_A" maxlength="64" /></label><label>复核状态<select v-model="reviewStatus"><option>待复核</option><option>已复核</option><option>无法形成共识</option></select></label><label>最终表观长势标签<select v-model="finalLabel"><option value="">未确定</option><option>较好</option><option>一般</option><option>较弱</option><option>无法判断</option></select></label><label class="wide">复核说明<textarea v-model="reviewNote" rows="3" maxlength="500" placeholder="记录分歧处理依据；不能推断根系、产量或未来长势。" /></label></div><button class="save-button adjudication-save" :disabled="saving" @click="saveAdjudication">保存当前样本复核记录</button></section>
    </template>
  </div>
</template>

<style scoped>
.annotation-page{color:#edf5e7;padding:12px 0 35px}.annotation-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:20px}.annotation-heading h1{font-size:28px;font-weight:500;margin:5px 0}.annotation-heading p{color:#aac4a3;font-size:12px}.annotation-back,.tool-button{display:flex;align-items:center;gap:6px;border:1px solid #a5e58a38;border-radius:8px;padding:9px 12px;background:#14362385;color:#cfe9c2;font-size:11px;cursor:pointer}.annotation-back:hover,.tool-button:hover:not(:disabled){background:#75d66b24;border-color:#a5e58a6b}.annotation-state{display:flex;align-items:center;gap:9px;padding:35px;background:#103522b8;border:1px solid #a5e58a30;border-radius:14px}.error-state,.annotation-error{color:#f1c49a}.annotation-toolbar,.annotation-message,.annotation-error,.annotation-layout,.annotation-navigation,.consistency-panel{background:rgba(14,46,31,.68);border:1px solid #a9d99d32;border-radius:14px;backdrop-filter:blur(13px)}.annotation-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 15px;margin-bottom:15px}.annotation-toolbar>div{display:flex;align-items:center;gap:14px}.annotation-toolbar span{color:#9fb7a4;font-size:10px}.annotation-toolbar strong{font-size:12px;font-weight:500}.annotation-toolbar .tool-button{padding:7px 10px}.annotation-message,.annotation-error{display:flex;align-items:center;gap:7px;padding:10px 13px;font-size:11px;margin:0 0 15px}.annotation-message{color:#b9e6a4}.annotation-layout{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr);gap:15px;padding:15px}.annotation-image-panel,.annotation-form-panel{min-width:0}.panel-title{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}.panel-title h2{display:flex;align-items:center;gap:7px;font-size:14px;font-weight:500;margin:0}.panel-title h2 svg{color:#a5e58a}.panel-title>span{color:#9fb7a4;font-size:10px}.image-toolbar{display:flex;align-items:center;justify-content:center;gap:9px;margin:-2px 0 10px;color:#b7d2aa;font-size:10px}.image-toolbar button{display:grid;place-items:center;width:27px;height:27px;background:#a5e58a15;border:1px solid #a5e58a2d;border-radius:6px;color:#cfe9c2;cursor:pointer}.annotation-image-frame{height:520px;border-radius:10px;overflow:hidden;background:#071b14;border:1px solid #a5e58a25;display:grid;place-items:center}.annotation-image-frame img{max-width:100%;max-height:100%;object-fit:contain;transition:transform .2s ease}.image-loading{display:flex;align-items:center;gap:8px;color:#9fb7a4;font-size:11px}.image-meta{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;color:#9fb7a4;font-size:9px;margin-top:9px}.annotation-form-panel{padding:4px 2px}.annotation-form-panel label,.annotation-form-panel fieldset{display:block;margin-bottom:13px;color:#bcd4b2;font-size:10px}.annotation-form-panel input[type=text],.annotation-form-panel input:not([type]),.annotation-form-panel textarea,.annotation-form-panel select{display:block;width:100%;margin-top:6px;padding:9px 10px;background:#071b14b8;color:#e8f4e2;border:1px solid #a5e58a2d;border-radius:7px;font:inherit;box-sizing:border-box}.annotation-form-panel fieldset{border:1px solid #a5e58a20;border-radius:8px;padding:10px}.annotation-form-panel legend{padding:0 5px;color:#bcd4b2}.radio-label,.check-label{display:inline-flex!important;align-items:center;gap:6px;margin:6px 14px 2px 0!important}.radio-label input,.check-label input{accent-color:#8fd76f}.annotation-form-panel textarea{resize:vertical}.save-button{display:flex;align-items:center;justify-content:center;gap:7px;width:100%;padding:11px;border:0;border-radius:8px;background:#9ce17f;color:#0b2418;font-size:11px;cursor:pointer}.save-button:disabled{opacity:.55;cursor:not-allowed}.form-note{color:#8fa98a;font-size:9px;line-height:1.6;margin-top:10px}.annotation-navigation{display:flex;justify-content:space-between;padding:11px 15px;margin:15px 0}.tool-button:disabled{opacity:.4;cursor:not-allowed}.consistency-panel{padding:15px}.consistency-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.consistency-grid>div{padding:12px;border:1px solid #a5e58a1f;border-radius:8px;background:#75d66b0d}.consistency-grid strong{display:block;color:#c8eead;font-size:20px;font-weight:500}.consistency-grid small{color:#9fb7a4;font-size:9px}.consistency-panel p{color:#9fb7a4;font-size:10px;line-height:1.7;margin:13px 0 0}@media(max-width:900px){.annotation-layout{grid-template-columns:1fr}.annotation-image-frame{height:420px}}@media(max-width:600px){.annotation-heading{flex-direction:column}.annotation-toolbar{align-items:flex-start;flex-direction:column}.annotation-toolbar>div{flex-wrap:wrap}.consistency-grid{grid-template-columns:repeat(2,1fr)}}
.adjudication-panel{margin-top:15px}.adjudication-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.adjudication-grid label{color:#bcd4b2;font-size:10px}.adjudication-grid input,.adjudication-grid textarea,.adjudication-grid select{display:block;width:100%;margin-top:6px;padding:9px 10px;background:#071b14b8;color:#e8f4e2;border:1px solid #a5e58a2d;border-radius:7px;font:inherit;box-sizing:border-box}.adjudication-grid textarea{resize:vertical}.adjudication-grid .wide{grid-column:1/-1}.adjudication-save{margin-top:12px;max-width:260px}
</style>
