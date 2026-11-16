// V2.0 长势一体化 API；当前结果全部来自真实上传图片和后端计算。
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try { response = await fetch(`${apiBase}${path}`, options) } catch { throw new Error('无法连接分析服务，请确认 FastAPI 后端已启动。') }
  let payload
  try { payload = await response.json() } catch { throw new Error('分析服务没有正确响应。') }
  if (!response.ok) throw new Error(payload?.error?.message || '长势分析暂不可用。')
  return payload
}

export async function analyzeGrowth(file, signal, algorithm = 'ExG', plotId = '') {
  const form = new FormData()
  form.append('file', file)
  form.append('algorithm', algorithm)
  if (plotId) form.append('plot_id', plotId)
  const result = await request('/api/growth/analyze', { method: 'POST', body: form, signal })
  if (!result || result.status !== 'succeeded' || !/^[a-f0-9]{32}$/.test(result.analysis_id)
    || !Number.isFinite(result.vigor_score) || result.vigor_score < 0 || result.vigor_score > 100
    || !Number.isFinite(result.coverage_score) || !Number.isFinite(result.greenness_score)
    || !Number.isFinite(result.uniformity_score) || !result.reliability
    || !result.original_url || !result.mask_url || !result.overlay_url) {
    throw new Error('长势分析结果不完整，当前不展示成功结果。')
  }
  return result
}

export async function getGrowthHistory(signal) {
  const result = await request('/api/growth/history', { signal })
  return Array.isArray(result?.items) ? result.items : []
}

export function getGrowthHistoryItem(analysisId, signal) {
  return request(`/api/growth/history/${encodeURIComponent(analysisId)}`, { signal })
}

export function deleteGrowthHistory(analysisId) {
  return request(`/api/growth/history/${encodeURIComponent(analysisId)}`, { method: 'DELETE' })
}

export function growthMediaUrl(path) { return `${apiBase}${path || ''}` }
