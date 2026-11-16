// 未来长势预测接口；只有后端返回真实可用模型时才展示预测值。
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try { response = await fetch(`${apiBase}${path}`, options) } catch { throw new Error('无法连接未来预测服务。') }
  let payload
  try { payload = await response.json() } catch { throw new Error('未来预测服务没有正确响应。') }
  if (!response.ok) throw new Error(payload?.error?.message || '未来预测暂不可用。')
  return payload
}

export function getForecastStatus(signal) { return request('/api/growth-forecast/status', { signal }) }

export function predictFutureGrowth(file, options = {}) {
  const form = new FormData()
  form.append('file', file)
  if (options.currentStage) form.append('current_stage', options.currentStage)
  if (options.captureDate) form.append('capture_date', options.captureDate)
  if (options.latitude != null) form.append('latitude', String(options.latitude))
  if (options.longitude != null) form.append('longitude', String(options.longitude))
  if (options.location) form.append('location', options.location)
  if (options.historyAnalysisIds?.length) form.append('history_analysis_ids', JSON.stringify(options.historyAnalysisIds))
  return request('/api/growth-forecast/predict', { method: 'POST', body: form, signal: options.signal })
}
