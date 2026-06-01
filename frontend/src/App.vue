<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useFundStore } from './stores/fund'
import AppIcon from './components/AppIcon.vue'
const route=useRoute();const store=useFundStore();let t=null
const showNav=computed(()=>!route.path.startsWith('/fund/'))
onMounted(async()=>{store.loadSnapshot();await store.sync();t=setInterval(()=>store.refreshMarket(),30000)})
onUnmounted(()=>{if(t)clearInterval(t)})
</script>
<template>
<div class="app-container" :class="{'no-nav':!showNav}"><router-view v-slot="{Component}"><transition name="fade" mode="out-in"><component :is="Component" :key="$route.path"/></transition></router-view>
<nav class="bottom-nav" v-if="showNav"><router-link to="/" class="nav-item" exact-active-class="active" @click="store.sync()"><AppIcon name="wallet" :size="22"/><span>持有</span></router-link><router-link to="/advice" class="nav-item" active-class="active" @click="store.sync()"><AppIcon name="bulb" :size="22"/><span>持有建议</span></router-link><router-link to="/profile" class="nav-item" active-class="active" @click="store.sync()"><AppIcon name="person" :size="22"/><span>我的</span></router-link></nav></div>
</template>
