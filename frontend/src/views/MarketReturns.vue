<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, BarChart3, Landmark, LoaderCircle, Wheat } from 'lucide-vue-next'

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const status = ref(null)
const history = ref([])
const forecast = ref(null)
const loading = ref(true)
const error = ref('')
const areaMu = ref(1)
const yieldPerMu = ref(450)
const cost = ref(0)
const referencePrice = computed(() => status.value?.current_price_yuan_per_ton || 0)
const quantity = computed(() => Number(areaMu.value || 0) * Number(yieldPerMu.value || 0) / 1000)
const revenue = computed(() => quantity.value * referencePrice.value)
const profit = computed(() => revenue.value - Number(cost.value || 0))

async function request(path, options) {
  const response = await fetch(`${apiBase}${path}`, options)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload?.error?.message || '价格服务暂不可用。')
  return payload
}
async function load() {
  loading.value = true
  try {
    const [statusPayload, historyPayload] = await Promise.all([request('/api/price/status'), request('/api/price/history')])
    status.value = statusPayload
    history.value = historyPayload.items || []
    if (statusPayload.forecast_enabled) forecast.value = await request('/api/price/forecast?horizon_days=30', { method: 'POST' })
  } catch (caught) { error.value = caught.message || '价格服务暂不可用。' } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="market-page">
    <header class="market-heading"><div><span class="eyebrow">NATIONAL WHEAT MARKET</span><h1>市场与收益</h1><p>基于全国小麦平均收购价格的真实数据与透明基线。</p></div><span class="market-status"><span></span>{{ status?.status === 'ready' ? '可进行回测' : '数据持续接入' }}</span></header>
    <p v-if="error" class="market-error"><AlertTriangle :size="16" />{{ error }}</p>
    <div v-if="loading" class="market-empty"><LoaderCircle class="spin" :size="22" />正在读取官方价格数据</div>
    <template v-else>
      <section class="market-grid"><article class="market-panel price-hero"><div><span>当前全国平均收购价</span><strong>{{ status?.current_price_yuan_per_ton == null ? '—' : status.current_price_yuan_per_ton.toFixed(0) }}</strong><small>元/吨 · 数据截止 {{ status?.latest_date || '—' }}</small></div><Landmark :size="42" /></article><article class="market-panel"><span>已核验观测</span><strong>{{ status?.count ?? 0 }}</strong><small>条官方周度记录 · 最高 {{ status?.highest_price_yuan_per_ton ?? '—' }} / 最低 {{ status?.lowest_price_yuan_per_ton ?? '—' }}</small></article><article class="market-panel"><span>近期方向</span><strong>{{ status?.trend?.direction === 'unavailable' ? '待积累数据' : status.trend.direction }}</strong><small>近4周变化：{{ status?.trend?.four_week_change_yuan_per_ton ?? '—' }} 元/吨</small></article></section>
      <section class="market-columns"><article class="market-panel chart-panel"><div class="panel-head"><h2><BarChart3 :size="17" />历史价格</h2><span>{{ history.length }} 条真实记录</span></div><div v-if="history.length" class="price-list"><div v-for="item in history" :key="item.date" class="price-row"><span>{{ item.date }}</span><i :style="{ width: `${Math.max(8, Math.min(100, (item.price_yuan_per_ton / (status.current_price_yuan_per_ton || 1)) * 70))}%` }"></i><b>{{ item.price_yuan_per_ton.toFixed(0) }}</b></div></div><div v-else class="chart-empty">暂无可展示的真实历史序列。</div><small class="source-note">来源：国家粮食和物资储备局全国主要粮食品种收购价格周报；不同统计口径不混合。</small></article><article class="market-panel chart-panel"><div class="panel-head"><h2><Wheat :size="17" />未来价格预估</h2><span>{{ forecast?.status === 'succeeded' ? forecast.model : '尚未启用' }}</span></div><div v-if="forecast?.status === 'succeeded'" class="price-list"><div v-for="item in forecast.points.filter(point => point.model === 'mean_last_4_weeks')" :key="item.target_date" class="price-row"><span>{{ item.target_date }}</span><i :style="{ width: `${Math.max(8, Math.min(100, (item.forecast_yuan_per_ton / (status.current_price_yuan_per_ton || 1)) * 70))}%` }"></i><b>{{ item.forecast_yuan_per_ton.toFixed(0) }}</b></div></div><div v-else class="chart-empty"><AlertTriangle :size="24" /><strong>预测模型待启用</strong><span>{{ status?.message || '至少需要连续真实周度数据并完成滚动回测。' }}</span></div></article></section>
      <section class="market-panel harvest-panel"><div class="panel-head"><h2><Wheat :size="17" />2027年收获期价格展望</h2><span>情景参考</span></div><div class="harvest-scenarios"><article><b>正常</b><strong>{{ forecast?.harvest_scenarios?.normal || "待积累历史季节性" }}</strong></article><article><b>偏强</b><strong>{{ forecast?.harvest_scenarios?.strong || "待验证" }}</strong></article><article><b>偏弱</b><strong>{{ forecast?.harvest_scenarios?.weak || "待验证" }}</strong></article></div></section>
      <section class="market-panel profit-panel"><div class="panel-head"><h2>经营收益估算</h2><span>价格仅作参考，不等同成交价</span></div><div class="profit-form"><label>种植面积（亩）<input v-model.number="areaMu" type="number" min="0" step="1" /></label><label>预计亩产（公斤）<input v-model.number="yieldPerMu" type="number" min="0" step="10" /></label><label>预计总成本（元）<input v-model.number="cost" type="number" min="0" step="100" /></label></div><div class="profit-result"><div><span>预计总产量</span><strong>{{ quantity.toFixed(2) }} 吨</strong></div><div><span>参考销售收入</span><strong>{{ revenue.toFixed(2) }} 元</strong></div><div><span>参考利润</span><strong>{{ profit.toFixed(2) }} 元</strong></div></div></section>
      <section class="market-panel notice-panel"><AlertTriangle :size="18" /><span>当前页面只展示可追溯的全国平均收购价格。历史数据不足时不会生成 30 天或下一年度收获期预测；收获期预测需要更长的连续历史并经过独立回测。</span></section>
    </template>
  </div>
</template>

<style scoped>
.market-page{padding:8px 0 35px;color:#edf5e7}.market-heading{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;gap:20px}.eyebrow{font-size:9px;letter-spacing:1.7px;color:#a5e58a}.market-heading h1{font-size:28px;font-weight:500;margin:6px 0}.market-heading p{font-size:11px;color:#aac4a3}.market-status{padding:8px 12px;border:1px solid #a5e58a38;border-radius:20px;color:#c9e8bb;font-size:10px}.market-status span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#75d66b;margin-right:6px}.market-error,.market-empty,.market-panel{background:rgba(14,46,31,.68);border:1px solid #a9d99d32;border-radius:14px;backdrop-filter:blur(13px)}.market-error{display:flex;gap:7px;padding:10px;color:#f1c49a;font-size:11px}.market-empty{min-height:260px;display:flex;align-items:center;justify-content:center;gap:9px;color:#9fb7a4;font-size:11px}.market-grid{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:14px;margin-bottom:15px}.market-panel{padding:16px}.market-panel>span,.market-panel small{display:block;color:#9fb7a4;font-size:10px}.market-panel strong{display:block;color:#c8eead;font-size:26px;font-weight:400;margin:8px 0}.price-hero{display:flex;align-items:center;justify-content:space-between}.price-hero svg{color:#a5e58a}.market-columns{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:15px}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}.panel-head h2{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:500;margin:0}.panel-head h2 svg{color:#a5e58a}.panel-head>span{font-size:9px;color:#9fb7a4}.price-list{display:grid;gap:9px}.price-row{display:grid;grid-template-columns:86px 1fr 58px;align-items:center;gap:8px;font-size:9px;color:#9fb7a4}.price-row i{height:7px;border-radius:99px;background:linear-gradient(90deg,#477653,#a5e58a)}.price-row b{text-align:right;color:#d5f6bd;font-weight:400}.source-note{display:block;margin-top:13px;color:#789476;font-size:8px;line-height:1.5}.chart-empty{min-height:180px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:#9fb7a4;font-size:10px}.chart-empty svg{color:#d8b65c}.harvest-panel{margin-bottom:15px}.harvest-scenarios{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.harvest-scenarios article{display:flex;flex-direction:column;gap:7px;padding:11px;border:1px solid #a5e58a1c;border-radius:8px;background:#75d66b08}.harvest-scenarios b{font-size:10px;color:#cfe8c7}.harvest-scenarios strong{font-size:10px;color:#9fb7a4;font-weight:400}.profit-panel{margin-bottom:15px}.profit-form{display:flex;gap:12px}.profit-form label{display:flex;flex-direction:column;gap:5px;color:#9fb7a4;font-size:9px}.profit-form input{width:150px;padding:8px;border-radius:7px;border:1px solid #a5e58a2f;background:#143a28;color:#ecf6e9}.profit-result{display:flex;gap:38px;margin-top:15px}.profit-result span{display:block;color:#9fb7a4;font-size:9px}.profit-result strong{display:block;color:#c8eead;font-size:19px;margin-top:5px;font-weight:400}.notice-panel{display:flex;gap:9px;align-items:flex-start;color:#d8c88f;font-size:10px;line-height:1.6}.notice-panel svg{flex-shrink:0;color:#d8b65c}@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}@media(max-width:800px){.market-grid,.market-columns,.harvest-scenarios{grid-template-columns:1fr}.profit-form,.profit-result{flex-direction:column}.market-heading{flex-direction:column}.market-status{align-self:flex-start}}
</style>




