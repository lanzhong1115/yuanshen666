// 自动判断环境：本地开发 → localhost，线上/APK → 云服务器
const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
const BASE = isLocal ? 'http://localhost:8765/api' : 'http://139.155.150.75:8765/api'
async function request(url, options = {}) {
  const res = await fetch(BASE + url, { headers: { 'Content-Type': 'application/json', ...options.headers }, ...options })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: '请求失败' })); throw new Error(err.detail || 'HTTP ' + res.status) }
  return res.json()
}
export const api = {
  getHoldings: () => request('/holdings/'), addHolding: (data) => request('/holdings/', { method: 'POST', body: JSON.stringify(data) }),
  deleteHolding: (id) => request('/holdings/' + id, { method: 'DELETE' }), getSummary: () => request('/holdings/summary'),
  addTrade: (id, data) => request('/holdings/' + id + '/trade', { method: 'POST', body: JSON.stringify(data) }),
  getHoldingProfitHistory: (id, days = 30) => request('/holdings/' + id + '/profit-history?days=' + days),
  searchFunds: (q) => request('/funds/search?query=' + encodeURIComponent(q)),
  getFundNav: (code, days = 90) => request('/funds/' + code + '/nav?days=' + days),
  getFundEstimate: (code) => request('/funds/' + code + '/estimate'),
  getFundDetail: (code, e = false, d = 365) => request('/funds/' + code + '/detail?include_estimate=' + e + '&days=' + d),
  getFundValuation: (code) => request('/funds/' + code + '/valuation'),
  getBatchValuations: (codes) => request('/funds/valuations', { method: 'POST', body: JSON.stringify(codes) }),
  getIndices: () => request('/market/indices'), getSectors: () => request('/market/sectors'),
  syncAll: () => request('/sync/all'),
  getDiagnosis: () => request('/analysis/portfolio/diagnosis'), getAllocation: () => request('/analysis/portfolio/allocation'),
  getSignals: () => request('/analysis/portfolio/signals'), getRisk: () => request('/analysis/portfolio/risk'),
  getDailyProfit: (d = 30) => request('/analysis/profit/daily?days=' + d),
  getMonthlyProfit: (m = 12) => request('/analysis/profit/monthly?months=' + m),
  getProfitRanking: () => request('/analysis/profit/ranking'),
}
