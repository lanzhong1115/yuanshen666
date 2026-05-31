// 始终用电脑后端（开发时 Vite proxy，APK 环境直连）
const BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // 持仓
  getHoldings: () => request('/holdings/'),
  addHolding: (data) => request('/holdings/', { method: 'POST', body: JSON.stringify(data) }),
  updateHolding: (id, data) => request(`/holdings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteHolding: (id) => request(`/holdings/${id}`, { method: 'DELETE' }),
  getSummary: (realtime = false) => request(`/holdings/summary?realtime=${realtime}`),
  getFundEstimate: (code) => request(`/funds/${code}/estimate`),
  getFundDetail: (code, withEstimate = false, days = 365) => request(`/funds/${code}/detail?include_estimate=${withEstimate}&days=${days}`),
  getEstimateAll: () => request('/funds/estimate-all'),
  syncAll: () => request('/sync/all'),
  addTrade: (id, data) => request(`/holdings/${id}/trade`, { method: 'POST', body: JSON.stringify(data) }),
  getTrades: (id) => request(`/holdings/${id}/trades`),

  // 基金数据
  searchFunds: (q) => request(`/funds/search?query=${encodeURIComponent(q)}`),
  getFundInfo: (code) => request(`/funds/${code}/info`),
  getFundNav: (code, days = 90) => request(`/funds/${code}/nav?days=${days}`),
  getFundLatest: (code) => request(`/funds/${code}/latest`),
  getFundHoldings: (code) => request(`/funds/${code}/holdings`),
  getFundSectors: (code) => request(`/funds/${code}/sectors`),

  // 市场行情
  getIndices: () => request('/market/indices'),
  getSectors: () => request('/market/sectors'),
  getSectorFlow: () => request('/market/sectors/flow'),

  // 分析建议
  getDiagnosis: () => request('/analysis/portfolio/diagnosis'),
  getAllocation: () => request('/analysis/portfolio/allocation'),
  getSignals: () => request('/analysis/portfolio/signals'),
  getRisk: () => request('/analysis/portfolio/risk'),
  getDailyProfit: (days = 30) => request(`/analysis/profit/daily?days=${days}`),
  getMonthlyProfit: (months = 12) => request(`/analysis/profit/monthly?months=${months}`),
  getProfitRanking: () => request('/analysis/profit/ranking'),
}
