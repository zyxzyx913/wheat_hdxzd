<script setup>
import { computed, onMounted, ref } from 'vue'
import { BarChart3, CloudSun, LoaderCircle } from 'lucide-vue-next'
import { loadLatestAnalysis } from '../services/analysisSession'
const stage=ref(''), score=ref(''), confidence=ref(''), analysisSource=ref('未同步长势分析结果'), predictionStatus=ref(null), weatherStatus=ref('unavailable'), risks=ref(''), captureDate=ref(''), location=ref(''), result=ref(null), loading=ref(false), error=ref('')
onMounted(async () => {
  const saved = loadLatestAnalysis()
  const result = saved?.result
  const stageResult = saved?.stageResult || result?.growth_stage
  const vigor = result?.growth_analysis?.vigor_assessment || result
  const metrics = result?.growth_analysis?.metrics
  const derivedScore = metrics ? (() => { const coverage = Number(metrics.vegetation_coverage?.fraction || 0); const green = Number(metrics.green_degree?.mean_green_channel_ratio || 0); const cv = Number(metrics.distribution_uniformity?.coefficient_of_variation ?? 1); return Math.max(0, Math.min(100, (coverage / 0.75 * 100) * 0.45 + (green * 100) * 0.35 + ((1 - cv / 1.5) * 100) * 0.2)) })() : ''
  if (result) {
    stage.value = stageResult?.predicted_stage_name || result?.growth_stage?.predicted_stage_name || ''
    score.value = derivedScore !== '' ? derivedScore : (vigor?.vigor_score ?? '')
    confidence.value = stageResult?.confidence ?? result?.growth_stage?.confidence ?? ''
    analysisSource.value = '已同步最近一次长势分析结果'
  }
  // 旧缓存可能只有生育期，没有 V1.1 综合分；从真实历史记录兜底读取最新评分。
  if (score.value === '' || score.value == null) {
    try {
      const response = await fetch('/api/growth/history')
      if (response.ok) {
        const payload = await response.json()
        const latest = (payload.items || []).sort((a, b) => String(b.completed_at_utc || b.created_at_utc || '').localeCompare(String(a.completed_at_utc || a.created_at_utc || '')))[0]
        if (latest) {
          score.value = ''
          stage.value = stage.value || latest.growth_stage?.predicted_stage_name || ''
          confidence.value = confidence.value || latest.growth_stage?.confidence || ''
          if (latest.analysis_id) {
            const detailResponse = await fetch(`/api/growth/history/${encodeURIComponent(latest.analysis_id)}`)
            if (detailResponse.ok) {
              const detail = await detailResponse.json()
              score.value = deriveScore(detail) ?? detail.growth_analysis?.vigor_assessment?.vigor_score ?? detail.vigor_score ?? ''
              stage.value = stage.value || detail.growth_stage?.predicted_stage_name || ''
              confidence.value = confidence.value || detail.growth_stage?.confidence || ''
            }
          }
          if (score.value === '' || score.value == null) score.value = latest.vigor_score ?? ''
          analysisSource.value = '已同步最近一次真实长势分析记录'
        }
      }
    } catch { /* 历史接口失败时保留当前缓存状态 */ }
  }
  fetch('/api/growth-trend/status').then(response => response.ok ? response.json() : null).then(data => { predictionStatus.value = data }).catch(() => { predictionStatus.value = null })
})
const trendSeries = computed(() => {
  if (!result.value) return []
  const current = Number(result.value.current_summary?.vigor_score ?? score.value ?? 0)
  return [
    { label: '当前', value: current },
    { label: '7天', value: Number(result.value.horizons?.['7']?.estimates?.vigor_score?.value ?? current) },
    { label: '15天', value: Number(result.value.horizons?.['15']?.estimates?.vigor_score?.value ?? current) },
  ]
})
const chartPoints = computed(() => trendSeries.value.map((item, index) => `${index * 45 + 8},${96 - Math.max(0, Math.min(100, item.value)) * 0.76}`).join(' '))
async function run(){
  if(loading.value)return
  loading.value=true; error.value=''
  try{
    const payload={growth_stage:stage.value,vigor_score:score.value?Number(score.value):null,vigor_level:null,stage_confidence:confidence.value?Number(confidence.value):0,weather_status:weatherStatus.value,weather_risks:risks.value?risks.value.split(/[，,]/).map(item=>item.trim()).filter(Boolean):[],capture_date:captureDate.value||null,location:location.value||null}
    const r=await fetch('/api/growth-trend/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    const data=await r.json(); if(!r.ok)throw new Error(data?.error?.message||'趋势分析失败'); result.value=data
  }catch(e){error.value=e.message;result.value=null}finally{loading.value=false}
}
</script>
<template><div class="trend-page p2-layout"><header class="module-title"><div class="module-heading"><span class="module-icon"><BarChart3 :size="25" /></span><div><p class="module-eyebrow">SHORT-TERM GROWTH OUTLOOK</p><h1>生长预测</h1><p>沿着时间，关注下一阶段的生长变化。</p></div></div><span class="module-status"><span></span>{{ predictionStatus?.enabled === false ? '服务降级 · 基线可用' : '已启用 · 独立引擎' }}</span></header><div class="trend-workbench"><aside class="trend-panel trend-controls"><div class="control-heading"><span>预测条件</span><small>当前分析输入</small></div><div class="form-grid"><label>当前生育期<input v-model="stage" placeholder="请先在长势分析页完成识别" readonly title="来自最近一次长势分析" /></label><label>当前评分<input v-model="score" type="number" min="0" max="100" placeholder="请先完成长势分析" readonly title="来自最近一次长势分析" /></label><label>生育期置信度<input v-model="confidence" type="number" min="0" max="1" step="0.01" placeholder="请先完成生育期识别" readonly title="来自最近一次长势分析" /></label><label>天气状态<select v-model="weatherStatus"><option value="unavailable">不可用 / 使用基线</option><option value="succeeded">真实天气可用</option></select></label><label>当前拍摄日期<input v-model="captureDate" type="date" /></label><label class="wide location-field">种植地址（用于自动定位）<input v-model="location" placeholder="请填写省、市、县/区、乡镇或村，例如：河南省周口市淮阳区" /></label><small class="analysis-source">{{ analysisSource }}；填写详细地址后系统会自动定位，无需输入经纬度。</small><label class="wide">天气风险（用中文逗号分隔）<input v-model="risks" placeholder="例如：高温风险筛查" /></label></div><button @click="run" :disabled="loading"><LoaderCircle v-if="loading" class="spin" :size="16" />{{ loading?'分析中':'检查未来预测' }}</button><p v-if="error" class="error">{{ error }}</p></aside><main class="trend-main"><section class="trend-dashboard"><article class="trend-chart-card"><div class="dashboard-card-head"><div><span class="eyebrow">SHORT-TERM OUTLOOK</span><h2>长势变化趋势</h2></div><span class="chart-badge">规则估算</span></div><div v-if="!result" class="trend-empty-state"><div class="empty-chart-grid"><i></i><i></i><i></i><i></i></div><strong>等待趋势分析</strong><small>完成当前长势分析后显示7天与15天变化</small></div><div v-else class="line-chart"><svg viewBox="0 0 106 108" preserveAspectRatio="none" aria-label="长势趋势图"><line x1="8" y1="20" x2="98" y2="20"/><line x1="8" y1="58" x2="98" y2="58"/><line x1="8" y1="96" x2="98" y2="96"/><polyline :points="chartPoints" fill="none"/><circle v-for="(item,index) in trendSeries" :key="item.label" :cx="index * 45 + 8" :cy="96 - Math.max(0, Math.min(100, item.value)) * 0.76" r="2"/></svg><div class="chart-labels"><span v-for="item in trendSeries" :key="item.label">{{ item.label }}<b>{{ item.value.toFixed(1) }}</b></span></div></div></article><aside class="trend-kpi-card"><div class="dashboard-card-head"><h2>当前状态</h2><span class="chart-badge">{{ result?.current_summary?.growth_stage || '阶段待确认' }}</span></div><div class="kpi-row"><span>综合评分</span><strong>{{ Number(result?.current_summary?.vigor_score ?? 0).toFixed(1) }}</strong></div><div class="kpi-row"><span>生育期置信度</span><strong>{{ (Number(result?.current_summary?.stage_confidence || 0) * 100).toFixed(1) }}%</strong></div><div class="kpi-row"><span>天气依据</span><strong>{{ result?.weather?.status === 'succeeded' ? '已接入' : '基线' }}</strong></div></aside></section><section v-if="result" class="horizon-grid"><article v-for="key in ['7','15']" :key="key"><h2><CloudSun :size="18" />未来 {{ key }} 天</h2><strong>{{ result.horizons[key].trend }}</strong><p class="muted">可信度：{{ result.horizons[key].confidence }} · 天气覆盖：{{ result.horizons[key].data_completeness.weather_days_used }}/{{ result.horizons[key].data_completeness.weather_days_expected }} 天</p><p v-if="result.horizons[key].factors">{{ result.horizons[key].factors.join('；') }}</p><p v-if="result.horizons[key].weather_risks?.length">风险：{{ result.horizons[key].weather_risks.join('、') }}</p><p v-if="result.horizons[key].management">{{ result.horizons[key].management.join('；') }}</p><div v-if="result.horizons[key].estimates" class="estimate-box"><b>探索性指标估算</b><span>评分 {{ result.horizons[key].estimates.vigor_score.value }} · 覆盖 {{ (result.horizons[key].estimates.vegetation_coverage.value * 100).toFixed(1) }}%</span><span>LAI {{ result.horizons[key].estimates.lai.value }} · 生物量 {{ result.horizons[key].estimates.biomass_kg_per_ha.value }} kg/ha</span><span>亩产参考 {{ result.horizons[key].estimates.yield_kg_per_mu.value }} kg/亩</span></div><small>以上为规则推测区间，不是实测值或经过田间验证的预测。</small></article></section><section v-if="result" class="trend-panel result-meta"><b>预测依据与限制</b><p>{{ result.limitations.join('；') }}</p></section></main></div></div></template>
<style scoped>
.trend-page,
.yield-page{position:relative;isolation:isolate;display:block;width:100%;min-height:calc(100vh - 120px);padding:16px;color:#edf5e7;overflow:visible;box-sizing:border-box;background:transparent;border:0;border-radius:0;clip-path:none}
.trend-page::before,
.yield-page::before{content:"";position:absolute;inset:-24px -28px -20px;z-index:-2;background:url('../assets/growth-wheat-field-photo.jpg') center/cover no-repeat;filter:blur(6px) brightness(.42) saturate(.82);background-size:cover;background-position:center center;background-repeat:no-repeat}
.trend-page::after,
.yield-page::after{content:"";position:absolute;inset:-24px -28px -20px;z-index:-1;background:linear-gradient(125deg,#071b14ed,#0b2c1dd6 56%,#061811ee);pointer-events:none}
.trend-page header,
.yield-page header,.trend-panel,.yield-panel,.horizon-grid article,.scenario-grid article{background:rgba(14,46,31,.75);border:1px solid #a9d99d42;border-radius:15px;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);overflow:hidden;box-sizing:border-box;box-shadow:inset 0 1px #d8f0c312,0 10px 28px #020d0835}
.trend-page header,.yield-page header{display:flex;align-items:center;gap:14px;padding:22px;margin-bottom:14px}.trend-page header,.yield-page header{display:flex;align-items:center;gap:14px;padding:22px 0 26px;margin-bottom:14px;background:transparent;border-color:transparent;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}
.module-title{display:flex!important;justify-content:space-between;align-items:center;gap:20px;padding:12px 0 24px!important;background:transparent!important;border:0!important;box-shadow:none!important;backdrop-filter:none!important}.module-heading{display:flex;align-items:center;gap:14px}.module-icon{width:48px;height:48px;border-radius:13px;display:grid;place-items:center;background:#75d66b25;color:#a5e58a}.module-eyebrow{font-size:9px;letter-spacing:1.5px;color:#a5e58a;margin:0 0 5px}.module-title h1{font-size:28px;font-weight:500;margin:0 0 5px;color:#edf5e7}.module-title p:not(.module-eyebrow){font-size:11px;color:#b9cfb4;margin:0}.module-status{font-size:10px;color:#b9dfaa;border:1px solid #95d17b49;border-radius:20px;padding:8px 12px;background:#15392388;white-space:nowrap}.module-status span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#75d66b;margin-right:7px}.trend-page header h1,.yield-page header h1{margin:0;color:#f2f7ef;font-size:30px;line-height:1.15}
.trend-page header p,.yield-page header p{margin:7px 0 0;color:#a9c3ad}
.trend-page header svg,.yield-page header svg{color:#a5e58a;filter:drop-shadow(0 0 10px #75d66b45)}
.trend-page header > b,.yield-page header > b{margin-left:auto;border:1px solid #a5e58a45;border-radius:999px;padding:7px 12px;color:#c7e9bf;background:#183b286b;white-space:nowrap}.status-pill{margin-left:auto;border:1px solid #a5e58a45;border-radius:999px;padding:7px 12px;color:#c7e9bf;background:#183b286b;white-space:nowrap}
.trend-panel,.yield-panel{padding:24px}.p2-layout .trend-panel{min-height:250px;padding:26px 28px;margin-top:2px}.p2-layout .trend-panel::before{content:"";display:block;height:1px;background:linear-gradient(90deg,#a5e58a30,transparent);margin-bottom:18px}
.form-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}
.yield-form{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}
.form-grid label,.yield-form label{display:flex;flex-direction:column;gap:7px;color:#b9cfbb;font-size:13px;min-width:0}
.form-grid .wide{grid-column:span 2}.location-field{grid-column:span 2}.analysis-source{grid-column:span 4;color:#a5e58a;font-size:12px;padding:4px 0}
.form-grid input,.form-grid select,.yield-form input{appearance:none;-webkit-appearance:none;color-scheme:dark;width:100%;box-sizing:border-box;background:#0b2419!important;color:#edf5e7!important;border:1px solid #a5e58a42;border-radius:9px;padding:10px 11px;outline:none;font:inherit;min-height:42px}
.form-grid select{background-image:linear-gradient(45deg,transparent 50%,#a5e58a 50%),linear-gradient(135deg,#a5e58a 50%,transparent 50%)!important;background-position:calc(100% - 16px) 50%,calc(100% - 11px) 50%!important;background-size:5px 5px!important;background-repeat:no-repeat!important;padding-right:30px}
.form-grid input:focus,.form-grid select:focus,.yield-form input:focus{border-color:#a5e58a;box-shadow:0 0 0 3px #75d66b20}
.form-grid input::placeholder,.yield-form input::placeholder{color:#78917d}
.trend-panel > button,.yield-panel > button,.primary-btn{margin-top:15px;border:1px solid #c0eca865;border-radius:10px;background:linear-gradient(135deg,#a5e58a,#64bd69);color:#102719;font-weight:700;padding:11px 18px;cursor:pointer;box-shadow:0 8px 20px #071b1450;transition:transform .18s ease,filter .18s ease}
.trend-panel > button:hover,.yield-panel > button:hover,.primary-btn:hover{transform:translateY(-2px);filter:brightness(1.08)}
.trend-panel > button:disabled,.yield-panel > button:disabled,.primary-btn:disabled{opacity:.6;cursor:not-allowed;transform:none}
.note{margin:12px 0 0;color:#92ac96;font-size:13px}
.horizon-grid,.scenario-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;margin-top:15px}
.horizon-grid article,.scenario-grid article{padding:18px;min-height:150px}
.horizon-grid h3,.scenario-grid h3{margin:0 0 10px;color:#dcefd8}
.horizon-grid p,.scenario-grid p,.result-meta p{color:#aac3ad;line-height:1.65}.estimate-box{display:grid;gap:5px;margin-top:12px;padding:10px;border:1px solid #a5e58a35;border-radius:10px;background:#0b24198c;color:#c9e8c2;font-size:12px}.estimate-box span{color:#a9c3ad}.muted{font-size:12px;color:#8fa995!important}
.trend-workbench{display:block}.trend-controls{display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px;min-height:0;padding:14px!important;margin-bottom:15px}.trend-controls .control-heading{display:flex;flex-direction:column;gap:4px;min-width:150px;padding:0 12px 0 0;margin:0;border-right:1px solid #75d66b24}.trend-controls .control-heading span{font-size:15px;color:#edf5e7}.trend-controls .control-heading small{font-size:10px;color:#9fb7a4}.trend-controls .form-grid{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));flex:1;gap:12px}.trend-controls .form-grid .wide{grid-column:span 2}.trend-controls .analysis-source{grid-column:1/-1;order:5}.trend-controls>button{width:auto;margin:0;min-height:42px}.trend-main{min-width:0;display:grid;gap:15px}.trend-main .trend-dashboard,.trend-main .horizon-grid,.trend-main .result-meta{margin-top:0}@media(max-width:1050px){.trend-controls .control-heading{width:100%;border-right:0;border-bottom:1px solid #75d66b24;padding:0 0 10px}.trend-controls .form-grid{grid-template-columns:repeat(2,minmax(130px,1fr))}}@media(max-width:760px){.trend-controls{display:block}.trend-controls .control-heading{margin-bottom:14px}.trend-controls .form-grid{grid-template-columns:1fr}.trend-controls .form-grid .wide{grid-column:auto}.trend-controls .analysis-source{display:block;margin:10px 0}.trend-controls>button{width:100%;margin-top:12px}}
.trend-empty-state{height:140px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;color:#a9c3ad}.trend-empty-state strong{font-size:14px;color:#d9edcf}.trend-empty-state small{font-size:10px}.empty-chart-grid{display:flex;align-items:flex-end;gap:8px;height:42px;width:150px;padding:0 7px;border-bottom:1px solid #a5e58a35}.empty-chart-grid i{display:block;flex:1;background:#75d66b22;border:1px solid #a5e58a32;border-radius:5px 5px 0 0}.empty-chart-grid i:nth-child(1){height:35%}.empty-chart-grid i:nth-child(2){height:58%}.empty-chart-grid i:nth-child(3){height:44%}.empty-chart-grid i:nth-child(4){height:74%}.trend-controls .analysis-source{font-size:10px}.trend-controls label{font-size:11px}.trend-dashboard{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(260px,.8fr);gap:15px;margin-top:15px}.trend-chart-card,.trend-kpi-card{padding:20px;background:rgba(14,46,31,.75);border:1px solid #a9d99d42;border-radius:15px;backdrop-filter:blur(14px);box-shadow:inset 0 1px #d8f0c312,0 10px 28px #020d0835}.dashboard-card-head{display:flex;justify-content:space-between;align-items:center;gap:12px}.dashboard-card-head h2{margin:0;color:#e8f3e5;font-size:18px}.chart-badge{border:1px solid #a5e58a45;border-radius:999px;padding:5px 9px;color:#a5e58a;font-size:11px}.line-chart{margin-top:14px}.line-chart svg{display:block;width:100%;height:140px;overflow:visible}.line-chart line{stroke:#a5e58a18;stroke-width:.6;stroke-dasharray:2 2}.line-chart polyline{stroke:#a5e58a;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 5px #75d66b65)}.line-chart circle{fill:#d8f0b2;stroke:#75d66b;stroke-width:1}.chart-labels{display:grid;grid-template-columns:repeat(3,1fr);color:#8fab94;font-size:11px}.chart-labels span{display:flex;flex-direction:column;gap:4px}.chart-labels b{color:#d2edc4;font-size:14px}.kpi-row{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #a9d99d24;padding:17px 0;color:#a9c3ad;font-size:13px}.kpi-row:last-child{border-bottom:0}.kpi-row strong{color:#c9edbb;font-size:18px}.trend-dashboard + .horizon-grid{margin-top:15px}@media (max-width:1050px){.form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.yield-form{grid-template-columns:repeat(2,minmax(0,1fr))}.form-grid .wide{grid-column:span 2}.location-field{grid-column:span 2}.analysis-source{grid-column:span 4;color:#a5e58a;font-size:12px;padding:4px 0}}
@media (max-width:700px){.trend-dashboard{grid-template-columns:1fr}.trend-page,.yield-page{padding:10px}.trend-page header,.yield-page header{padding:16px;align-items:flex-start}.module-title{display:flex!important;justify-content:space-between;align-items:center;gap:20px;padding:12px 0 24px!important;background:transparent!important;border:0!important;box-shadow:none!important;backdrop-filter:none!important}.module-heading{display:flex;align-items:center;gap:14px}.module-icon{width:48px;height:48px;border-radius:13px;display:grid;place-items:center;background:#75d66b25;color:#a5e58a}.module-eyebrow{font-size:9px;letter-spacing:1.5px;color:#a5e58a;margin:0 0 5px}.module-title h1{font-size:28px;font-weight:500;margin:0 0 5px;color:#edf5e7}.module-title p:not(.module-eyebrow){font-size:11px;color:#b9cfb4;margin:0}.module-status{font-size:10px;color:#b9dfaa;border:1px solid #95d17b49;border-radius:20px;padding:8px 12px;background:#15392388;white-space:nowrap}.module-status span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#75d66b;margin-right:7px}.trend-page header h1,.yield-page header h1{font-size:24px}.trend-page header > b,.yield-page header > b{margin-left:auto;border:1px solid #a5e58a45;border-radius:999px;padding:7px 12px;color:#c7e9bf;background:#183b286b;white-space:nowrap}.trend-page header > b,.yield-page header > b,.status-pill{margin-left:0;margin-top:3px}.form-grid,.yield-form,.horizon-grid,.scenario-grid{grid-template-columns:1fr}.form-grid .wide{grid-column:auto}.trend-panel,.yield-panel{padding:14px}}
</style>

