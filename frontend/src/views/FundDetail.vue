<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFundStore } from '../stores/fund'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute(); const router = useRouter(); const store = useFundStore()
const code = route.params.code
const fund = ref(null); const loading = ref(true)
const canvas = ref(null); const profitCanvas = ref(null); const period = ref(30)
const periods = [{label:"一周",days:7},{label:"15天",days:15},{label:"30天",days:30},{label:"半年",days:180},{label:"一年",days:365}]
const myHold = computed(() => store.holdings.find(h => h.fund_code === code))
const isUp = v => v >= 0

onMounted(async () => {
  if (myHold.value) fund.value = { fund_name:myHold.value.fund_name||code, fund_code:code, fund_type:myHold.value.fund_type||'', latest_nav:myHold.value.current_nav, latest_date:myHold.value.nav_date }
  loading.value = !fund.value
  const cached = store.fundCache[code]
  if (cached) { fund.value = cached; loading.value = false; await nextTick(); setTimeout(() => drawCanvas(), 100) }
  setTimeout(() => drawProfit(), 150)
  try { fund.value = await api.getFundDetail(code, false, 365); store.fundCache[code] = fund.value } catch {}
  loading.value = false
  if (!cached) { await nextTick(); setTimeout(() => drawCanvas(), 200) }
  setTimeout(() => drawProfit(), 250)
})

function drawCanvas() {
  const c = canvas.value; if (!c || !fund.value?.nav_history?.length) return
  const lastDate=new Date(fund.value.nav_history[fund.value.nav_history.length-1].date+'T00:00:00');const cutoff=new Date(lastDate);cutoff.setDate(cutoff.getDate()-period.value);const cs=cutoff.toISOString().slice(0,10);const ce=lastDate.toISOString().slice(0,10);const d=fund.value.nav_history.filter(x=>x.date>=cs&&x.date<=ce)||fund.value.nav_history.slice(-period.value)
  if(!d.length)return
  const W=c.width=c.offsetWidth*2;const H=c.height=180*2
  const ctx=c.getContext('2d');ctx.scale(2,2)
  const pad={t:18,r:68,b:28,l:62};const pw=W/2-pad.l-pad.r;const ph=H/2-pad.t-pad.b
  const base=d[0].acc_nav||d[0].nav;const min=Math.min(...d.map(x=>x.nav));const max=Math.max(...d.map(x=>x.nav));const rng=(max-min)||1
  const xStep=pw/(d.length-1);ctx.clearRect(0,0,W,H)
  // Grid
  ctx.strokeStyle='#f5f5f5';ctx.lineWidth=0.5
  for(let i=0;i<=4;i++){const y=pad.t+ph*i/4;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+pw,y);ctx.stroke()}
  // Zero baseline
  const zeroY=pad.t+ph-(base-min)/rng*ph
  ctx.strokeStyle='rgba(0,0,0,0.12)';ctx.setLineDash([4,4]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(pad.l,zeroY);ctx.lineTo(pad.l+pw,zeroY);ctx.stroke();ctx.setLineDash([])
  // Area fill below line
  const chg=(((d[d.length-1].acc_nav||d[d.length-1].nav)-base)/base*100);const lc=chg>=0?'#E53935':'#4CAF50'
  ctx.beginPath()
  d.forEach((p,i)=>{const x=pad.l+xStep*i;const y=pad.t+ph-(p.nav-min)/rng*ph;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)})
  const lx=pad.l+xStep*(d.length-1);const ly=pad.t+ph-(d[d.length-1].nav-min)/rng*ph
  ctx.lineTo(lx,zeroY);ctx.lineTo(pad.l,zeroY);ctx.closePath()
  const grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ph)
  grad.addColorStop(0,chg>=0?'rgba(229,57,53,0.15)':'rgba(76,175,80,0.10)')
  grad.addColorStop(1,'rgba(255,255,255,0)')
  ctx.fillStyle=grad;ctx.fill()
  // Line
  ctx.strokeStyle=lc;ctx.lineWidth=2.5;ctx.lineJoin='round';ctx.lineCap='round';ctx.beginPath()
  d.forEach((p,i)=>{const x=pad.l+xStep*i;const y=pad.t+ph-(p.nav-min)/rng*ph;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)})
  ctx.stroke()
  // Data points
  d.forEach((p,i)=>{
    if(i%Math.max(1,Math.floor(d.length/8))===0||i===d.length-1){
      const x=pad.l+xStep*i;const y=pad.t+ph-(p.nav-min)/rng*ph
      ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill()
      ctx.fillStyle=lc;ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill()
    }
  })
  // End point highlight
  ctx.fillStyle=lc;ctx.beginPath();ctx.arc(lx,ly,5,0,Math.PI*2);ctx.fill()
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(lx,ly,2,0,Math.PI*2);ctx.fill()
  // X labels
  ctx.fillStyle='#999';ctx.font='10px sans-serif';ctx.textAlign='center'
  ctx.fillText(cs.slice(5),pad.l,H/2-pad.b+16);ctx.fillText(ce.slice(5),pad.l+pw,H/2-pad.b+16)
  // Y labels (NAV left)
  ctx.fillStyle='#888';ctx.font='10px sans-serif';ctx.textAlign='right'
  for(let i=0;i<=4;i++){const v=min+rng*i/4;ctx.fillText(v.toFixed(4),pad.l-6,pad.t+ph-ph*i/4+4)}
  // Y labels (% right)
  ctx.textAlign='left'
  for(let i=0;i<=4;i++){const v=min+rng*i/4;const pct=((v-base)/base*100);ctx.fillStyle=pct>=0?'#E53935':'#4CAF50';ctx.fillText((pct>=0?'+':'')+pct.toFixed(1)+'%',pad.l+pw+4,pad.t+ph-ph*i/4+4)}
  // Title
  ctx.fillStyle=lc;ctx.font='bold 13px sans-serif';ctx.textAlign='center'
  ctx.fillText((chg>=0?'+':'')+chg.toFixed(2)+'%',W/4,pad.t-4)
}

