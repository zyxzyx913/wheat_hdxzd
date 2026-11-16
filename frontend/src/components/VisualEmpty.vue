<script setup>
import { ImagePlus, ChartNoAxesCombined, Files, Sprout, PieChart } from 'lucide-vue-next'
defineProps({ title: {type:String,default:'等待数据接入'}, kind: {type:String,default:'chart'}, note: {type:String,default:'功能建设中'}, compact:Boolean })
</script>
<template>
  <div class="visual-empty" :class="[kind,{compact}]" role="note" :aria-label="title + '，' + note">
    <div v-if="kind === 'chart'" class="chart-scaffold" aria-hidden="true"><i v-for="n in 4" :key="n"></i></div>
    <div v-if="kind === 'ring'" class="empty-ring" aria-hidden="true"><PieChart :size="26" :stroke-width="1.2" /></div>
    <span v-else class="visual-empty-icon"><ImagePlus v-if="kind==='image'" :size="30" :stroke-width="1.2" /><Files v-else-if="kind==='report'" :size="30" :stroke-width="1.2" /><Sprout v-else-if="kind==='plant'" :size="33" :stroke-width="1.2" /><ChartNoAxesCombined v-else :size="29" :stroke-width="1.2" /></span>
    <strong>{{ title }}</strong><small>{{ note }}</small>
  </div>
</template>

