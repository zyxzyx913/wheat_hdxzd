import { createRouter, createWebHashHistory } from 'vue-router'
import { allModules } from '../config/modules.js'

// 用明确的路径映射保留全部旧地址，避免导航调整造成页面错配。
const pages = {
  '/': () => import('../views/Home.vue'),
  '/image-recognition': () => import('../views/ImageRecognition.vue'),
  '/growth-analysis': () => import('../views/GrowthAnalysis.vue'),
  '/growth-prediction': () => import('../views/GrowthPrediction.vue'),
  '/yield-prediction': () => import('../views/YieldPrediction.vue'),
  '/market-returns': () => import('../views/MarketReturns.vue'),
  '/reports': () => import('../views/Reports.vue'),
  '/phenotype-analysis': () => import('../views/PhenotypeAnalysis.vue'),
  '/research-center': () => import('../views/ResearchCenter.vue'),
  '/research-annotation': () => import('../views/ResearchAnnotation.vue'),
  '/prediction': () => import('../views/Prediction.vue'),
}
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    ...allModules.map((item) => ({ path: item.path, component: pages[item.path], meta: { title: item.title } })),
    { path: '/research-annotation', component: pages['/research-annotation'], meta: { title: '科研标注管理' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach((to) => {
  document.title = `${to.meta.title} · 麦视通 — 小麦智能分析与预测平台`
})
export default router

