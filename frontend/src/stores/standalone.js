import { defineStore } from 'pinia'
import * as api from '../api/direct.js'

const STORAGE_KEY = 'fund_holdings_v2'

export const useStandaloneStore = defineStore('standalone', {
  state: () => ({
    holdings: [], dailyProfit: [], monthlyProfit: [], ranking: { profit: [], loss: [] },
    indices: [], sectors: [], diagnosis: [], allocation: null, signals: [], risk: null,
    summary: null, loading: false, lastSync: null, version: 0,
  }),

  getters: {
    totalCost: s => s.holdings.reduce((sum, h) => sum + (h.buy_amount || 0), 0),
    totalValue: s => s.holdings.reduce((sum, h) => sum + (h.current_value || 0), 0),
    totalProfit: s => s.holdings.reduce((sum, h) => sum + (h.profit || 0), 0),
    totalAssets: s => s.totalValue,
    totalProfitPct: s => s.totalCost > 0 ? +(s.totalProfit / s.totalCost * 100).toFixed(2) : 0,
    hasHoldings: s => s.holdings.length > 0,
  },

  actions: {
    loadFromStorage() {
      try { const d = JSON.parse(localStorage.getItem(STORAGE_KEY)); if (d?.holdings) this.holdings = d.holdings } catch {}
    },

    _save() {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ holdings: this.holdings })) } catch {}
    },

    async sync() {
      this.loading = true
      try {
        let indices=[],sectors=[];try{indices=await api.fetchIndices()}catch{};try{sectors=await api.fetchSectors()}catch{}
        this.indices = indices; this.sectors = (sectors || []).slice(0, 8)

        const codes = [...new Set(this.holdings.map(h => h.fund_code))]
        const navMap = {}
        await Promise.all(codes.map(async c => { try { navMap[c] = await api.fetchFundNAV(c, 90) } catch {} }))

        let totalCost = 0, totalValue = 0
        const dailyVals = {}
        for (const h of this.holdings) {
          const nav = navMap[h.fund_code] || []
          h.current_nav = nav.length ? nav[nav.length - 1].nav : 0
          h.daily_return = nav.length ? nav[nav.length - 1].daily_return : 0
          h.nav_date = nav.length ? nav[nav.length - 1].date : ''
          const shares = h.buy_shares > 0 ? h.buy_shares : h.buy_nav > 0 ? h.buy_amount / h.buy_nav : h.current_nav > 0 ? h.buy_amount / h.current_nav : 0
          h.current_value = +(shares * h.current_nav).toFixed(2) || h.buy_amount
          h.profit = +(h.current_value - h.buy_amount).toFixed(2)
          h.profit_pct = h.buy_amount > 0 ? +((h.profit / h.buy_amount) * 100).toFixed(2) : 0
          totalCost += h.buy_amount; totalValue += h.current_value
          nav.forEach(n => { dailyVals[n.date] = (dailyVals[n.date] || 0) + shares * n.nav })
        }

        const sorted = Object.entries(dailyVals).sort((a, b) => a[0] > b[0] ? 1 : -1).slice(-30)
        this.dailyProfit = sorted.map(([date, val]) => ({ date, total_value: +val.toFixed(2), total_cost: totalCost, profit: +(val - totalCost).toFixed(2), profit_pct: totalCost > 0 ? +((val - totalCost) / totalCost * 100).toFixed(2) : 0 }))

        const monthly = {}
        this.dailyProfit.forEach(d => { const m = d.date.slice(0, 7); if (!monthly[m]) monthly[m] = { month: m, start: d.total_value, end: d.total_value }; monthly[m].end = d.total_value })
        this.monthlyProfit = Object.values(monthly).slice(-12).map(m => ({ month: m.month, start_value: m.start, end_value: m.end, profit: +(m.end - m.start).toFixed(2), profit_pct: m.start > 0 ? +((m.end - m.start) / m.start * 100).toFixed(2) : 0 }))

        const sorted2 = [...this.holdings].sort((a, b) => b.profit_pct - a.profit_pct)
        this.ranking = { profit: sorted2.filter(h => h.profit > 0), loss: sorted2.filter(h => h.profit < 0) }
        this.summary = { total_cost: totalCost, total_value: totalValue, total_profit: this.totalProfit, total_profit_pct: this.totalProfitPct, fund_count: this.holdings.length, details: this.holdings }
        this.lastSync = Date.now(); this.version++
      } catch (e) { console.error('sync:', e) }
      this.loading = false
    },

    async refreshMarket() {
      try { const [i, s] = await Promise.all([api.fetchIndices(), api.fetchSectors()]); if (i.length) this.indices = i; if (s.length) this.sectors = s.slice(0, 8) } catch {}
    },

    async addHolding(data) {
      this.holdings.unshift({ ...data, id: Date.now() }); this._save(); await this.sync()
    },
    async removeHolding(id) {
      this.holdings = this.holdings.filter(h => h.id !== id); this._save(); await this.sync()
    },
  },
})