function drawProfit(){const c=profitCanvas.value;if(!c||!fund.value?.nav_history?.length)return;const lastDate=new Date(fund.value.nav_history[fund.value.nav_history.length-1].date+"T00:00:00");const cutoff=new Date(lastDate);cutoff.setDate(cutoff.getDate()-period.value);const cs=cutoff.toISOString().slice(0,10);const ce=lastDate.toISOString().slice(0,10);const d=fund.value.nav_history.filter(x=>x.date>=cs&&x.date<=ce)||fund.value.nav_history.slice(-period.value);if(!d.length)return;const W=c.width=c.offsetWidth*2;const H=c.height=170*2;const ctx=c.getContext("2d");ctx.scale(2,2);const pad={t:22,r:68,b:28,l:68};const pw=W/2-pad.l-pad.r;const ph=H/2-pad.t-pad.b;const invested=myHold.value?.buy_amount||0;const baseAcc=d[0].acc_nav||d[0].nav;const profits=d.map(x=>(((x.acc_nav||x.nav)/baseAcc-1)*invested));const min=Math.min(...profits,0);const max=Math.max(...profits,0);const rng=(max-min)||1;const xStep=pw/(d.length-1);ctx.clearRect(0,0,W,H);ctx.strokeStyle="#f5f5f5";ctx.lineWidth=0.5;for(let i=0;i<=4;i++){const y=pad.t+ph*i/4;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+pw,y);ctx.stroke()};const zeroYP=pad.t+ph-(0-min)/rng*ph;ctx.strokeStyle="rgba(0,0,0,0.12)";ctx.setLineDash([4,4]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(pad.l,zeroYP);ctx.lineTo(pad.l+pw,zeroYP);ctx.stroke();ctx.setLineDash([]);const chg=profits[profits.length-1];const lc=chg>=0?"#E53935":"#4CAF50";ctx.beginPath();profits.forEach((v,i)=>{const x=pad.l+xStep*i;const y=pad.t+ph-(v-min)/rng*ph;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)});const lx=pad.l+xStep*(profits.length-1);const ly=pad.t+ph-(chg-min)/rng*ph;ctx.lineTo(lx,zeroYP);ctx.lineTo(pad.l,zeroYP);ctx.closePath();const grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ph);grad.addColorStop(0,chg>=0?"rgba(229,57,53,0.12)":"rgba(76,175,80,0.08)");grad.addColorStop(1,"rgba(255,255,255,0)");ctx.fillStyle=grad;ctx.fill();ctx.strokeStyle=lc;ctx.lineWidth=2;ctx.lineJoin="round";ctx.beginPath();profits.forEach((v,i)=>{const x=pad.l+xStep*i;const y=pad.t+ph-(v-min)/rng*ph;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)});ctx.stroke();profits.forEach((v,i)=>{if(i%Math.max(1,Math.floor(profits.length/8))===0||i===profits.length-1){const x=pad.l+xStep*i;const y=pad.t+ph-(v-min)/rng*ph;ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill();ctx.fillStyle=lc;ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill()}});ctx.fillStyle=lc;ctx.beginPath();ctx.arc(lx,ly,5,0,Math.PI*2);ctx.fill();ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(lx,ly,2,0,Math.PI*2);ctx.fill();ctx.fillStyle="#999";ctx.font="10px sans-serif";ctx.textAlign="center";ctx.fillText(cs.slice(5),pad.l,H/2-pad.b+16);ctx.fillText(ce.slice(5),pad.l+pw,H/2-pad.b+16);ctx.fillStyle="#888";ctx.textAlign="right";for(let i=0;i<=4;i++){const v=min+rng*i/4;ctx.fillText((v>=0?"+":"")+v.toFixed(0)+"元",pad.l-6,pad.t+ph-ph*i/4+4)};ctx.textAlign="center";ctx.fillStyle=lc;ctx.font="bold 12px sans-serif";ctx.fillText((chg>=0?"+":"")+chg.toFixed(0)+"元",W/4,pad.t-2)}
let dt=null;function switchPeriod(p){period.value=p;clearTimeout(dt);dt=setTimeout(()=>requestAnimationFrame(()=>{drawCanvas();drawProfit()}),50)}
function goBack() { router.push('/') }
</script>

