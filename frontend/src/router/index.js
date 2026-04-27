import { createRouter, createWebHashHistory } from 'vue-router';

const DesktopView  = () => import('@/views/DesktopView.vue');
const MobileView   = () => import('@/views/MobileView.vue');
const BallView     = () => import('@/views/BallView.vue');
const EmbedView    = () => import('@/views/EmbedView.vue');
const SettingsView = () => import('@/views/SettingsView.vue');

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/',         component: DesktopView,  meta: { name: '电脑版' } },
    { path: '/desktop',  redirect: '/' },
    { path: '/mobile',   component: MobileView,   meta: { name: '手机版' } },
    { path: '/ball',     component: BallView,     meta: { name: '精灵球', transparent: true } },
    { path: '/embed',    component: EmbedView,    meta: { name: '嵌入版' } },
    { path: '/settings', component: SettingsView, meta: { name: '设置' } },
    { path: '/:any(.*)*', redirect: '/' },
  ],
});
