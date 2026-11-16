// 保存最近一次真实图像分析任务的引用，让图像识别页和长势分析页共享结果。
// 这里只保存任务元数据与后端媒体地址，不把本地图片二进制写入浏览器存储。
const STORAGE_KEY = 'maishitong.latest-image-analysis.v1'

export function saveLatestAnalysis(payload) {
  if (typeof window === 'undefined' || !payload?.result?.task_id) return
  try {
    const previous = loadLatestAnalysis() || {}
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...previous, ...payload, savedAt: new Date().toISOString() }))
  } catch { /* 浏览器禁用 localStorage 时不影响当前页面 */ }
}

export function loadLatestAnalysis() {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed?.result?.task_id ? parsed : null
  } catch { return null }
}

export function clearLatestAnalysis() {
  if (typeof window === 'undefined') return
  try { window.localStorage.removeItem(STORAGE_KEY) } catch { /* 忽略存储权限限制 */ }
}
