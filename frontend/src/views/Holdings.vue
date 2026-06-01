<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useFundStore } from '../stores/fund'
import * as echarts from 'echarts'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const store = useFundStore()
const router = useRouter()
const showAdd = ref(false)
const menuOpen = ref(null)
const trendChart = ref(null)
let trendC = null

const holdings = computed(() => store.holdings)
const indices = computed(() => store.indices.slice(0, 4))
const sectors = computed(() => store.sectors)
const hasData = computed(() => store.hasHoldings)

const addForm = ref({ fund_code:'',fund_name:'',fund_type:'',buy_amount:'',buy_shares:'',buy_nav:'',buy_date:'',platform:'手动录入' })
const searchResults = ref([])
const searching = ref(false)

// Init
onMounted(async () => {
  if (!store.lastSync) await store.sync()
  initTrendChart()
})
watch(() => store.version, () => initTrendChart())

// 顶部收益图
function initTrendChart() {
  if (!trendChart.value) return
  if (trendC) trendC.dispose()
  const c = echarts.init(trendChart.value); trendC = c
  const h = store.holdings
  if (!h.length) { c.setOption({ title:{text:'暂无数据',left:'center',top:'center',textStyle:{fontSize:13,color:'#999'}} }); return }
  const funds = h.map(x => ({ name:(x.fund_name||x.fund_code).slice(0,8), profit:x.profit||0 })).sort((a,b)=>b.profit-a.profit)
  const tp = funds.reduce((s,f)=>s+f.profit,0)
  const today = store.dailyProfit.slice(-1)[0]
  c.setOption({
    title:{ text:(today?.date||'')+' 日收益', subtext:`${tp>=0?'+':''}${tp.toFixed(2)}元`, left:'center',top:4, textStyle:{fontSize:13,fontWeight:600}, subtextStyle:{fontSize:20,fontWeight:700,color:tp>=0?'#E53935':'#4CAF50'} },
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
    grid:{top:60,right:16,bottom:24,left:70},
    xAxis:{type:'value',axisLabel:{fontSize:9,color:'#999',formatter:v=>v>0?'+'+v:v},splitLine:{lineStyle:{color:'#f0f0f0'}}},
    yAxis:{type:'category',data:funds.map(f=>f.name).reverse(),axisLabel:{fontSize:10},axisLine:{show:false},axisTick:{show:false}},
    series:[{data:funds.map(f=>({value:f.profit,itemStyle:{color:f.profit>=0?'#E53935':'#4CAF50'}})).reverse(),type:'bar',barWidth:'50%',label:{show:true,position:'right',fontSize:9,formatter:p=>`${p.value>=0?'+':''}${p.value.toFixed(0)}`},markLine:{silent:true,symbol:'none',lineStyle:{color:'#ddd',type:'dashed'},data:[{xAxis:0}]}}],
  }); c.resize()
}

// ===== 持仓操作 =====
function removeHolding(id) { if (confirm('确认删除？')) store.removeHolding(id) }
function goFundDetail(code) { router.push(`/fund/${code}`) }

// ===== 搜索 =====
let st = null
function onSearchInput() {
  clearTimeout(st)
  if (addForm.value.fund_code.trim().length < 2) { searchResults.value = []; return }
  searching.value = true
  st = setTimeout(async () => {
    try { const r = await api.searchFunds(addForm.value.fund_code); searchResults.value = r.results || [] } catch { searchResults.value = [] }
    searching.value = false
  }, 300)
}
function selectFund(f) { addForm.value.fund_code = f.fund_code; addForm.value.fund_name = f.fund_name; addForm.value.fund_type = f.fund_type; searchResults.value = [] }
async function submitAdd() {
  if (!addForm.value.fund_code || !addForm.value.buy_amount) return
  await store.addHolding({ fund_code:addForm.value.fund_code, fund_name:addForm.value.fund_name||addForm.value.fund_code, fund_type:addForm.value.fund_type, buy_amount:parseFloat(addForm.value.buy_amount), buy_shares:parseFloat(addForm.value.buy_shares)||0, buy_nav:parseFloat(addForm.value.buy_nav)||0, buy_date:addForm.value.buy_date||'', platform:addForm.value.platform })
  showAdd.value = false
  addForm.value = { fund_code:'',fund_name:'',fund_type:'',buy_amount:'',buy_shares:'',buy_nav:'',buy_date:'',platform:'手动录入' }
}

