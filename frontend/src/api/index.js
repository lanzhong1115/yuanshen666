const BASE = 'http://139.155.150.75:8765/api'

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, { headers: { 'Content-Type': 'application/json', ...options.headers }, ...options })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: '请求失败' })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export const api = {
  getHoldings: () => request('/holdings/'),
  addHolding: (data) => request('/holdings/', { method: 'POST', body: JSON.stringify(data) }),
  deleteHolding: (id) => request(`/holdings/${id}`, { method: 'DELETE' }),
  getSummary: () => request('/holdings/summary'),
  addTrade: (id, data) => request(`/holdings/${id}/trade`, { method: 'POST', body: JSON.stringify(data) }),
  getTrades: (id) => request(`/holdings/${id}/trades`),
  searchFunds: (q) => request(`/funds/search?query=${encodeURIComponent(q)}`),
  getFundNav: (code, days = 90) => request(`/funds/${code}/nav?days=${days}`),
  getFundEstimate: (code) => request(`/funds/${code}/estimate`),
  getFundDetail: (code, withEstimate = false, days = 365) => request(`/funds/${code}/detail?include_estimate=${withEstimate}&days=${days}`),
  getIndices: () => request('/market/indices'),
  getSectors: () => request('/market/sectors'),
  syncAll: () => request('/sync/all'),
  getDiagnosis: () => request('/analysis/portfolio/diagnosis'),
  getAllocation: () => request('/analysis/portfolio/allocation'),
  getSignals: () => request('/analysis/portfolio/signals'),
  getRisk: () => request('/analysis/portfolio/risk'),
  getDailyProfit: (days = 30) => request(`/analysis/profit/daily?days=${days}`),
  getMonthlyProfit: (months = 12) => request(`/analysis/profit/monthly?months=${months}`),
  getProfitRanking: () => request('/analysis/profit/ranking'),
}