<template>
  <div class="fd">
    <div class="fd-bar">
      <button class="fd-back" @click="goBack"><AppIcon name="arrow-back" :size="18"/></button>
      <div class="fd-bar-info"><div class="fd-name">{{ fund?.fund_name || code }}</div><div class="fd-code">{{ code }} {{ fund?.fund_type || '' }}</div></div>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <template v-if="!loading">
      <div class="fd-card" v-if="myHold">
        <div class="fd-sec-title">我的持仓</div>
        <div class="fd-my-stats">
          <div class="fd-my-s"><span class="fd-my-sl">持有金额</span><span class="fd-my-sv">{{ (myHold.current_value||0).toLocaleString() }}元</span></div>
          <div class="fd-my-s"><span class="fd-my-sl">持仓收益</span><span class="fd-my-sv" :class="isUp(myHold.profit||0)?'up':'down'">{{ isUp(myHold.profit||0)?'+':'' }}{{ (myHold.profit||0).toFixed(2) }}</span></div>
          <div class="fd-my-s"><span class="fd-my-sl">收益率</span><span class="fd-my-sv" :class="isUp(myHold.profit_pct||0)?'up':'down'">{{ isUp(myHold.profit_pct||0)?'+':'' }}{{ (myHold.profit_pct||0).toFixed(2) }}%</span></div>
        </div>
        <div class="fd-my-meta"><span>投入 {{ (myHold.buy_amount||0).toLocaleString() }}元</span><span>份额 {{ myHold.buy_shares || '-' }}</span><span>买入 {{ myHold.buy_date || '-' }}</span></div>
      </div>
      <div class="fd-card" v-if="fund?.latest_nav">
        <div class="fd-navs">
          <div class="fd-nv"><span class="fd-nv-date">{{ fund.latest_date }}</span><span class="fd-nv-val">{{ fund.latest_nav?.toFixed(4) }}</span><span class="fd-nv-lbl">单位净值</span></div>
          <div class="fd-nv" v-if="myHold"><span class="fd-nv-date">日涨跌</span><span class="fd-nv-val est" :class="isUp(myHold.daily_return||0)?'up':'down'">{{ (myHold.daily_return||0)>=0?'+':'' }}{{ (myHold.daily_return||0).toFixed(2) }}%</span></div>
        </div>
      </div>
      <div class="fd-card">
        <div class="fd-sec-title">净值走势</div>
        <div class="fd-periods">
          <button v-for="p in periods" :key="p.days" class="fd-per-btn" :class="{on:period===p.days}" @click="switchPeriod(p.days)">{{ p.label }}</button>
        </div>
        <div v-if="fund?.nav_history" style="font-size:11px;color:#999;margin-bottom:4px">{{ fund.nav_history.length }} 个净值数据点</div>
        <canvas ref="canvas" style="width:100%;height:180px;margin-top:8px"></canvas>
        <div class="fd-sec-title" style="margin-top:12px">收益走势</div>
        <canvas ref="profitCanvas" style="width:100%;height:170px;margin-top:4px"></canvas>
      </div>
      <div class="fd-card" v-if="fund?.holdings?.length">
        <div class="fd-sec-title">前十大重仓股</div>
        <div class="fd-holds-table">
          <div class="fd-ht-row head"><span>股票</span><span>占比</span></div>
          <div class="fd-ht-row" v-for="s in fund.holdings.slice(0,10)" :key="s.stock_code"><span class="fd-ht-name">{{ s.stock_name||s.stock_code }}<i>{{ s.stock_code }}</i></span><span>{{ s.ratio }}%</span></div>
        </div>
      </div>
      <div v-if="!myHold && !fund?.latest_nav" class="loading">暂无数据</div>
    </template>
  </div>