// ===== 加仓/减仓/定投 =====
const showTrade = ref(false)
const tradeForm = ref({ holding_id:0,fund_code:'',fund_name:'',type:'buy',amount:'',shares:'',nav:'',date:'',notes:'' })
function openTrade(h,type) { tradeForm.value = { holding_id:h.id,fund_code:h.fund_code,fund_name:h.fund_name||h.fund_code,type,amount:'',shares:'',nav:h.current_nav?.toFixed(4)||'',date:new Date().toISOString().slice(0,10),notes:'' }; showTrade.value = true }
async function submitTrade() { const f = tradeForm.value; await api.addTrade(f.holding_id,{ type:f.type,amount:parseFloat(f.amount)||0,shares:parseFloat(f.shares)||0,nav:parseFloat(f.nav)||0,date:f.date,notes:f.notes }); showTrade.value = false; await store.sync() }
</script>

<template>
  <div class="holdings-page">
    <!-- 资产卡片 -->
    <div class="asset-hero">
      <div class="asset-label">总资产 (元)</div>
      <div class="asset-value">{{ store.totalAssets.toLocaleString('zh-CN',{minimumFractionDigits:2}) }}</div>
      <div class="asset-pnl">
        <div class="pnl-item"><span class="pnl-sub">持仓盈亏</span><span :class="store.totalProfit>=0?'up':'down'" style="font-weight:700;font-size:15px">{{ store.totalProfit>=0?'+':'' }}{{ store.totalProfit.toFixed(2) }}</span></div>
        <div class="pnl-divider"></div>
        <div class="pnl-item"><span class="pnl-sub">收益率</span><span :class="store.totalProfitPct>=0?'up':'down'" style="font-weight:700;font-size:15px">{{ store.totalProfitPct>=0?'+':'' }}{{ store.totalProfitPct.toFixed(2) }}%</span></div>
      </div>
    </div>
    <!-- 指数 -->
    <div class="index-strip" v-if="indices.length">
      <div class="index-chip" v-for="i in indices" :key="i.code"><span class="ic-name">{{ i.name }}</span><span class="ic-price">{{ i.price.toFixed(0) }}</span><span :class="i.change_pct>=0?'up':'down'" class="ic-chg">{{ i.change_pct>=0?'+':'' }}{{ i.change_pct.toFixed(2) }}%</span></div>
    </div>
    <!-- 收益图 -->
    <div class="card"><div class="card-header"><span class="card-title">当日收益</span></div><div ref="trendChart" style="height:180px;width:100%"></div></div>
    <!-- 持仓 -->
    <div class="card">
      <div class="card-header"><span class="card-title">持仓</span><button class="btn btn-primary btn-sm" @click="showAdd=true"><AppIcon name="plus" :size="14" style="color:#fff"/> 添加</button></div>
      <div v-if="!hasData" class="empty"><AppIcon name="chart" :size="40" color="#ccc"/><span>暂无持仓</span></div>
      <div v-for="h in holdings" :key="h.id">
        <div class="holding-row">
          <div class="h-left">
            <div class="h-name">{{ h.fund_name||h.fund_code }}</div>
            <div class="h-code">{{ h.fund_code }}</div>
          </div>
          <div class="h-right">
            <div class="h-val">{{ (h.current_value||0).toLocaleString('zh-CN',{minimumFractionDigits:2}) }}</div>
            <div class="h-daily" :class="(h.daily_return||0)>=0?'up':'down'">{{ h.nav_date?h.nav_date.slice(5):'' }} {{ (h.daily_return||0)>=0?'+':'' }}{{ (h.daily_return||0).toFixed(2) }}%</div>
          </div>
          <div class="h-menu-wrap">
            <button class="h-menu-btn" @click.stop="menuOpen=menuOpen===h.id?null:h.id">···</button>
            <div class="h-menu-drop" v-if="menuOpen===h.id" @click.stop>
              <div class="h-menu-item" @click="menuOpen=null;openTrade(h,'buy')">+ 加仓</div>
              <div class="h-menu-item" @click="menuOpen=null;openTrade(h,'sell')">− 减仓</div>
              <div class="h-menu-item" @click="menuOpen=null;openTrade(h,'auto')">↻ 定投</div>
              <div class="h-menu-item danger" @click="menuOpen=null;removeHolding(h.id)">删除</div>
            </div>
          </div>
          <button class="h-arrow" @click.stop="goFundDetail(h.fund_code)"><AppIcon name="chevron-right" :size="16" color="#bbb"/></button>
        </div>
      </div>
    </div>
    <!-- 板块 -->
    <div class="card" v-if="sectors.length"><div class="card-header"><span class="card-title">板块行情</span></div><div class="sector-grid"><div class="sector-chip" v-for="s in sectors.slice(0,8)" :key="s.code"><span>{{ s.name }}</span><span :class="s.change_pct>=0?'up':'down'">{{ s.change_pct>=0?'+':'' }}{{ s.change_pct.toFixed(2) }}%</span></div></div></div>

    <!-- 加仓/减仓/定投弹窗 -->
    <div class="modal-overlay" v-if="showTrade" @click.self="showTrade=false"><div class="modal-content"><h3 style="margin-bottom:12px;font-size:16px">{{ tradeForm.type==='buy'?'加仓':tradeForm.type==='sell'?'减仓':'定投' }} - {{ tradeForm.fund_name }}</h3><input class="input" v-model="tradeForm.amount" type="number" :placeholder="tradeForm.type==='auto'?'每期金额':'金额'"/><input class="input" v-model="tradeForm.shares" type="number" placeholder="份额(选填)"/><input class="input" v-model="tradeForm.nav" type="number" placeholder="净值" step="0.0001"/><input class="input" v-model="tradeForm.date" type="date"/><input v-if="tradeForm.type==='auto'" class="input" v-model="tradeForm.notes" placeholder="定投周期"/><div style="display:flex;gap:10px;margin-top:16px"><button class="btn btn-outline" style="flex:1" @click="showTrade=false">取消</button><button class="btn btn-primary" style="flex:1" @click="submitTrade">确认</button></div></div></div>

    <!-- 添加持仓弹窗 -->
    <div class="modal-overlay" v-if="showAdd" @click.self="showAdd=false"><div class="modal-content"><h3 style="margin-bottom:12px;font-size:16px">添加持仓</h3><input class="input" v-model="addForm.fund_code" placeholder="输入基金代码搜索..." @input="onSearchInput"/><div class="search-dropdown" v-if="searchResults.length"><div class="search-item" v-for="f in searchResults" :key="f.fund_code" @click="selectFund(f)"><span class="s-code">{{ f.fund_code }}</span><span class="s-name">{{ f.fund_name }}</span></div></div><div v-if="addForm.fund_name" style="padding:8px 12px;background:var(--bg);border-radius:6px;margin-top:8px;font-size:13px">{{ addForm.fund_name }}</div><input class="input" v-model="addForm.buy_amount" type="number" placeholder="投入金额 (元)" style="margin-top:10px"/><input class="input" v-model="addForm.buy_shares" type="number" placeholder="持有份额 (选填)"/><input class="input" v-model="addForm.buy_nav" type="number" placeholder="买入净值 (选填)" step="0.0001"/><input class="input" v-model="addForm.buy_date" type="date"/><div style="display:flex;gap:10px;margin-top:16px"><button class="btn btn-outline" style="flex:1" @click="showAdd=false">取消</button><button class="btn btn-primary" style="flex:1" @click="submitAdd">确认</button></div></div></div>
  </div>
