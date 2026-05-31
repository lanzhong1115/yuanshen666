<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useStandaloneStore } from '../stores/standalone'
import * as echarts from 'echarts'
import AppIcon from '../components/AppIcon.vue'

const store = useStandaloneStore()
const allocationChart = ref(null)
let chartInst = null

// 直接从 store 读取缓存数据（0延迟）
const diagnosis = computed(() => store.diagnosis?.diagnosis || [])
const allocation = computed(() => store.allocation)
const signals = computed(() => store.signals?.signals || [])
const risk = computed(() => store.risk)

// 初始化: 首次加载用 store 缓存
onMounted(async () => {
  if (!store.lastSync) await store.sync()
  await nextTick()
  if (store.hasHoldings) initChart()
})

// 持仓变更后自动更新图表
watch(() => store.version, async () => {
  await nextTick()
  initChart()
})

function initChart() {
  if (!allocationChart.value || !allocation.value) return
  if (chartInst) chartInst.dispose()
  const chart = echarts.init(allocationChart.value)
  chartInst = chart

  const cur = allocation.value.current || {}
  const rec = allocation.value.recommended || {}

  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    legend: { bottom: 4, textStyle: { fontSize: 11 } },
    series: [
      {
        name: '当前', type: 'pie',
        radius: ['42%', '62%'], center: ['27%', '48%'],
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12 } },
        data: [
          { value: cur.stock || 0, name: '股票型', itemStyle: { color: '#E53935' } },
          { value: cur.mixed || 0, name: '混合型', itemStyle: { color: '#FF9800' } },
          { value: cur.bond || 0, name: '债券型', itemStyle: { color: '#4CAF50' } },
          { value: cur.money || 0, name: '货币型', itemStyle: { color: '#1A73E8' } },
          { value: cur.other || 0, name: '其他', itemStyle: { color: '#ccc' } },
        ].filter(d => d.value > 0),
      },
      {
        name: '建议', type: 'pie',
        radius: ['42%', '62%'], center: ['73%', '48%'],
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12 } },
        data: [
          { value: rec.stock || 0, name: '股票型', itemStyle: { color: '#E53935' } },
          { value: rec.mixed || 0, name: '混合型', itemStyle: { color: '#FF9800' } },
          { value: rec.bond || 0, name: '债券型', itemStyle: { color: '#4CAF50' } },
          { value: rec.money || 0, name: '货币型', itemStyle: { color: '#1A73E8' } },
        ],
      },
    ],
    graphic: [
      { type: 'text', left: '19%', top: '44%', style: { text: '当前', fontSize: 11, fill: '#999', textAlign: 'center' } },
      { type: 'text', left: '65%', top: '44%', style: { text: '建议', fontSize: 11, fill: '#999', textAlign: 'center' } },
    ],
  })
}

// 把指数数据融入建议
const marketContext = computed(() => {
  const idx = store.indices.slice(0, 3)
  if (!idx.length) return ''
  const up = idx.filter(i => i.change_pct > 0).length
  const mood = up >= 2 ? '偏暖' : up >= 1 ? '震荡' : '偏冷'
  return `大盘${mood}（${idx.map(i => i.name + i.change_pct.toFixed(1) + '%').join(' ')}）`
})

const actionMap = { buy: ['建议加仓', 'up'], sell: ['建议减仓', 'down'], hold: ['持有观望', ''] }
const diagBadges = { danger: '严重', warning: '注意', info: '提示' }
const diagColors = { danger: 'up', warning: 'warning', info: '' }
</script>

