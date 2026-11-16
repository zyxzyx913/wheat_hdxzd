<script setup>
// 原创植物学风格装饰图版，不是样本、器官识别或实测结果。
defineProps({ compact: Boolean })
const stems = [{ x: 175, y: 66, r: -13 }, { x: 264, y: 31, r: 10 }]
</script>
<template>
  <figure class="wheat-plate" :class="{ compact }">
    <span class="plate-heading">小麦 · 植物图版</span>
    <svg viewBox="0 0 420 490" fill="none" aria-hidden="true">
      <ellipse cx="220" cy="265" rx="142" ry="191" stroke="currentColor" opacity=".12" />
      <path d="M52 422H365M212 45V450" stroke="currentColor" stroke-dasharray="2 7" opacity=".15" />
      <g v-for="stem in stems" :key="stem.x" :transform="`translate(${stem.x} ${stem.y}) rotate(${stem.r})`" stroke="#6F8A57" stroke-width="1.4">
        <path d="M0 0C-3 110 9 265 0 382" />
        <path d="M0 223C-25 192 -58 149 -76 131C-68 183 -39 221 0 243M2 278C40 214 60 202 80 187C58 248 34 273 2 295" fill="#6F8A57" fill-opacity=".13" />
        <path d="M-76 131Q-29 200 0 237M80 187Q40 252 2 289" opacity=".6" />
        <g v-for="n in 9" :key="n" :transform="`translate(0 ${n * 11})`" stroke="#AF9243">
          <path d="M0 14C-21 6 -26 -8 -21 -18C-8 -16 1 -2 0 14ZM0 14C21 6 26 -8 21 -18C8 -16 -1 -2 0 14Z" fill="#D4B04C" fill-opacity=".25" />
          <path d="M-21 -18L-33 -58M21 -18L33 -58M-4 8L-18 -12M4 8L18 -12" stroke-width=".8" />
        </g>
        <path d="M0 13V-28" stroke="#AF9243" />
      </g>
      <path d="M165 430Q140 452 131 465M168 431Q163 461 169 476M175 433Q187 462 203 470M244 429Q226 448 222 469M248 432Q251 456 265 473M249 431Q276 449 294 455" stroke="#9C8A64" stroke-width=".9" />
      <path d="M303 139H361M290 279H359" stroke="#A78E58" stroke-width=".7" opacity=".6" /><circle cx="303" cy="139" r="2" fill="#BDA35C" /><circle cx="290" cy="279" r="2" fill="#BDA35C" />
    </svg>
    <figcaption><span>麦穗 · 叶片 · 生长</span><small>品牌植物插画 · 非识别结果</small></figcaption>
  </figure>
</template>
