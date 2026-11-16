<script setup>
import { computed, nextTick, onUnmounted, ref, useId, watch } from 'vue'
import { CircleHelp } from 'lucide-vue-next'
import { algorithmHelp } from '../config/algorithmHelp.js'

const props = defineProps({ algorithm: { type: String, required: true } })
const help = computed(() => algorithmHelp[props.algorithm])
const trigger = ref(null)
const popup = ref(null)
const visible = ref(false)
const positioned = ref(false)
const tooltipId = `algorithm-help-${useId()}`
const position = ref({ left: '12px', top: '12px' })
let focused = false
let overButton = false
let overPopup = false
let hideTimer = null
let frame = null

function updatePosition() {
  if (!visible.value || !trigger.value || !popup.value) return
  const box = trigger.value.getBoundingClientRect()
  const tip = popup.value.getBoundingClientRect()
  const margin = 12
  const gap = 10
  let left = box.right + gap
  if (left + tip.width > window.innerWidth - margin) left = box.left - tip.width - gap
  left = Math.max(margin, Math.min(left, window.innerWidth - tip.width - margin))
  const top = Math.max(margin, Math.min(box.top - 8, window.innerHeight - tip.height - margin))
  position.value = { left: `${left}px`, top: `${top}px` }
  positioned.value = true
}

function schedulePosition() {
  if (frame !== null) return
  frame = requestAnimationFrame(() => { frame = null; updatePosition() })
}

async function show() {
  clearTimeout(hideTimer)
  if (!help.value) return
  if (!visible.value) positioned.value = false
  visible.value = true
  await nextTick()
  updatePosition()
}

function close() {
  clearTimeout(hideTimer)
  overPopup = false
  visible.value = false
}

function scheduleHide() {
  clearTimeout(hideTimer)
  // 留出移入说明卡片的时间；键盘聚焦期间保持可读。
  if (!focused && !overButton && !overPopup) hideTimer = setTimeout(close, 120)
}

function onOutsidePointer(event) {
  if (!trigger.value?.contains(event.target) && !popup.value?.contains(event.target)) close()
}

function onEscape(event) {
  if (event.key === 'Escape') close()
}

function removeListeners() {
  document.removeEventListener('pointerdown', onOutsidePointer, true)
  document.removeEventListener('keydown', onEscape)
  window.removeEventListener('resize', schedulePosition)
  window.removeEventListener('scroll', schedulePosition, true)
}

watch(visible, value => {
  if (value) {
    document.addEventListener('pointerdown', onOutsidePointer, true)
    document.addEventListener('keydown', onEscape)
    window.addEventListener('resize', schedulePosition)
    window.addEventListener('scroll', schedulePosition, true)
  } else removeListeners()
})

onUnmounted(() => {
  clearTimeout(hideTimer)
  if (frame !== null) cancelAnimationFrame(frame)
  removeListeners()
})
</script>

<template>
  <span v-if="help" class="algorithm-help">
    <button ref="trigger" type="button" class="algorithm-help-trigger" :aria-label="`了解 ${algorithm} 的区别与侧重点`" :aria-describedby="visible ? tooltipId : undefined"
      @mouseenter="overButton=true; show()" @mouseleave="overButton=false; scheduleHide()"
      @focus="focused=true; show()" @blur="focused=false; scheduleHide()" @click.stop="show">
      <CircleHelp :size="15" :stroke-width="1.7" aria-hidden="true" />
    </button>
    <!-- 说明层挂到 body，避免被玻璃面板或结果卡片裁切。 -->
    <Teleport to="body">
      <div v-if="visible" :id="tooltipId" ref="popup" role="tooltip" class="algorithm-help-popup" :style="{...position,visibility:positioned?'visible':'hidden'}"
        @mouseenter="overPopup=true; show()" @mouseleave="overPopup=false; scheduleHide()">
        <strong class="help-algorithm-name">{{ algorithm }}</strong><h3>{{ help.headline }}</h3>
        <dl><div><dt>怎么判断</dt><dd>{{ help.rule }}</dd></div><div><dt>侧重点</dt><dd>{{ help.focus }}</dd></div><div><dt>需要留意</dt><dd>{{ help.caution }}</dd></div></dl>
        <p>植被占比不是识别准确率</p>
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.algorithm-help{display:inline-flex;vertical-align:middle;flex-shrink:0;line-height:1}
.algorithm-help .algorithm-help-trigger{display:grid;place-items:center;width:25px;height:25px;min-height:0;padding:0;border:1px solid #b5d8a43a;border-radius:50%;background:#133a2766;color:#b9d9a5;cursor:help;transition:background .15s,border-color .15s}
.algorithm-help .algorithm-help-trigger:hover,.algorithm-help .algorithm-help-trigger:focus-visible{background:#86bb5036;border-color:#b9e89691;color:#e1f4d2}.algorithm-help-trigger:focus-visible{outline:2px solid #a5e58a;outline-offset:3px}
.algorithm-help-popup{position:fixed;z-index:3000;width:min(300px,calc(100vw - 24px));box-sizing:border-box;max-height:calc(100vh - 24px);overflow:auto;padding:18px;background:rgba(10,36,25,.97);border:1px solid #b4da9270;border-radius:12px;box-shadow:0 12px 36px #0007,inset 0 1px 0 #d1edb912;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);color:#e6f0df;text-align:left;font-family:inherit;line-height:1.7}
.help-algorithm-name{font-size:11px;letter-spacing:.2px;color:#b7dd98;font-weight:500}.algorithm-help-popup h3{font-size:14px;font-weight:500;color:#f0f7e9;margin:5px 0 13px;line-height:1.6}.algorithm-help-popup dl{margin:0;display:grid;gap:12px}.algorithm-help-popup dt{font-size:10px;color:#a8c492;margin-bottom:3px}.algorithm-help-popup dd{font-size:12px;color:#dce9d3;line-height:1.8;margin:0}.algorithm-help-popup>p{font-size:10px;color:#d2c599;border-top:1px solid #b5d8a424;padding-top:11px;margin:13px 0 0}
@supports not (backdrop-filter:blur(1px)){.algorithm-help-popup{background:#0a2419}}
</style>