<template>
  <div class="advice-page">
    <div class="page-header">
      <span class="ph-title">持有建议</span>
      <span class="ph-sub" v-if="marketContext">{{ marketContext }}</span>
    </div>

    <div v-if="!store.hasHoldings" class="empty">
      <AppIcon name="search" :size="36" color="#ccc" />
      <span>暂无持仓，先添加基金获取建议</span>
    </div>

    <template v-if="store.hasHoldings">
      <!-- 风险评估 -->
      <div class="card risk-bar" v-if="risk">
        <span class="risk-tag" :class="'rl-' + risk.risk_level">风险{{ risk.risk_level }}</span>
        <span class="risk-info">建议仓位 {{ risk.suggested_position }}% · 现金 {{ risk.suggested_cash }}%</span>
      </div>

      <!-- 买卖信号 -->
      <div class="card">
        <div class="card-header"><span class="card-title">操作参考</span></div>
        <div class="signal-list">
          <div v-for="s in signals" :key="s.fund_code" class="sig-item" :class="'sig-' + s.action">
            <span class="sig-icon">{{ s.action === 'buy' ? '▲' : s.action === 'sell' ? '▼' : '—' }}</span>
            <div class="sig-body">
              <span class="sig-name">{{ s.fund_name || s.fund_code }}</span>
              <span class="sig-reason">{{ s.reason }}</span>
            </div>
            <span class="sig-badge" :class="'badge-' + actionMap[s.action][1]">{{ actionMap[s.action][0] }}</span>
          </div>
        </div>
      </div>

      <!-- 持仓诊断 -->
      <div class="card" v-if="diagnosis.length">
        <div class="card-header"><span class="card-title">诊断</span></div>
        <div v-for="(d, i) in diagnosis" :key="i" class="diag-row">
          <span class="diag-badge" :class="'db-' + d.level">{{ diagBadges[d.level] }}</span>
          <span>{{ d.message }}</span>
        </div>
      </div>

      <!-- 分仓建议 -->
      <div class="card" v-if="allocation">
        <div class="card-header"><span class="card-title">分仓建议</span></div>
        <div ref="allocationChart" style="height:200px;width:100%"></div>
        <div v-if="allocation.adjustments?.length" style="margin-top:8px">
          <div v-for="(tip, i) in allocation.adjustments" :key="i" class="tip-line">
            <AppIcon name="bulb" :size="13" style="flex-shrink:0;color:#FF9800" /> {{ tip }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.advice-page { padding: 12px 0 20px; }
.page-header { padding: 8px 20px; display: flex; justify-content: space-between; align-items: baseline; }
.ph-title { font-size: 20px; font-weight: 700; }
.ph-sub { font-size: 11px; color: #999; }

.risk-bar {
  display: flex; align-items: center; gap: 10px;
  background: #FFF8E1; border-left: 3px solid #FF9800;
}
.risk-tag { padding: 3px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; color: #fff; }
.rl-低 { background: #4CAF50; } .rl-中 { background: #FF9800; } .rl-高 { background: #E53935; }
.risk-info { font-size: 13px; color: #666; }

.signal-list { display: flex; flex-direction: column; gap: 6px; }
.sig-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; }
.sig-buy { background: rgba(229,57,53,.05); }
.sig-sell { background: rgba(76,175,80,.05); }
.sig-hold { background: var(--bg); }
.sig-icon { font-size: 16px; flex-shrink: 0; }
.sig-buy .sig-icon { color: #E53935; } .sig-sell .sig-icon { color: #4CAF50; }
.sig-body { flex: 1; min-width: 0; }
.sig-name { font-size: 14px; font-weight: 500; display: block; }
.sig-reason { font-size: 12px; color: #999; }
.sig-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 4px; flex-shrink: 0; }
.badge-up { background: rgba(229,57,53,.1); color: #E53935; }
.badge-down { background: rgba(76,175,80,.1); color: #4CAF50; }

.diag-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.diag-row:last-child { border-bottom: none; }
.diag-badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 3px; flex-shrink: 0; }
.db-danger { background: rgba(229,57,53,.08); color: #E53935; }
.db-warning { background: rgba(255,152,0,.08); color: #E65100; }
.db-info { background: #f5f5f5; color: #999; }

.tip-line { display: flex; align-items: center; gap: 6px; padding: 6px 0; font-size: 12px; color: #666; }
.badge-warning { background: rgba(255,152,0,.1); color: #E65100; }
</style>
