<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useFundStore } from '../stores/fund'
import * as echarts from 'echarts'
import AppIcon from '../components/AppIcon.vue'

const store = useFundStore()
const dailyChart = ref(null)
const monthlyChart = ref(null)
const pieChart = ref(null)
const rankTab = ref('profit')
let chartInsts = {}

// 从 store 缓存读取
const dailyProfit = computed(() => store.dailyProfit)
const monthlyProfit = computed(() => store.monthlyProfit)
const profitRank = computed(() => store.ranking?.profit || [])
const lossRank = computed(() => store.ranking?.loss || [])
const currentRank = computed(() => rankTab.value === 'profit' ? profitRank.value : lossRank.value)

onMounted(async () => {
  if (!store.lastSync) await store.sync()
  await nextTick()
  initAllCharts()
})

watch(() => store.version, async () => {
  await nextTick()
  initAllCharts()
})

function initAllCharts() {
  initDailyChart()
  initMonthlyChart()
  initPieChart()
}

function initDailyChart() {
  if (!dailyChart.value) return
  if (chartInsts.daily) chartInsts.daily.dispose()
  const chart = echarts.init(dailyChart.value)
  chartInsts.daily = chart

  const data = store.dailyProfit
  if (!data.length) return

  chart.setOption({
    grid: { top: 8, right: 10, bottom: 22, left: 42 },
    xAxis: { type: 'category', data: data.map(d => d.date.slice(5)), axisLabel: { fontSize: 9, color: '#999', interval: 4 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 9, color: '#999' }, splitLine: { lineStyle: { color: '#f5f5f5' } } },
    series: [{
      data: data.map(d => ({ value: d.profit, itemStyle: { color: d.profit >= 0 ? '#E53935' : '#4CAF50' } })),
      type: 'bar', barWidth: '55%',
    }],
  })
}

function initMonthlyChart() {
  if (!monthlyChart.value) return
  if (chartInsts.monthly) chartInsts.monthly.dispose()
  const chart = echarts.init(monthlyChart.value)
  chartInsts.monthly = chart

  const data = store.monthlyProfit
  if (!data.length) return

  chart.setOption({
    grid: { top: 8, right: 10, bottom: 22, left: 42 },
    xAxis: { type: 'category', data: data.map(d => d.month.slice(5) || d.month), axisLabel: { fontSize: 9, color: '#999' } },
    yAxis: { type: 'value', axisLabel: { fontSize: 9, color: '#999', formatter: v => v + '%' }, splitLine: { lineStyle: { color: '#f5f5f5' } } },
    series: [{
      data: data.map(d => d.profit_pct),
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 3,
      lineStyle: { color: '#1A73E8', width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(26,115,232,.1)' }, { offset: 1, color: 'rgba(26,115,232,0)' }]) },
    }],
  })
}

function initPieChart() {
  if (!pieChart.value || !store.holdings.length) return
  if (chartInsts.pie) chartInsts.pie.dispose()
  const chart = echarts.init(pieChart.value)
  chartInsts.pie = chart

  const colors = ['#E53935', '#FF9800', '#4CAF50', '#1A73E8', '#9C27B0', '#00BCD4', '#FF5722', '#607D8B']
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '50%'],
      label: { formatter: '{b}\n{d}%', fontSize: 10 },
      data: store.holdings.map((h, i) => ({
        name: h.fund_name || h.fund_code,
        value: h.current_value || h.buy_amount || 0,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }],
  })
}
</script>

