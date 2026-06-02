<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFundStore } from '../stores/fund'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const route=useRoute();const router=useRouter();const store=useFundStore()
const code=route.params.code
const myHold=computed(()=>store.holdings.find(h=>h.fund_code===code))
const isUp=v=>v>=0
const c1=ref(null);const c2=ref(null)
const period=ref(30)
const periods=[{label:'一周',days:7},{label:'15天',days:15},{label:'30天',days:30},{label:'半年',days:180},{label:'一年',days:365}]
const valuation=ref(null)
let navData=[],profitData=[],touchIdx=-1,tradeMarks=[],valTimer=null

async function drawBoth(){
 if(!c1.value||!c2.value)return
 let nav=(store.fundCache[code]||{}).nav_history
 if(!nav||!nav.length){const d=await api.getFundDetail(code,false,Math.max(period.value,365));nav=d.nav_history||[];store.fundCache[code]=d}
 if(!nav.length)return
 nav=nav.slice(-period.value)

 const draw=(cv,vals,label,unit)=>{
  const W=cv.width=cv.offsetWidth*3;cv.height=180*3
  const ctx=cv.getContext('2d');ctx.scale(3,3)
  const pad={t:14,r:44,b:22,l:48};const pw=cv.offsetWidth-pad.l-pad.r;const ph=180-pad.t-pad.b
  const min=Math.min(...vals,0);const max=Math.max(...vals,0);const rng=(max-min)||1
  const xStep=pw/(vals.length-1);ctx.clearRect(0,0,W,cv.height)
  ctx.strokeStyle='#f0f0f0';ctx.lineWidth=0.5
  for(let i=0;i<=4;i++){const y=pad.t+ph*i/4;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+pw,y);ctx.stroke()}
  const zeroY=pad.t+ph-(0-min)/rng*ph
  ctx.strokeStyle='rgba(0,0,0,0.1)';ctx.setLineDash([3,4]);ctx.lineWidth=1
  ctx.beginPath();ctx.moveTo(pad.l,zeroY);ctx.lineTo(pad.l+pw,zeroY);ctx.stroke();ctx.setLineDash([])
  const chg=vals[vals.length-1];const lc=chg>=0?'#E53935':'#4CAF50'
  ctx.strokeStyle=lc;ctx.lineWidth=1.8;ctx.lineJoin='round';ctx.lineCap='round';ctx.beginPath()
  vals.forEach((v,i)=>{const x=pad.l+xStep*i;const y=pad.t+ph-(v-min)/rng*ph;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)})
  ctx.stroke()
  const lx=pad.l+xStep*(vals.length-1);ctx.lineTo(lx,zeroY);ctx.lineTo(pad.l,zeroY);ctx.closePath()
  const grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ph)
  grad.addColorStop(0,chg>=0?'rgba(229,57,53,0.1)':'rgba(76,175,80,0.07)');grad.addColorStop(1,'rgba(255,255,255,0)')
  ctx.fillStyle=grad;ctx.fill()
  ctx.fillStyle='#999';ctx.font='9px sans-serif';ctx.textAlign='center'
  ctx.fillText(nav[0].date.slice(5),pad.l,180-pad.b+14);ctx.fillText(nav[nav.length-1].date.slice(5),pad.l+pw,180-pad.b+14)
  ctx.fillStyle='#888';ctx.textAlign='right';ctx.font='9px sans-serif'
  for(let i=0;i<=4;i++){const v=min+rng*i/4;ctx.fillText(label+(v>=0?'+':'')+v.toFixed(unit),pad.l-4,pad.t+ph-ph*i/4+3)}
  // Crosshair
  if(touchIdx>=0&&touchIdx<vals.length){
   const tx=pad.l+xStep*touchIdx;const ty=pad.t+ph-(vals[touchIdx]-min)/rng*ph
   ctx.strokeStyle='rgba(0,0,0,0.3)';ctx.lineWidth=1;ctx.setLineDash([2,3])
   ctx.beginPath();ctx.moveTo(tx,pad.t);ctx.lineTo(tx,pad.t+ph);ctx.stroke();ctx.setLineDash([])
   ctx.fillStyle='rgba(0,0,0,0.8)';const tw=ctx.measureText(vals[touchIdx].toFixed(unit)+label).width+12
   ctx.fillRect(tx-tw/2,pad.t-18,tw,16);ctx.fillStyle='#fff';ctx.font='9px sans-serif';ctx.textAlign='center'
   ctx.fillText(label+(vals[touchIdx]>=0?'+':'')+vals[touchIdx].toFixed(unit),tx,pad.t-5)
  }
  // Trade markers (B/S)
  if(tradeMarks.length){
   tradeMarks.forEach(t=>{
    const idx=nav.findIndex(n=>n.date===t.date)
    if(idx<0)return
    const mx=pad.l+xStep*idx
    ctx.fillStyle=t.type==='buy'?'#E53935':'#4CAF50'
    ctx.beginPath();ctx.moveTo(mx,pad.t-12);ctx.lineTo(mx-5,pad.t);ctx.lineTo(mx+5,pad.t);ctx.closePath();ctx.fill()
    ctx.fillStyle='#fff';ctx.font='bold 8px sans-serif';ctx.textAlign='center'
    ctx.fillText(t.type==='buy'?'B':'S',mx,pad.t-2)
   })
  }
 }
 // NAV chart
 const nv=nav.map(x=>x.nav);navData=nav.map((n,i)=>({date:n.date,val:nv[i]}))
 draw(c1.value,nv,'',4)
 // Profit chart
 const invested=myHold.value?.buy_amount||0
 let prevN=nav[0].nav;const profits=[0]
 for(let i=1;i<nav.length;i++){const dp=invested>0?((nav[i].nav-prevN)/prevN*invested):((nav[i].nav-prevN)/prevN*100);prevN=nav[i].nav;profits.push(dp)}
 profitData=nav.map((n,i)=>({date:n.date,val:profits[i]}))
 draw(c2.value,profits,invested>0?'':'',0)
}

