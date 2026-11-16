import fieldCloseup from '../assets/wheat-field-brand.png'
import greenWheat from '../assets/wheat-usda-field.jpg'
import ripeWheat from '../assets/wheat-usda-nebraska.jpg'
import atmosphere from '../assets/agriculture-atmosphere.png'
import cropScenes from '../assets/agtech-card-scenes.png'

// 场景仅用于背景装饰，不进入用户图像、模型结果或实验数据。
export const backgroundScenes = {
  home: { image: atmosphere, size: '200% 200%', position: '0% 0%', label: '农田全景', credit: 'AI 生成的品牌场景' },
  'image-recognition': { image: fieldCloseup, label: '麦穗近景', credit: 'AI 生成的品牌场景' },
  'growth-prediction': { image: greenWheat, label: '绿色小麦田', credit: 'USDA / Lance Cheung · 公共领域', source: 'https://commons.wikimedia.org/wiki/File:Wheat_(20200520-NRCS-LSC-0007).jpg' },
  'yield-prediction': { image: ripeWheat, position: '22% center', label: '成熟麦田', credit: 'USDA ARS / Stephen Ausmus', source: 'https://www.ars.usda.gov/oc/images/photos/mar22/k11701-1/' },
  'market-returns': { image: atmosphere, size: '200% 200%', position: '100% 100%', label: '仓储麦粒', credit: 'AI 生成的品牌场景' },
  reports: { image: cropScenes, size: '200% 200%', position: '100% 100%', label: '晨雾田野', credit: 'AI 生成的品牌场景' },
}
export function backgroundStyle(scene) {
  return { '--page-scene-image': `url("${scene.image}")`, '--page-scene-size': scene.size || 'cover', '--page-scene-position': scene.position || 'center' }
}


