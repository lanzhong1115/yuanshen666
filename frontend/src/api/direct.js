// Cordova原生HTTP - 绕过WebView所有限制
const nativeGet=async(url)=>{
  return new Promise((resolve)=>{
    try{
      cordova.plugin.http.get(url,{},{},'UTF-8',
        r=>resolve(r.data||''),
        e=>{console.log('HTTP err:',url.slice(0,60),e.error);resolve('')}
      )
    }catch(e){console.log('HTTP ex:',e.message);resolve('')}
  })
}
const sj=t=>{try{return JSON.parse(t.replace(/NaN/g,'null').replace(/Infinity/g,'null'))}catch{return null}}

export async function fetchFundNAV(code,days=90){try{const t=await nativeGet('http://fund.eastmoney.com/pingzhongdata/'+code+'.js');const nm=t.match(/Data_netWorthTrend\s*=\s*(\[[\s\S]*?\])/);if(!nm)return[];const nd=sj(nm[1]);if(!nd)return[];const am=t.match(/Data_ACWorthTrend\s*=\s*(\[[\s\S]*?\])/);let amap={};if(am){(sj(am[1])||[]).forEach(a=>{if(Array.isArray(a))amap[a[0]]=a[1];else if(a?.x)amap[a.x]=a.y})};const c=Date.now()-days*86400000;const r=[];nd.forEach(n=>{if(n.x>=c)r.push({date:new Date(n.x).toISOString().slice(0,10),nav:+n.y.toFixed(4),acc_nav:+(amap[n.x]||0).toFixed(4),daily_return:0})});for(let i=1;i<r.length;i++)if(r[i-1].nav>0)r[i].daily_return=+((r[i].nav-r[i-1].nav)/r[i-1].nav*100).toFixed(2);return r.slice(-days)}catch{return[]}}

export async function fetchIndices(){const n={'000001':'上证指数','399001':'深证成指','399006':'创业板指','000688':'科创50','000300':'沪深300','000905':'中证500','000852':'中证1000','399005':'中小100'};try{const t=await nativeGet('http://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000688,1.000300,1.000905,1.000852,0.399005&fields=f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18');const d=sj(t);if(d?.data?.diff)return d.data.diff.map(i=>({code:i.f12,name:n[i.f12]||i.f14,price:+i.f2?.toFixed(2)||0,change_pct:+i.f3?.toFixed(2)||0,change_amt:+i.f4?.toFixed(2)||0,volume:i.f5||0,high:+i.f15?.toFixed(2)||0,low:+i.f16?.toFixed(2)||0,open:+i.f17?.toFixed(2)||0,prev_close:+i.f18?.toFixed(2)||0}))}catch{}return[]}

export async function fetchSectors(){try{const t=await nativeGet('http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=30&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f2,f3,f12,f14');const d=sj(t);if(d?.data?.diff)return d.data.diff.map(i=>({code:i.f12,name:i.f14,price:+i.f2?.toFixed(2)||0,change_pct:+i.f3?.toFixed(2)||0}))}catch{}return[]}

let fl=null
export async function searchFunds(q){try{if(!fl){const t=await nativeGet('http://fund.eastmoney.com/js/fundcode_search.js');const m=t.match(/var\s+r\s*=\s*(\[\[[\s\S]*?\]\]);/);if(m)fl=sj(m[1])||[]}if(!fl)return[];const ql=q.toLowerCase();return fl.filter(i=>i[0].includes(ql)||(i[2]||'').toLowerCase().includes(ql)).slice(0,20).map(i=>({fund_code:i[0],fund_name:i[2],fund_type:i[3]||''}))}catch{return[]}}
