import { createRouter, createWebHistory } from 'vue-router'

// 懒加载所有页面 — 按需加载减少初始包体积，消除切换卡顿
const Holdings = () => import('../views/Holdings.vue')
const Advice = () => import('../views/Advice.vue')
const Profile = () => import('../views/Profile.vue')
const FundDetail = () => import('../views/FundDetail.vue')

const routes = [
  { path: '/', name: 'Holdings', component: Holdings, meta: { title: '持有' } },
  { path: '/advice', name: 'Advice', component: Advice, meta: { title: '持有建议' } },
  { path: '/profile', name: 'Profile', component: Profile, meta: { title: '我的' } },
  { path: '/fund/:code', name: 'FundDetail', component: FundDetail, meta: { title: '基金详情' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
