// 统一请求地址：开发/预览由 Vite 代理；部署时也可设置后端服务地址。
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

// 名称与 Python 注册表保持一致；描述用于普通用户选择方案。
export const segmentationAlgorithms = Object.freeze([
  { name: 'ExG', description: '植被颜色指数' },
  { name: 'HSV', description: '绿色范围提取' },
  { name: 'Otsu-ExG', description: '自动阈值提取' },
  { name: 'ExG-HSV Fusion', description: '双特征交集融合' },
])

export function imageUrl(path) {
  return `${apiBase}${path}`
}

// 某些 Windows/浏览器环境会隐藏或丢失文件后缀，但仍会提供正确 MIME。
// 仅在 MIME 明确为 JPEG/PNG 且文件名没有支持的后缀时补齐后缀；真实编码仍由后端 Pillow 校验。
export function normalizeImageFile(file) {
  if (!file) return file
  const extension = file.type === 'image/png' ? '.png' : file.type === 'image/jpeg' ? '.jpg' : ''
  if (!extension) return file
  const currentExtension = (file.name || '').match(/\.(jpg|jpeg|png)$/i)?.[0]?.toLowerCase()
  if (currentExtension === extension || (extension === '.jpg' && currentExtension === '.jpeg')) return file
  return new File([file], `${file.name || 'wheat-image'}${extension}`, { type: file.type, lastModified: file.lastModified })
}

function connectionError(message) {
  const error = new Error(message)
  error.connectionFailed = true
  return error
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${apiBase}${path}`, options)
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw connectionError('无法连接分析服务，请确认后端已在本机 8000 端口启动。')
  }
  let payload
  try {
    payload = await response.json()
  } catch {
    throw connectionError('分析服务没有正确响应，请确认后端已启动。')
  }
  if (!response.ok) {
    throw new Error(payload.error?.message || '分析服务暂不可用，请稍后重试。')
  }
  return payload
}

export function getImageServiceHealth(signal) {
  return request('/api/health', { signal })
}

export async function analyzeImage(file, signal, algorithm = 'ExG') {
  if (!segmentationAlgorithms.some(item => item.name === algorithm)) throw new Error('请选择有效的识别方案。')
  const form = new FormData()
  form.append('file', normalizeImageFile(file))
  form.append('algorithm', algorithm)
  // 由浏览器生成 multipart boundary，不手工设置 Content-Type。
  const result = await request('/api/image/analyze', { method: 'POST', body: form, signal })
  const numericFields = ['width', 'height', 'vegetation_pixel_count', 'total_valid_pixels', 'vegetation_ratio', 'analysis_time_seconds']
  if (!result || result.status !== 'succeeded' || result.algorithm !== algorithm || !/^[a-f0-9]{32}$/.test(result.task_id)
    || !/^[a-f0-9]{64}$/.test(result.input_sha256)
    || numericFields.some(key => !Number.isFinite(result[key]))
    || ['width', 'height', 'vegetation_pixel_count', 'total_valid_pixels'].some(key => !Number.isInteger(result[key]))
    || result.total_valid_pixels !== result.width * result.height
    || result.width <= 0 || result.height <= 0 || result.vegetation_pixel_count < 0 || result.analysis_time_seconds < 0
    || result.total_valid_pixels <= 0 || result.vegetation_ratio < 0 || result.vegetation_ratio > 1
    || Math.abs(result.vegetation_ratio - result.vegetation_pixel_count / result.total_valid_pixels) > 1e-12
    || ['original', 'mask', 'overlay'].some(key => result[`${key}_url`] !== `/media/${result.task_id}/${key}.png`)) {
    throw new Error('返回的分析结果不完整，请重新分析；当前不展示成功结果。')
  }
  return result
}

export async function predictGrowthStage(file, signal) {
  const form = new FormData()
  form.append('file', normalizeImageFile(file))
  const result = await request('/api/growth-stage/predict', { method: 'POST', body: form, signal })
  if (!result || result.status !== 'succeeded' || !Number.isInteger(result.predicted_stage)
    || result.predicted_stage < 1 || result.predicted_stage > 7
    || !Number.isFinite(result.confidence) || result.confidence < 0 || result.confidence > 1
    || !Number.isFinite(result.inference_time_seconds) || !result.probabilities
    || Object.values(result.probabilities).some(value => !Number.isFinite(Number(value)))) {
    throw new Error('生育期服务返回结果不完整，当前不展示分类结果。')
  }
  return result
}
