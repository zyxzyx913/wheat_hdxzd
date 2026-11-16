<script setup>
import { Box, Layers3 } from 'lucide-vue-next'
// 只预留展示容器；不生成假模型、假点云或分析结论。
</script>
<template>
  <section class="model-reserve" aria-label="小麦三维模型展示预留区域">
    <div class="model-reserve-heading"><span><Layers3 :size="16" />小麦空间研究</span><span class="archive-status">功能建设中</span></div>
    <div class="model-reserve-stage"><div class="model-floor" aria-hidden="true"></div><span class="model-box"><Box :size="34" :stroke-width="1" /></span><h2>三维模型展示区</h2><p>预留小麦三维图像、点云与重建结果展示</p><small>暂无已接入的模型或点云数据</small></div>
  </section>
</template>
