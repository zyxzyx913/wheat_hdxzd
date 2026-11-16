// 科研标注管理 API。普通业务页面不调用这些接口，所有请求附带本地科研访问头。
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const accessHeaders = { 'X-Research-Access': 'local-research' }

async function researchRequest(path, options = {}) {
  let response
  try {
    response = await fetch(`${apiBase}${path}`, { ...options, headers: { ...accessHeaders, ...(options.headers || {}) } })
  } catch {
    throw new Error('无法连接科研标注服务，请确认 FastAPI 后端已启动。')
  }
  let payload
  try { payload = await response.json() } catch { payload = null }
  if (!response.ok) throw new Error(payload?.detail || payload?.error?.message || '科研标注服务暂不可用。')
  return payload
}

export function getAnnotationTasks() { return researchRequest('/api/research/annotation/tasks') }
export function getAnnotationStatus() { return researchRequest('/api/research/annotation/status') }
export function getAnnotationConsistency() { return researchRequest('/api/research/annotation/consistency') }

export async function getAnnotationImage(anonymousId) {
  const response = await fetch(`${apiBase}/api/research/annotation/image/${encodeURIComponent(anonymousId)}`, { headers: accessHeaders })
  if (!response.ok) throw new Error('标注图片读取失败。')
  return URL.createObjectURL(await response.blob())
}

export function submitAnnotation(payload) {
  return researchRequest('/api/research/annotation/records', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function submitAdjudication(payload) {
  return researchRequest('/api/research/annotation/adjudications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function exportAnnotations() {
  const response = await fetch(`${apiBase}/api/research/annotation/export`, { headers: accessHeaders })
  if (!response.ok) throw new Error('当前还没有可导出的标注记录。')
  return URL.createObjectURL(await response.blob())
}