</template>

<style scoped>
.holdings-page{padding:12px 0 20px}
.asset-hero{background:linear-gradient(135deg,#E53935,#C62828);margin:0 16px;border-radius:14px;padding:22px 20px;color:#fff;box-shadow:0 4px 16px rgba(229,57,53,.25)}
.asset-label{font-size:12px;opacity:.85;margin-bottom:4px}
.asset-value{font-size:30px;font-weight:700}
.asset-pnl{display:flex;gap:18px;margin-top:12px}
.pnl-sub{font-size:11px;opacity:.75}
.pnl-divider{width:1px;height:30px;background:rgba(255,255,255,.2)}
.index-strip{display:flex;overflow-x:auto;gap:8px;padding:10px 16px;scrollbar-width:none}
.index-chip{display:flex;align-items:center;gap:6px;padding:7px 12px;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);white-space:nowrap;flex-shrink:0;font-size:12px}
.ic-name{color:#666}.ic-price{font-weight:600}.ic-chg{font-weight:500}
.holding-row{display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid #f0f0f0}
.holding-row:last-child{border-bottom:none}
.h-left{flex:1;min-width:0;cursor:pointer}
.h-name{font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.h-code{font-size:11px;color:#999}
.h-right{text-align:right}
.h-val{font-size:15px;font-weight:600}
.h-daily{font-size:13px;font-weight:600;margin-top:2px}
.h-arrow{background:none;border:none;cursor:pointer;padding:4px;flex-shrink:0}
.h-menu-wrap{position:relative;flex-shrink:0}
.h-menu-btn{width:28px;height:28px;border:none;background:transparent;font-size:18px;cursor:pointer;color:#999;border-radius:50%;letter-spacing:1px;line-height:1}
.h-menu-btn:hover{background:#f0f0f0}
.h-menu-drop{position:absolute;right:0;top:100%;background:#fff;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.12);z-index:50;min-width:100px;overflow:hidden;animation:menuIn .15s ease}
.h-menu-item{padding:10px 16px;font-size:13px;cursor:pointer;white-space:nowrap}
.h-menu-item:hover{background:#f5f5f5}
.h-menu-item.danger{color:#E53935}
@keyframes menuIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.holding-expand{animation:expandIn .2s ease;overflow:hidden;background:#fafafa;border-radius:0 0 10px 10px;padding:10px 14px;margin-bottom:2px}
@keyframes expandIn{from{max-height:0;opacity:0}to{max-height:200px;opacity:1}}
.sector-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.sector-chip{display:flex;justify-content:space-between;padding:9px 12px;background:var(--bg);border-radius:8px;font-size:12px}
.search-dropdown{background:var(--bg);border-radius:8px;margin-top:4px;max-height:180px;overflow-y:auto}
.search-item{display:flex;gap:8px;padding:10px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #eee}
.s-code{font-weight:600;color:var(--blue);min-width:56px}
.s-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:10px 20px;border-radius:8px;border:none;font-size:14px;font-weight:500;cursor:pointer}
.btn-primary{background:var(--accent);color:#fff}
.btn-outline{background:transparent;border:1px solid var(--border);color:var(--text)}
.btn-sm{padding:6px 12px;font-size:12px}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:flex-end;justify-content:center;z-index:200}
.modal-content{background:#fff;border-radius:16px 16px 0 0;width:100%;max-width:480px;max-height:85vh;overflow-y:auto;padding:24px 20px}
.input{width:100%;padding:12px 14px;border:1px solid #eee;border-radius:8px;font-size:15px;color:#333;background:#f5f6fa;outline:none;margin-top:8px}
.input:focus{border-color:#E53935}
</style>
