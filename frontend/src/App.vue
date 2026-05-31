<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useStandaloneStore } from './stores/standalone'
import AppIcon from './components/AppIcon.vue'
const route=useRoute();const store=useStandaloneStore();let t=null
const showNav=computed(()=>!route.path.startsWith('/fund/'))
onMounted(async()=>{store.loadFromStorage();await store.sync();t=setInterval(()=>store.refreshMarket(),30000)})
onUnmounted(()=>{if(t)clearInterval(t)})
</script>
<template>
<div class="app-container" :class="{'no-nav':!showNav}">
<router-view v-slot="{Component}"><transition name="fade" mode="out-in"><component :is="Component" :key="$route.path"/></transition></router-view>
<nav class="bottom-nav" v-if="showNav">
<router-link to="/" class="nav-item" exact-active-class="active" @click="store.sync()"><AppIcon name="wallet" :size="22"/><span class="nav-label">持有</span></router-link>
<router-link to="/advice" class="nav-item" active-class="active" @click="store.sync()"><AppIcon name="bulb" :size="22"/><span class="nav-label">持有建议</span></router-link>
<router-link to="/profile" class="nav-item" active-class="active" @click="store.sync()"><AppIcon name="person" :size="22"/><span class="nav-label">我的</span></router-link>
</nav>
</div>
</template>
<style scoped>
.app-container{max-width:480px;margin:0 auto;min-height:100vh;padding-bottom:70px;background:var(--bg)}
.app-container.no-nav{padding-bottom:0}
.fade-enter-active,.fade-leave-active{transition:opacity .1s ease}
.fade-enter-from,.fade-leave-to{opacity:0}
.bottom-nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;display:flex;justify-content:space-around;align-items:center;background:rgba(255,255,255,.95);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-top:1px solid var(--border);padding:6px 0 env(safe-area-inset-bottom,6px);z-index:100}
.nav-item{display:flex;flex-direction:column;align-items:center;gap:2px;text-decoration:none;color:#999;font-size:11px;padding:4px 18px;border-radius:8px;transition:color .15s}
.nav-item.active{color:var(--accent)}.nav-label{font-weight:500}
</style>