<template>
  <div class="profile-page">
    <!-- 资金总览 -->
    <div class="card">
      <div class="overview">
        <div class="ov-item">
          <span class="ov-label">总投入</span>
          <span class="ov-value">{{ (store.summary?.total_cost || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
        </div>
        <div class="ov-item">
          <span class="ov-label">当前市值</span>
          <span class="ov-value">{{ (store.summary?.total_value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
        </div>
        <div class="ov-item">
          <span class="ov-label">总收益</span>
          <span class="ov-value" :class="store.totalProfit >= 0 ? 'up' : 'down'">
            {{ store.totalProfit >= 0 ? '+' : '' }}{{ store.totalProfit.toFixed(2) }}
          </span>
          <span class="tag" :class="store.totalProfitPct >= 0 ? 'tag-up' : 'tag-down'" style="margin-top:2px">
            {{ store.totalProfitPct >= 0 ? '+' : '' }}{{ store.totalProfitPct.toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 日收益 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">每日收益</span>
        <span class="card-subtitle">近30日</span>
      </div>
      <div ref="dailyChart" style="height:180px;width:100%"></div>
    </div>

    <!-- 月收益率 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">月度收益率</span>
      </div>
      <div ref="monthlyChart" style="height:180px;width:100%"></div>
    </div>

    <!-- 持仓分布 -->
    <div class="card" v-if="store.hasHoldings">
      <div class="card-header"><span class="card-title">持仓分布</span></div>
      <div ref="pieChart" style="height:220px;width:100%"></div>
    </div>

    <!-- 盈亏排行 -->
    <div class="card" v-if="profitRank.length || lossRank.length">
      <div class="card-header">
        <span class="card-title">收益排行</span>
        <div class="tab-row">
          <button class="tab-btn" :class="{ on: rankTab === 'profit' }" @click="rankTab = 'profit'">盈利 {{ profitRank.length }}</button>
          <button class="tab-btn" :class="{ on: rankTab === 'loss' }" @click="rankTab = 'loss'">亏损 {{ lossRank.length }}</button>
        </div>
      </div>
      <div v-if="!currentRank.length" style="text-align:center;padding:16px;color:#999;font-size:13px">暂无</div>
      <div v-for="(item, i) in currentRank" :key="item.fund_code" class="rank-row">
        <span class="rk-num">{{ i + 1 }}</span>
        <div class="rk-info">
          <span class="rk-name">{{ item.fund_name || item.fund_code }}</span>
          <span class="rk-code">{{ item.fund_code }}</span>
        </div>
        <div class="rk-pnl">
          <span :class="item.profit >= 0 ? 'up' : 'down'" style="font-size:14px;font-weight:600">{{ item.profit >= 0 ? '+' : '' }}{{ item.profit.toFixed(2) }}</span>
          <span class="tag" :class="item.profit_pct >= 0 ? 'tag-up' : 'tag-down'" style="margin-top:1px">{{ item.profit_pct >= 0 ? '+' : '' }}{{ item.profit_pct.toFixed(2) }}%</span>
        </div>
      </div>
    </div>

    <div v-if="!store.hasHoldings" class="empty">
      <AppIcon name="chart" :size="36" color="#ccc" />
      <span>添加持仓后查看收益分析</span>
    </div>
  </div>
</template>

<style scoped>
.profile-page { padding: 12px 0 20px; }
.overview { display: flex; justify-content: space-around; gap: 8px; }
.ov-item { display: flex; flex-direction: column; align-items: center; }
.ov-label { font-size: 11px; color: #999; margin-bottom: 2px; }
.ov-value { font-size: 16px; font-weight: 700; }

.tab-row { display: flex; gap: 4px; }
.tab-btn { padding: 4px 12px; border: 1px solid #eee; border-radius: 12px; background: #f9f9f9; font-size: 12px; cursor: pointer; color: #666; }
.tab-btn.on { background: var(--accent); color: #fff; border-color: var(--accent); }

.rank-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f5f5f5; }
.rank-row:last-child { border-bottom: none; }
.rk-num { width: 20px; height: 20px; border-radius: 50%; background: #f5f5f5; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: #999; flex-shrink: 0; }
.rk-info { flex: 1; min-width: 0; }
.rk-name { font-size: 14px; font-weight: 500; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rk-code { font-size: 11px; color: #999; }
.rk-pnl { text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
</style>
