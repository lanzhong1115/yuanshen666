/**
 * 养基助手 - 中央数据仓库
 * 单次 sync() 获取所有数据，页面切换 <0.1s
 */
import { defineStore } from 'pinia'
import { api } from '../api'

export const useFundStore = defineStore('fund', {
  state: () => ({
    summary: null,
    holdings: [],
    dailyProfit: [],
    monthlyProfit: [],
    ranking: null,
    indices: [],
    sectors: [],
    diagnosis: null,
    allocation: null,
    signals: null,
    risk: null,
    loading: false,
    lastSync: null,
    version: 0,
    fundCache: {},  // 基金详情预缓存 {code: {nav, holds, returns}}
  }),

  getters: {
    totalAssets: s => s.summary?.total_value || 0,
    totalProfit: s => s.summary?.total_profit || 0,
    totalProfitPct: s => s.summary?.total_profit_pct || 0,
    hasHoldings: s => s.holdings.length > 0,
  },

  actions: {
    async sync() {
      this.loading = true
      try {
        const data = await api.syncAll()
        this._applyData(data)
        // 存本地快照，冷启动秒开
        try { localStorage.setItem('fund_snapshot', JSON.stringify(data)) } catch {}
      } catch (e) { console.error('sync:', e) }
      this.loading = false
    },

    /** 冷启动：先加载本地快照，再异步刷新 */
    loadSnapshot() {
      try {
        const raw = localStorage.getItem('fund_snapshot')
        if (raw) this._applyData(JSON.parse(raw))
      } catch {}
    },

    _applyData(data) {
      this.summary = data.summary
      this.holdings = data.summary?.details || []
      this.dailyProfit = data.daily_profit || []
      this.monthlyProfit = data.monthly_profit || []
      this.ranking = data.ranking
      this.indices = data.indices || []
      this.sectors = data.sectors || []
      this.diagnosis = data.diagnosis
      this.allocation = data.allocation
      this.signals = data.signals
      this.risk = data.risk
      this.lastSync = Date.now()
      this.version++
    },

    async refreshMarket() {
      try {
        const [indices, sectors] = await Promise.all([api.getIndices(), api.getSectors()])
        this.indices = indices.indices || []
        this.sectors = sectors.sectors || []
      } catch {}
    },

    async addHolding(data) { await api.addHolding(data); await this.sync() },
    async removeHolding(id) { await api.deleteHolding(id); await this.sync() },

    /** 预加载所有持仓基金的详情（后台静默） */
    async preloadDetails() {
      const codes = [...new Set(this.holdings.map(h => h.fund_code))]
      for (const code of codes) {
        if (!this.fundCache[code]) {
          api.getFundDetail(code, false).then(d => { this.fundCache[code] = d }).catch(() => {})
        }
      }
    },

    /** 获取单个基金详情（缓存优先） */
    getFundCache(code) { return this.fundCache[code] || null },
  },
})