</template>

<style scoped>
.fd{min-height:100vh;background:var(--bg);padding-bottom:20px}
.fd-bar{display:flex;align-items:center;gap:12px;padding:14px 16px;background:#fff;position:sticky;top:0;z-index:10;border-bottom:1px solid var(--border)}
.fd-back{background:none;border:none;padding:4px;color:var(--blue);cursor:pointer}
.fd-name{font-size:17px;font-weight:600}
.fd-code{font-size:12px;color:#999}
.fd-card{background:#fff;margin:10px 16px;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
.fd-sec-title{font-size:14px;font-weight:600;margin-bottom:10px}
.fd-navs{display:flex;justify-content:space-around}
.fd-nv{text-align:center}
.fd-nv-date{font-size:11px;color:#999;display:block}
.fd-nv-val{font-size:22px;font-weight:700;display:block;margin:2px 0}
.fd-nv-val.est{font-size:19px}
.fd-nv-lbl{font-size:11px;color:#999}
.fd-my-stats{display:flex;justify-content:space-around;margin-bottom:10px}
.fd-my-s{text-align:center}
.fd-my-sl{font-size:11px;color:#999;display:block}
.fd-my-sv{font-size:16px;font-weight:700;display:block;margin-top:2px}
.fd-my-meta{display:flex;gap:12px;font-size:11px;color:#999;padding-top:8px;border-top:1px solid #f5f5f5;flex-wrap:wrap}
.fd-periods{display:flex;gap:6px;flex-wrap:wrap}
.fd-per-btn{padding:4px 12px;border:1px solid #ddd;border-radius:12px;background:#f9f9f9;font-size:12px;cursor:pointer;color:#666}
.fd-per-btn.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.fd-holds-table{font-size:12px}
.fd-ht-row{display:flex;padding:8px 0;border-bottom:1px solid #f5f5f5;gap:4px}
.fd-ht-row.head{color:#999;font-size:11px;border-bottom:2px solid #eee}
.fd-ht-row span{flex:1;text-align:right}
.fd-ht-row span:first-child{flex:2;text-align:left}
.fd-ht-name i{font-size:10px;color:#999;margin-left:4px;font-style:normal}
</style>
