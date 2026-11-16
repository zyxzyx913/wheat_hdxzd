import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 相对资源地址配合哈希路由，便于后续部署到子目录。
const backendProxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
  '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
}
export default defineConfig({
  plugins: [vue()],
  base: './',
  // Codex Windows 运行时对工作区文件执行 realpath 可能返回 EPERM；
  // 保留符号链接路径即可避免构建阶段解析失败，不改变运行时资源路径。
  resolve: { preserveSymlinks: true },
  // 图片地址与 API 一起代理，避免结果图片错误请求到前端端口。
  server: { proxy: backendProxy },
  preview: { proxy: backendProxy },
})