// 后台加载交易标记（不阻塞图表）
async function loadTrades(){
 if(!myHold.value)return
 try{
  const r=await api.getHoldingProfitHistory(myHold.value.id,365)
  tradeMarks=r.trades||[]
 }catch(e){}
}

// 触摸拖拽
function handleTouch(e,data){
 const c=e.target;const r=c.getBoundingClientRect()
 const x=(e.touches[0].clientX-r.left)/c.offsetWidth
 const idx=Math.round(x*(data.length-1))
 touchIdx=Math.max(0,Math.min(data.length-1,idx))
 if(e.type==='touchend'||e.type==='touchcancel'){touchIdx=-1}
 drawBoth()
}

let dt=null
function switchPeriod(p){period.value=p;clearTimeout(dt);dt=setTimeout(()=>requestAnimationFrame(drawBoth),50)}

async function refreshValuation(){
 if(!myHold.value)return
 try{valuation.value=await api.getFundValuation(myHold.value.fund_code)}catch(e){}
}

onMounted(()=>{
 setTimeout(drawBoth,80);loadTrades().then(()=>drawBoth())
 refreshValuation();valTimer=setInterval(refreshValuation,30000)
})
function goBack(){router.push('/')}
</script>

<template>
<div class="fd">
 <div class="fd-bar"><button class="fd-back" @click="goBack"><AppIcon name="arrow-back" :size="18"/></button><div class="fd-bar-info"><div class="fd-name">{{myHold?.fund_name||code}}</div><div class="fd-code">{{code}} {{myHold?.fund_type||''}}</div></div></div>
 <template v-if="myHold">
  <div class="fd-card">
   <div class="fd-sec-title">我的持仓</div>
   <div class="fd-my-stats">
    <div class="fd-my-s"><span class="fd-my-sl">持有金额</span><span class="fd-my-sv">{{(myHold.current_value||0).toLocaleString()}}元</span></div>
    <div class="fd-my-s"><span class="fd-my-sl">持仓收益</span><span class="fd-my-sv" :class="isUp(myHold.profit||0)?'up':'down'">{{isUp(myHold.profit||0)?'+':''}}{{(myHold.profit||0).toFixed(2)}}</span></div>
    <div class="fd-my-s"><span class="fd-my-sl">收益率</span><span class="fd-my-sv" :class="isUp(myHold.profit_pct||0)?'up':'down'">{{isUp(myHold.profit_pct||0)?'+':''}}{{(myHold.profit_pct||0).toFixed(2)}}%</span></div>
   </div>
   <div class="fd-my-meta"><span>投入{{(myHold.buy_amount||0).toLocaleString()}}元</span><span>份额{{myHold.buy_shares||'-'}}</span><span>买入{{myHold.buy_date||'-'}}</span></div>
  </div>
  <div class="fd-card" v-if="valuation">
   <div class="fd-sec-title">实时估值 <span style="font-weight:400;font-size:11px;color:#bbb">{{valuation.gztime}}</span></div>
   <div class="fd-val-row">
    <div class="fd-val-item">
     <span class="fd-val-label">估算净值</span>
     <span class="fd-val-num">{{valuation.gsz?.toFixed(4)}}</span>
    </div>
    <div class="fd-val-item">
     <span class="fd-val-label">估算涨跌</span>
     <span class="fd-val-num" :class="isUp(valuation.gszzl||0)?'up':'down'">{{isUp(valuation.gszzl||0)?'+':''}}{{(valuation.gszzl||0).toFixed(2)}}%</span>
    </div>
    <div class="fd-val-item">
     <span class="fd-val-label">最新净值</span>
     <span class="fd-val-num" style="color:#999">{{valuation.dwjz?.toFixed(4)}}<i style="font-size:10px;font-style:normal;margin-left:4px">{{valuation.jzrq}}</i></span>
    </div>
   </div>
  </div>
  <div class="fd-card">
   <div class="fd-sec-title">净值走势</div>
   <div class="fd-periods"><button v-for="p in periods" :key="p.days" class="fd-per-btn" :class="{on:period===p.days}" @click="switchPeriod(p.days)">{{p.label}}</button></div>
   <canvas ref="c1" style="width:100%;height:180px;touch-action:none" @touchstart.prevent="handleTouch($event,navData)" @touchmove.prevent="handleTouch($event,navData)" @touchend.prevent="touchIdx=-1;drawBoth()"></canvas></div>
  <div class="fd-card">
   <div class="fd-sec-title">收益走势</div>
   <canvas ref="c2" style="width:100%;height:180px;touch-action:none" @touchstart.prevent="handleTouch($event,profitData)" @touchmove.prevent="handleTouch($event,profitData)" @touchend.prevent="touchIdx=-1;drawBoth()"></canvas></div>
 </template>
 <div v-else class="loading">暂无持仓数据</div>
</div>
</template>

<style scoped>
.fd{min-height:100vh;background:var(--bg);padding-bottom:20px}
.fd-bar{display:flex;align-items:center;gap:12px;padding:14px 16px;background:#fff;position:sticky;top:0;z-index:10;border-bottom:1px solid var(--border)}
.fd-back{background:none;border:none;padding:4px;color:var(--blue);cursor:pointer}
.fd-name{font-size:17px;font-weight:600}.fd-code{font-size:12px;color:#999}
.fd-card{background:#fff;margin:10px 16px;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
.fd-sec-title{font-size:14px;font-weight:600;margin-bottom:10px}
.fd-my-stats{display:flex;justify-content:space-around;margin-bottom:10px}.fd-my-s{text-align:center}
.fd-my-sl{font-size:11px;color:#999;display:block}.fd-my-sv{font-size:16px;font-weight:700;display:block;margin-top:2px}
.fd-my-meta{display:flex;gap:12px;font-size:11px;color:#999;padding-top:8px;border-top:1px solid #f5f5f5;flex-wrap:wrap}
.fd-val-row{display:flex;justify-content:space-around;margin-top:8px}
.fd-val-item{text-align:center}
.fd-val-label{font-size:11px;color:#999;display:block}
.fd-val-num{font-size:17px;font-weight:700;display:block;margin-top:2px}
.fd-periods{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.fd-per-btn{padding:4px 12px;border:1px solid #ddd;border-radius:12px;background:#f9f9f9;font-size:12px;cursor:pointer;color:#666}
.fd-per-btn.on{background:var(--blue);color:#fff;border-color:var(--blue)}
</style>
