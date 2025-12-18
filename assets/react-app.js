;(function(){
  var h = React.createElement;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var useRef = React.useRef;

  function ensureChartJs(){
    return new Promise(function(resolve){
      if (window.Chart) { resolve(window.Chart); return; }
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
      s.onload = function(){ resolve(window.Chart); };
      s.onerror = function(){ resolve(null); };
      document.head.appendChild(s);
    });
  }

  function normalizeTipo(t){
    var s = String(t || '').toLowerCase();
    if (!s) return '';
    if (s.startsWith('sub') && s.indexOf('almox') !== -1) return 'sub_almoxarifado';
    if (s.indexOf('almox') !== -1 && s.indexOf('sub') === -1) return 'almoxarifado';
    if (s.startsWith('cen')) return 'central';
    if (s.startsWith('set')) return 'setor';
    return s;
  }

  function formatDateKey(date){
    var d = new Date(date);
    var y = d.getFullYear();
    var m = String(d.getMonth()+1).padStart(2,'0');
    var day = String(d.getDate()).padStart(2,'0');
    return y+'-'+m+'-'+day;
  }

  function getLastNDays(n){
    var days = [];
    var today = new Date();
    for (var i=n-1;i>=0;i--){
      var d = new Date(today);
      d.setDate(today.getDate()-i);
      days.push(formatDateKey(d));
    }
    return days;
  }

  function movingAverage(series, windowSize){
    var result = [];
    var sum = 0;
    var q = [];
    for (var i=0;i<series.length;i++){
      sum += series[i];
      q.push(series[i]);
      if (q.length>windowSize) sum -= q.shift();
      var denom = Math.min(windowSize, i+1);
      result.push(sum/denom);
    }
    return result;
  }

  function normalizeIdStr(val){
    var s = String(val == null ? '' : val).trim();
    if (!s) return '';
    var m = s.match(/ObjectId\(['"]?([0-9a-fA-F]{24})['"]?\)/);
    if (m && m[1]) return m[1];
    if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith('\'') && s.endsWith('\''))){
      return s.slice(1,-1);
    }
    return s;
  }

  function ConsumoMedioWidget(props){
    var chartRef = useRef(null);
    var resumoText = useRef('');
    var _a = useState({datasets:[], labels:[]}), graph = _a[0], setGraph = _a[1];
    var isOperador = String(props.isOperador||'') === 'true';
    var setorId = normalizeIdStr(props.setorId||'');
    useEffect(function(){
      var run = async function(){
        var end = new Date();
        var start = new Date();
        start.setDate(end.getDate()-29);
        var data_inicio = start.toISOString().substring(0,10);
        var data_fim = end.toISOString().substring(0,10);
        var resp = await window.fetchJson('/api/movimentacoes?per_page=1000&data_inicio='+encodeURIComponent(data_inicio)+'&data_fim='+encodeURIComponent(data_fim));
        var items = Array.isArray(resp.items)? resp.items : [];
        var LEVELS = isOperador? ['setor'] : ['almoxarifado','sub_almoxarifado','setor'];
        if (isOperador && setorId){
          items = items.filter(function(m){
            var origemTipo = normalizeTipo(m.origem_tipo || m.local_tipo || '');
            var origemId = normalizeIdStr(m.origem_id || m.local_id || '');
            return origemTipo==='setor' && origemId===setorId;
          });
        }
        var days = getLastNDays(30);
        var daily = {};
        for (var i=0;i<days.length;i++){ daily[days[i]] = {central:0, almoxarifado:0, sub_almoxarifado:0, setor:0}; }
        var tiposSaida = new Set(['transferencia','saida','consumo','retirada']);
        for (var j=0;j<items.length;j++){
          var m = items[j];
          var tipoMov = String(m.tipo_movimentacao || m.tipo || '').toLowerCase();
          if (!tiposSaida.has(tipoMov)) continue;
          var dayKey = formatDateKey(m.data_movimentacao || m.created_at || Date.now());
          if (!daily[dayKey]) continue;
          var origem = normalizeTipo(m.origem_tipo || m.local_tipo || '');
          if (LEVELS.indexOf(origem)===-1) continue;
          var qty = Number(m.quantidade || 0);
          if (!isFinite(qty) || qty<=0) continue;
          daily[dayKey][origem] += qty;
        }
        var COLORS = { almoxarifado:'#22c55e', sub_almoxarifado:'#06b6d4', setor:'#f59e0b' };
        var datasets = [];
        var resumo = {};
        for (var k=0;k<LEVELS.length;k++){
          var level = LEVELS[k];
          var series = days.map(function(d){ return daily[d][level] || 0; });
          var avg7 = movingAverage(series, 7);
          datasets.push({ label: level.charAt(0).toUpperCase()+level.slice(1).replace('_',' '), data: avg7, borderColor: COLORS[level], backgroundColor: COLORS[level], tension:0.25, pointRadius:0, borderWidth:2 });
          var last7 = avg7.slice(-7);
          var mAvg = last7.length? (last7.reduce(function(a,b){return a+b;},0)/last7.length) : 0;
          resumo[level] = mAvg;
        }
        resumoText.current = isOperador? ('Média (7d) — Setor: '+Number(resumo.setor||0).toFixed(1)) : ('Média (7d) — Almox: '+Number(resumo.almoxarifado||0).toFixed(1)+', Sub: '+Number(resumo.sub_almoxarifado||0).toFixed(1)+', Setor: '+Number(resumo.setor||0).toFixed(1));
        setGraph({ datasets: datasets, labels: days.map(function(d){ return d.substring(5); }) });
        var Chart = await ensureChartJs();
        if (Chart && chartRef.current){
          new Chart(chartRef.current, { type:'line', data:{ labels: days.map(function(d){return d.substring(5);}), datasets: datasets }, options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:true, position:'bottom' }, tooltip:{ mode:'index', intersect:false } }, interaction:{ mode:'index', intersect:false }, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Consumo (média 7d)'} }, x:{ title:{ display:true, text:'Últimos 30 dias'} } } } });
        }
      };
      run();
    }, [props.isOperador, props.setorId]);
    return h('div',{className:'card border-0 shadow-sm h-100'},[
      h('div',{className:'card-header bg-transparent d-flex justify-content-between align-items-center'},[
        h('h5',{className:'card-title mb-0'}, [h('i',{className:'fas fa-chart-line me-2'}), (isOperador? 'Consumo Médio do Setor (30 dias)' : 'Consumo Médio por Nível (30 dias)')]),
        h('div',{className:'d-flex align-items-center gap-2'}, isOperador? [h('span',{className:'badge bg-warning text-dark'},'Setor')] : [h('span',{className:'badge bg-success'},'Almox'), h('span',{className:'badge bg-info text-dark'},'Sub'), h('span',{className:'badge bg-warning text-dark'},'Setor')])
      ]),
      h('div',{className:'card-body'},[
        h('div',{style:{height:'260px'}}, h('canvas',{ref:chartRef})),
        h('div',{className:'mt-3'}, h('small',{className:'text-muted'}, String(resumoText.current||'Carregando dados de consumo...')))
      ])
    ]);
  }

  function setorColor(idx, total){
    var hue = Math.round((idx/Math.max(1,total))*300);
    return 'hsl('+hue+', 70%, 50%)';
  }

  function ConsumoPorSetorWidget(){
    var chartRef = useRef(null);
    var _a = useState({labels:[], datasets:[]}), graph = _a[0], setGraph = _a[1];
    var _b = useState([]), resumoRows = _b[0], setResumoRows = _b[1];
    var _c = useState([]), legendBadges = _c[0], setLegendBadges = _c[1];
    useEffect(function(){
      var run = async function(){
        var end = new Date();
        var start = new Date();
        start.setDate(end.getDate()-29);
        var data_inicio = start.toISOString().substring(0,10);
        var data_fim = end.toISOString().substring(0,10);
        var sResp = await window.fetchJson('/api/setores?per_page=200');
        var setores = Array.isArray(sResp.items)? sResp.items : [];
        var totalSetores = setores.length;
        var days = getLastNDays(30);
        var mResp = await window.fetchJson('/api/movimentacoes?per_page=3000&data_inicio='+encodeURIComponent(data_inicio)+'&data_fim='+encodeURIComponent(data_fim));
        var movs = Array.isArray(mResp.items)? mResp.items : [];
        var tiposSaida = new Set(['transferencia','saida','consumo','retirada']);
        var estResp = await window.fetchJson('/api/estoque/hierarquia?per_page=2000');
        var estItems = Array.isArray(estResp.items)? estResp.items : (Array.isArray(estResp)? estResp : []);
        var datasets = [];
        var rows = [];
        var badges = [];
        setores.forEach(function(s, idx){
          var sid = normalizeIdStr(s.id);
          var sname = s.nome || ('Setor '+sid);
          var color = setorColor(idx, Math.max(6, totalSetores));
          var daily = {};
          for (var d=0; d<days.length; d++){ daily[days[d]] = 0; }
          for (var m=0; m<movs.length; m++){
            var mv = movs[m];
            var tipoMov = String(mv.tipo_movimentacao || mv.tipo || '').toLowerCase();
            if (!tiposSaida.has(tipoMov)) continue;
            var origemTipo = normalizeTipo(mv.origem_tipo || mv.local_tipo || '');
            if (origemTipo !== 'setor') continue;
            var origemId = normalizeIdStr(mv.origem_id || mv.local_id || '');
            if (origemId !== sid) continue;
            var dayKey = formatDateKey(mv.data_movimentacao || mv.created_at || Date.now());
            if (!daily[dayKey]) continue;
            var qty = Number(mv.quantidade || 0);
            if (!isFinite(qty) || qty<=0) continue;
            daily[dayKey] += qty;
          }
          var series = days.map(function(d){ return daily[d] || 0; });
          var avg7 = movingAverage(series, 7);
          var total30d = series.reduce(function(a,b){return a+b;},0);
          var last7 = avg7.slice(-7);
          var last7Avg = last7.length? (last7.reduce(function(a,b){return a+b;},0)/last7.length) : 0;
          var estoqueAtual = 0;
          for (var it=0; it<estItems.length; it++){
            var e = estItems[it];
            var tipo = normalizeTipo(e.local_tipo || '');
            if (tipo !== 'setor') continue;
            var lid = normalizeIdStr(e.local_id || e.setor_id || '');
            if (lid !== sid) continue;
            var q = Number(e.quantidade_disponivel == null ? (e.quantidade || 0) : e.quantidade_disponivel);
            estoqueAtual += (isFinite(q)? q : 0);
          }
          datasets.push({ label:sname, data:avg7, borderColor:color, backgroundColor:color, tension:0.25, pointRadius:0, borderWidth:2 });
          rows.push({ nome:sname, media7d:last7Avg, saidas30d:total30d, estoqueAtual:estoqueAtual });
          var shortName = String(sname).length>22? (String(sname).slice(0,22)+'…') : String(sname);
          badges.push(h('span',{className:'badge', style:{ backgroundColor: color, color: '#fff', whiteSpace:'nowrap', textOverflow:'ellipsis', overflow:'hidden' }}, shortName));
        });
        setLegendBadges(badges);
        setResumoRows(rows);
        setGraph({ labels: days.map(function(d){return d.substring(5);}), datasets: datasets });
        var Chart = await ensureChartJs();
        if (Chart && chartRef.current){
          new Chart(chartRef.current, { type:'line', data:{ labels: days.map(function(d){return d.substring(5);}), datasets: datasets }, options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:false }, tooltip:{ mode:'index', intersect:false } }, interaction:{ mode:'index', intersect:false }, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Consumo (média 7d)'} }, x:{ title:{ display:true, text:'Últimos 30 dias'} } } } });
        }
      };
      run();
    }, []);
    return h('div',{className:'card border-0 shadow-sm h-100'},[
      h('div',{className:'card-header bg-transparent d-flex justify-content-between align-items-start'},[
        h('h5',{className:'card-title mb-0'}, [h('i',{className:'fas fa-chart-line me-2'}),'Consumo por Setor (30 dias)']),
        h('div',{className:'d-flex flex-wrap align-items-start gap-2', style:{ maxHeight:'140px', overflowY:'auto' }}, legendBadges)
      ]),
      h('div',{className:'card-body'},[
        h('div',{style:{height:'260px'}}, h('canvas',{ref:chartRef})),
        h('div',{className:'mt-3'},[
          h('div',{className:'table-responsive', style:{ maxHeight:'260px', overflowY:'auto' }},[
            h('table',{className:'table table-sm align-middle'},[
              h('thead',null,h('tr',null,[
                h('th',null,'Setor'),
                h('th',{className:'text-end'},'Média 7d'),
                h('th',{className:'text-end'},'Saídas 30d'),
                h('th',{className:'text-end'},'Tem agora')
              ])),
              h('tbody',null, resumoRows.length? resumoRows.map(function(r, idx){
                return h('tr',{key:String(idx)},[
                  h('td',null,r.nome),
                  h('td',{className:'text-end'}, Number(r.media7d).toFixed(1)),
                  h('td',{className:'text-end'}, Number(r.saidas30d).toFixed(1)),
                  h('td',{className:'text-end'}, Number(r.estoqueAtual).toFixed(1))
                ]);
              }) : [h('tr',null,h('td',{colSpan:4, className:'text-center text-muted'},'Carregando dados por setor...'))])
            ])
          ])
        ])
      ]),
      h('div',{className:'card-footer bg-transparent'}, h('small',{className:'text-muted'}, 'Séries com média móvel de 7 dias por setor. Escopo respeitado pelo seu nível de acesso.'))
    ]);
  }

  function QuickActionsWidget(){
    return h('div',{className:'card border-0 shadow-sm h-100'},[
      h('div',{className:'card-header bg-transparent'}, h('h5',{className:'card-title mb-0'}, [h('i',{className:'fas fa-bolt me-2'}),'Ações Rápidas'])),
      h('div',{className:'card-body'},[
        h('div',{className:'d-grid gap-2'},[
          h('a',{href:'/movimentacoes#transferencia', className:'btn btn-outline-primary btn-sm'}, [h('i',{className:'fas fa-exchange-alt me-1'}),'Transferência']),
          h('a',{href:'/movimentacoes#saida', className:'btn btn-outline-success btn-sm'}, [h('i',{className:'fas fa-arrow-up me-1'}),'Saída'])
        ])
      ])
    ]);
  }

  function EstoqueBaixoWidget(){
    var _a = useState({ loading:true, error:false, low:[], zero:[] }), st = _a[0], setSt = _a[1];
    useEffect(function(){
      var run = async function(){
        try {
          var data = await window.fetchJson('/api/estoque/hierarquia?per_page=200');
          var items = Array.isArray(data.items)? data.items : [];
          var lowItems = [];
          var zeroItems = [];
          for (var i=0;i<items.length;i++){
            var it = items[i];
            var disp = parseFloat(it.quantidade_disponivel || 0);
            var inicial = parseFloat(it.quantidade_inicial || 0);
            var limiarBaixo = Math.max(inicial*0.1, 5);
            if (disp <= 0) zeroItems.push(it); else if (disp <= limiarBaixo) lowItems.push(Object.assign({}, it, { limiarBaixo: limiarBaixo }));
          }
          setSt({ loading:false, error:false, low:lowItems.slice(0,3), zero:zeroItems.slice(0,3) });
        } catch(e){
          setSt({ loading:false, error:true, low:[], zero:[] });
        }
      };
      run();
    }, []);
    function normalizeTipo2(t){ return String(t||'').toLowerCase().replace(/[-_]/g,'').replace(/^subalmoxarifado$/, 'sub‑almoxarifado'); }
    function formatQtd(n){ var v = Number(n||0); return v%1===0? v.toString() : v.toFixed(2); }
    return h('div',{className:'card h-100'},[
      h('div',{className:'card-header bg-warning text-dark'}, h('h6',{className:'card-title mb-0'}, [h('i',{className:'fas fa-exclamation-triangle me-2'}),'Estoque Baixo'])),
      h('div',{className:'card-body'},[
        (st.loading? h('div',{className:'text-center'}, [h('div',{className:'spinner-border spinner-border-sm text-warning', role:'status'}, h('span',{className:'visually-hidden'},'Carregando...')), h('p',{className:'mt-2 mb-0 text-muted'},'Carregando...')]) : (st.error? h('div',{className:'text-center text-danger'}, [h('i',{className:'fas fa-exclamation-circle fa-2x mb-2'}), h('p',{className:'mb-0'},'Erro ao carregar dados')]) : (function(){
          var items = [];
          for (var z=0; z<st.zero.length; z++){
            var it = st.zero[z];
            items.push(h('div',{className:'list-group-item px-0 py-2'},[
              h('div',{className:'d-flex justify-content-between align-items-center'},[
                h('div',null,[h('strong',{className:'text-danger'}, it.produto_nome || 'Produto'), h('div',{className:'small text-muted'}, normalizeTipo2(it.local_tipo)+' · '+(it.local_nome || 'Local'))]),
                h('span',{className:'badge bg-danger'}, formatQtd(it.quantidade_disponivel))
              ])
            ]));
          }
          for (var l=0; l<st.low.length; l++){
            var it2 = st.low[l];
            var pct = (it2.limiarBaixo>0)? Math.min(100, Math.max(0, (parseFloat(it2.quantidade_disponivel || 0)/it2.limiarBaixo)*100)) : 0;
            items.push(h('div',{className:'list-group-item px-0 py-2'},[
              h('div',{className:'d-flex justify-content-between align-items-center'},[
                h('div',null,[h('strong',{className:'text-warning'}, it2.produto_nome || 'Produto'), h('div',{className:'small text-muted'}, normalizeTipo2(it2.local_tipo)+' · '+(it2.local_nome || 'Local'))]),
                h('span',{className:'badge bg-warning text-dark'}, formatQtd(it2.quantidade_disponivel))
              ]),
              h('div',{className:'progress mt-1', style:{height:'4px'}}, h('div',{className:'progress-bar bg-warning', style:{width:String(pct)+'%'}}))
            ]));
          }
          if (!items.length) return h('div',{className:'text-center text-success'}, [h('i',{className:'fas fa-check-circle fa-2x mb-2'}), h('p',{className:'mb-0'},'Nenhum item com estoque baixo!')]);
          return h('div',{className:'list-group list-group-flush'}, items);
        })()))
      ]),
      h('div',{className:'card-footer bg-light'}, h('a',{href:'/estoque', className:'btn btn-sm btn-outline-warning'}, [h('i',{className:'fas fa-eye me-1'}),'Ver Estoque Completo']))
    ]);
  }

  function parseDateFlexible(value){
    if (!value) return null;
    try {
      if (value instanceof Date) return value;
      if (typeof value === 'number') return new Date(value);
      var s = String(value).trim();
      var dm = s.match(/^([0-3]?\d)[\/\-]([0-1]?\d)[\/\-](\d{4})(?:\s+(\d{1,2}):(\d{2}))?$/);
      if (dm){
        var d = parseInt(dm[1],10);
        var m = parseInt(dm[2],10)-1;
        var y = parseInt(dm[3],10);
        var hh = dm[4]? parseInt(dm[4],10) : 0;
        var mm = dm[5]? parseInt(dm[5],10) : 0;
        return new Date(y,m,d,hh,mm);
      }
      var iso = new Date(s);
      if (!isNaN(iso.getTime())) return iso;
    } catch(_){ }
    return null;
  }

  function formatDateISO(s){
    try {
      var d = new Date(s);
      var dd = String(d.getDate()).padStart(2,'0');
      var mm = String(d.getMonth()+1).padStart(2,'0');
      var yyyy = d.getFullYear();
      return dd+'/'+mm+'/'+yyyy;
    } catch(e){
      return String(s||'-');
    }
  }

  function VencimentosWidget(){
    var _a = useState({ loading:true, error:false, items:[], vencidos:0, proximos:0 }), st = _a[0], setSt = _a[1];
    useEffect(function(){
      var run = async function(){
        var DIAS_AVISO = 30;
        try {
          var prodResp = await window.fetchJson('/api/produtos?per_page=200&ativo=true');
          var produtos = Array.isArray(prodResp.items)? prodResp.items : (Array.isArray(prodResp)? prodResp : []);
          if (!produtos.length){ setSt({ loading:false, error:false, items:[], vencidos:0, proximos:0 }); return; }
          var hoje = new Date();
          var items = [];
          var totalVencidos = 0;
          var totalProximos = 0;
          for (var p=0; p<produtos.length; p++){
            var pr = produtos[p];
            try {
              var lotResp = await window.fetchJson('/api/produtos/'+encodeURIComponent(pr.id)+'/lotes');
              var lotes = Array.isArray(lotResp.items)? lotResp.items : (Array.isArray(lotResp)? lotResp : []);
              for (var l=0; l<lotes.length; l++){
                var lt = lotes[l];
                var dv = parseDateFlexible(lt.data_vencimento);
                if (!dv) continue;
                var dias = Math.ceil((dv - hoje)/(1000*60*60*24));
                var status = null;
                if (dias < 0){ status='vencido'; totalVencidos++; }
                else if (dias <= DIAS_AVISO){ status='proximo'; totalProximos++; }
                else { continue; }
                items.push({ produto_id: pr.id, produto_nome: pr.nome || 'Produto', numero_lote: lt.numero_lote || lt.lote || '-', data_vencimento: dv.toISOString(), dias_para_vencer: dias, status: status });
              }
            } catch(_){ }
          }
          items.sort(function(a,b){ var ra = a.status==='vencido'?0:1; var rb = b.status==='vencido'?0:1; if (ra!==rb) return ra-rb; return a.dias_para_vencer - b.dias_para_vencer; });
          items = items.slice(0,5);
          setSt({ loading:false, error:false, items:items, vencidos:Number(totalVencidos||0), proximos:Number(totalProximos||0) });
        } catch(_){
          setSt({ loading:false, error:true, items:[], vencidos:0, proximos:0 });
        }
      };
      run();
    }, []);
    return h('div',{className:'card border-0 shadow-sm h-100'},[
      h('div',{className:'card-header bg-transparent d-flex justify-content-between align-items-center'},[
        h('h5',{className:'card-title mb-0'}, [h('i',{className:'fas fa-calendar-exclamation me-2'}),'Vencimentos de Lotes']),
        h('div',{className:'d-flex align-items-center gap-2'}, [h('span',{className:'badge bg-danger'}, ['Vencidos: ', h('span',null,String(st.vencidos))]), h('span',{className:'badge bg-warning text-dark'}, ['Próximos (30d): ', h('span',null,String(st.proximos))])])
      ]),
      h('div',{className:'card-body'},[
        (st.loading? h('div',{className:'text-center'}, [h('div',{className:'spinner-border spinner-border-sm text-primary', role:'status'}, h('span',{className:'visually-hidden'},'Carregando...')), h('p',{className:'mt-2 mb-0 text-muted'},'Carregando...')]) : (st.error? h('div',{className:'text-center text-danger'}, [h('i',{className:'fas fa-exclamation-circle fa-2x mb-2'}), h('p',{className:'mb-0'},'Erro ao carregar dados')]) : (function(){
          if (!st.items.length) return h('div',{className:'text-center text-success'}, [h('i',{className:'fas fa-check-circle fa-2x mb-2'}), h('p',{className:'mb-0'},'Nenhum lote vencido ou próximo ao vencimento.')]);
          var rows = [];
          for (var i=0;i<st.items.length;i++){
            var item = st.items[i];
            var status = String(item.status||'').toLowerCase();
            var cls = status==='vencido'? 'text-danger' : 'text-warning';
            var lot = item.numero_lote || '-';
            var nome = item.produto_nome || 'Produto';
            rows.push(h('div',{className:'list-group-item px-0 py-2'},[
              h('div',{className:'d-flex justify-content-between align-items-center'},[
                h('div',null,[h('h6',{className:'mb-1'},nome), h('small',{className:'text-muted'}, 'Lote: '+lot)]),
                h('div',{className:'text-end'},[ h('div',{className:cls}, h('strong',null,(function(){ var n=Number(item.dias_para_vencer||0); if (!isFinite(n)) return '-'; if (n<0) return 'Vencido há '+Math.abs(n)+'d'; if (n===0) return 'Vence hoje'; return 'Vence em '+n+'d'; })() )), h('small',{className:'text-muted'}, 'Venc.: '+formatDateISO(item.data_vencimento)) ])
              ])
            ]));
          }
          return h('div',{className:'list-group list-group-flush'}, rows);
        })()))
      ]),
      h('div',{className:'card-footer bg-light d-flex justify-content-end'}, h('a',{href:'/estoque', className:'btn btn-sm btn-outline-primary'}, [h('i',{className:'fas fa-warehouse me-1'}),'Consultar Estoque']))
    ]);
  }

  function WidgetContainer(props){
    return h('div',{className:'col-'+(props.size||'lg-6')+' mb-4'}, props.children);
  }

  function Dashboard(props){
    var context = props && props.context ? props.context : {};
    var title = props && props.title ? props.title : 'Dashboard';
    var scopeName = props && props.scopeName ? props.scopeName : '';
    var nivel = (context.nivelAcesso||'').trim();
    var isOperador = nivel==='operador_setor';
    var widgets = [];
    var can = function(levels){ return levels.indexOf(nivel) !== -1; };
    if (can(['super_admin','admin_central','gerente_almox','resp_sub_almox','operador_setor'])){
      widgets.push({ id:'consumo_medio', size:'lg-12', node: h(ConsumoMedioWidget, { isOperador:String(isOperador), setorId: context.setorId||'' }) });
    }
    if (can(['super_admin','admin_central','gerente_almox','resp_sub_almox','operador_setor'])){
      widgets.push({ id:'acoes_rapidas', size:'lg-6', node: h(QuickActionsWidget) });
    }
    if (can(['super_admin','admin_central','gerente_almox','resp_sub_almox'])){
      widgets.push({ id:'estoque_baixo', size:'lg-6', node: h(EstoqueBaixoWidget) });
      widgets.push({ id:'vencimentos', size:'lg-6', node: h(VencimentosWidget) });
    }
    return h('div',{className:'container-fluid'},[
      h('div',{className:'row mb-4'}, h('div',{className:'col-12'}, [ h('h1',{className:'h3 mb-0'}, title), h('p',{className:'text-muted'}, (scopeName? scopeName+' - ' : '') + (context.userNome||'')) ])),
      h('div',{className:'row'}, widgets.map(function(w){ return h(WidgetContainer,{key:w.id,size:w.size}, w.node); }))
    ]);
  }

  function mountDashboard(opts){
    var rootEl = document.getElementById('app-root');
    if(!rootEl){
      rootEl = document.createElement('div');
      rootEl.id = 'app-root';
      document.body.appendChild(rootEl);
    }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(Dashboard, { title: (opts&&opts.title)||'Dashboard', scopeName: (opts&&opts.scopeName)||'', context: (opts&&opts.userContext)||{} }));
  }

  window.PluckApp = { mountDashboard: mountDashboard };
  function EstoquePage(){
    var _a = useState(''), filtroProduto = _a[0], setFiltroProduto = _a[1];
    var _b = useState(''), filtroTipo = _b[0], setFiltroTipo = _b[1];
    var _c = useState(''), filtroStatus = _c[0], setFiltroStatus = _c[1];
    var _d = useState(''), filtroLocal = _d[0], setFiltroLocal = _d[1];
    var _e = useState([]), locais = _e[0], setLocais = _e[1];
    var _f = useState([]), items = _f[0], setItems = _f[1];
    var _g = useState({ page:1, pages:1, total:0, per_page:20 }), pagination = _g[0], setPagination = _g[1];
    var _h = useState(false), loading = _h[0], setLoading = _h[1];
    var _i = useState(''), error = _i[0], setError = _i[1];
    var _j = useState({ produtos:0, locais:0, baixos:0, zerados:0 }), resumo = _j[0], setResumo = _j[1];
    var _k = useState(function(){ try{ var p = localStorage.getItem('per_page_estoque'); return p? String(p) : '20'; } catch(_){ return '20'; } }), perPage = _k[0], setPerPage = _k[1];
    useEffect(function(){
      var run = async function(){
        try { var locs = await window.fetchJson('/api/hierarquia/locais'); if (Array.isArray(locs)) setLocais(locs); } catch(_){ }
      }; run();
    }, []);
    function buildParams(page){
      var params = new URLSearchParams();
      params.set('page', String(page||pagination.page||1));
      params.set('per_page', String(perPage||20));
      if (filtroProduto) params.set('produto', filtroProduto);
      if (filtroTipo) params.set('tipo', filtroTipo);
      if (filtroStatus) params.set('status', filtroStatus);
      if (filtroLocal) params.set('local', filtroLocal);
      return params;
    }
    function fmtInt(n){ return Number(n||0).toLocaleString('pt-BR',{maximumFractionDigits:0}); }
    async function load(page, append){
      setLoading(true); setError('');
      try {
        var resp = await window.fetchJson('/api/estoque/hierarquia?'+buildParams(page).toString());
        var estoque = Array.isArray(resp.items)? resp.items : (Array.isArray(resp)? resp : []);
        var pag = resp.pagination || { page:(page||1), pages:1, total:estoque.length, per_page: pagination.per_page };
        if (append) { setItems(function(prev){ return (prev||[]).concat(estoque); }); } else { setItems(estoque); }
        setPagination(pag);
        var base = append ? (items||[]).concat(estoque) : estoque;
        var produtosSet = new Set(base.map(function(it){return it.produto_id;}));
        var locaisSet = new Set(base.map(function(it){return it.local_id;}));
        var baixos = 0, zerados = 0;
        for (var i=0;i<base.length;i++){
          var it = base[i];
          var disp = parseFloat(it.quantidade_disponivel || 0);
          var inicial = parseFloat(it.quantidade_inicial || 0);
          if (disp<=0) zerados++; else if (disp <= Math.max(inicial*0.1, 5)) baixos++;
        }
        setResumo({ produtos: produtosSet.size, locais: locaisSet.size, baixos: baixos, zerados: zerados });
      } catch(e){ setError(String(e && e.message || 'Erro ao carregar dados')); setItems([]); }
      setLoading(false);
    }
    useEffect(function(){ var t = setTimeout(function(){ setItems([]); load(1, false); }, 200); return function(){ clearTimeout(t); }; }, [filtroProduto, filtroTipo, filtroStatus, filtroLocal, perPage]);
    function onExport(){ var p = buildParams(1); window.open('/api/estoque/hierarquia/export?'+p.toString(), '_blank'); }
    
    function renderChips(){
      var chips = [];
      if (filtroProduto) chips.push(h('span',{className:'badge bg-primary me-2'}, ['Produto: ', filtroProduto]));
      if (filtroTipo) chips.push(h('span',{className:'badge bg-info text-dark me-2'}, ['Tipo: ', filtroTipo]));
      if (filtroStatus) chips.push(h('span',{className:'badge bg-warning text-dark me-2'}, ['Status: ', filtroStatus]));
      if (filtroLocal) chips.push(h('span',{className:'badge bg-secondary me-2'}, ['Local: ', filtroLocal]));
      return chips.length? h('div',{className:'d-flex flex-wrap align-items-center mb-2'}, chips) : null;
    }
    function agruparPorProduto(list){
      var mapa = {};
      for (var i=0;i<list.length;i++){
        var it = list[i];
        var pid = it.produto_id; if (!pid) continue;
        var tipo = String(it.local_tipo||'').toLowerCase();
        var qtd = parseFloat(it.quantidade||0);
        var disp = parseFloat(it.quantidade_disponivel||0);
        var inicial = parseFloat(it.quantidade_inicial||0);
        var dt = it.data_atualizacao? new Date(it.data_atualizacao) : null;
        if (!mapa[pid]) mapa[pid] = { produto_id: pid, produto_nome: it.produto_nome, produto_codigo: it.produto_codigo, unidade_medida: it.unidade_medida||'', totais:{ alm:0, sub:0, set:0, cen:0 }, disponivel:0, inicial:0, ultima:null };
        var p = mapa[pid];
        if (tipo==='almoxarifado') p.totais.alm += qtd; else if (tipo==='subalmoxarifado') p.totais.sub += qtd; else if (tipo==='setor') p.totais.set += qtd; else if (tipo==='central') p.totais.cen += qtd; else p.totais.alm += qtd;
        p.disponivel += disp; p.inicial += inicial; if (dt && (!p.ultima || dt>p.ultima)) p.ultima = dt;
      }
      return Object.values(mapa);
    }
    var linhas = agruparPorProduto(items);
    return h('div',{className:'row'},[
      h('div',{className:'col-12'},[
        h('div',{className:'d-flex justify-content-between align-items-center mb-3'},[
          h('h2',null,[h('i',{className:'fas fa-sitemap me-2'}),'Estoque por Hierarquia']),
          h('div',null,[
            h('button',{className:'btn btn-outline-primary me-2', onClick:function(){ setItems([]); load(1, false); }}, [h('i',{className:'fas fa-sync-alt'}),' Atualizar']),
            h('a',{href:'/produtos', className:'btn btn-outline-secondary'}, [h('i',{className:'fas fa-arrow-left'}),' Voltar'])
          ])
        ]),
        h('div',{className:'card mb-3'}, h('div',{className:'card-body'},[
          h('div',{className:'row g-3'},[
            h('div',{className:'col-md-3'},[
              h('label',{className:'form-label'},'Produto'),
              h('input',{type:'text', className:'form-control', value:filtroProduto, onChange:function(e){ setFiltroProduto(e.target.value); }, placeholder:'Buscar por código ou nome...'})
            ]),
            h('div',{className:'col-md-2'},[
              h('label',{className:'form-label'},'Tipo de Local'),
              h('select',{className:'form-select', value:filtroTipo, onChange:function(e){ setFiltroTipo(e.target.value); }},[
                h('option',{value:''},'Todos'),
                h('option',{value:'central'},'Central'),
                h('option',{value:'almoxarifado'},'Almoxarifado'),
                h('option',{value:'subalmoxarifado'},'Sub-almoxarifado'),
                h('option',{value:'setor'},'Setor')
              ])
            ]),
            h('div',{className:'col-md-2'},[
              h('label',{className:'form-label'},'Status'),
              h('select',{className:'form-select', value:filtroStatus, onChange:function(e){ setFiltroStatus(e.target.value); }},[
                h('option',{value:''},'Todos'),
                h('option',{value:'disponivel'},'Disponível'),
                h('option',{value:'baixo'},'Estoque Baixo'),
                h('option',{value:'zerado'},'Zerado')
              ])
            ]),
            h('div',{className:'col-md-3'},[
              h('label',{className:'form-label'},'Local'),
              h('select',{className:'form-select', value:filtroLocal, onChange:function(e){ setFiltroLocal(e.target.value); }}, (function(){
                var opts = [h('option',{value:''},'Todos os locais')];
                var grupos = { central:[], almoxarifado:[], subalmoxarifado:[], setor:[] };
                for (var i=0;i<locais.length;i++){ var l = locais[i]; if (grupos[l.tipo]) grupos[l.tipo].push(l); }
                var keys = Object.keys(grupos);
                for (var k=0;k<keys.length;k++){
                  var tipo = keys[k]; var arr = grupos[tipo]; if (!arr.length) continue;
                  opts.push(h('optgroup',{label: tipo.charAt(0).toUpperCase()+tipo.slice(1)}, arr.map(function(l){ return h('option',{value:String(l.id)}, l.nome); })));
                }
                return opts;
              })())
            ]),
            h('div',{className:'col-md-2 d-flex align-items-end'}, h('div',{className:'d-grid w-100'}, h('button',{className:'btn btn-primary', onClick:function(){ setItems([]); load(1, false); }}, [h('i',{className:'fas fa-filter'}),' Filtrar'])))
          ])
        ])),
        renderChips(),
        h('div',{className:'row g-3 mb-3'},[
          h('div',{className:'col-md-3'}, h('div',{className:'card bg-primary text-white'}, h('div',{className:'card-body text-center'},[h('h3',null,String(resumo.produtos||0)), h('p',{className:'mb-0'},'Produtos Diferentes')]))),
          h('div',{className:'col-md-3'}, h('div',{className:'card bg-success text-white'}, h('div',{className:'card-body text-center'},[h('h3',null,String(resumo.locais||0)), h('p',{className:'mb-0'},'Locais com Estoque')]))),
          h('div',{className:'col-md-3'}, h('div',{className:'card bg-warning text-white'}, h('div',{className:'card-body text-center'},[h('h3',null,String(resumo.baixos||0)), h('p',{className:'mb-0'},'Estoques Baixos')]))),
          h('div',{className:'col-md-3'}, h('div',{className:'card bg-danger text-white'}, h('div',{className:'card-body text-center'},[h('h3',null,String(resumo.zerados||0)), h('p',{className:'mb-0'},'Estoques Zerados')])))
        ]),
        h('div',{className:'card'},[
          h('div',{className:'card-header d-flex justify-content-between align-items-center'},[
            h('h5',{className:'mb-0'},[h('i',{className:'fas fa-table me-2'}),'Estoque Detalhado']),
            h('div',null, h('button',{className:'btn btn-sm btn-outline-success', onClick:onExport}, [h('i',{className:'fas fa-file-excel'}),' Exportar']))
          ]),
          h('div',{className:'card-body'},[
            h('div',{className:'d-flex justify-content-end mb-2'}, h('div',{className:'input-group', style:{maxWidth:'200px'}}, [ h('span',{className:'input-group-text'}, 'Itens'), h('select',{className:'form-select', value: perPage, onChange:function(e){ var v = String(e.target.value); setPerPage(v); try{ localStorage.setItem('per_page_estoque', v);}catch(_){ } setItems([]); load(1, false); }}, [ h('option',{value:'20'}, '20'), h('option',{value:'50'}, '50'), h('option',{value:'100'}, '100') ]) ])),
            loading? h('div',{className:'text-center py-4'}, h('i',{className:'fas fa-spinner fa-spin'})) : (error? h('div',{className:'alert alert-danger'}, error) : (function(){
              if (!linhas.length) return h('div',{className:'alert alert-info text-center'}, [h('i',{className:'fas fa-info-circle'}),' Nenhum item encontrado com os filtros aplicados']);
              return h('div',{className:'table-responsive'},[
                h('table',{className:'table table-hover'},[
                  h('thead',null,h('tr',null,[ h('th',null,'Produto'), h('th',null,'Totais por Hierarquia'), h('th',null,'Disponível'), h('th',null,'Status'), h('th',null,'Última Atualização'), h('th',null,'Ações') ])),
                  h('tbody',null, linhas.map(function(p, idx){
                    var badge = 'bg-success';
                    if (p.disponivel <= 0) badge = 'bg-danger'; else if (p.disponivel <= Math.max(p.inicial*0.1, 5)) badge = 'bg-warning';
                    var ultimaStr = p.ultima? p.ultima.toLocaleString('pt-BR') : '-';
                    return h('tr',{key:String(idx)},[
                      h('td',null,[ h('strong',null,p.produto_nome||'-'), h('br',null), h('small',{className:'text-muted'}, p.produto_codigo||'-') ]),
                      h('td',null,[
                        h('div',{className:'hier-line'},[h('span',{className:'text-success'},'Almox: '), h('span',{className:'hier-qty'}, fmtInt(p.totais.alm))]),
                        h('div',{className:'hier-line'},[h('span',{className:'text-info'},'Sub: '), h('span',{className:'hier-qty'}, fmtInt(p.totais.sub))]),
                        h('div',{className:'hier-line'},[h('span',{className:'text-warning'},'Setor: '), h('span',{className:'hier-qty'}, fmtInt(p.totais.set))])
                      ]),
                      h('td',null, h('span',{className:'disp-qty'}, fmtInt(p.disponivel))),
                      h('td',null, h('span',{className:'badge '+badge}, badge==='bg-danger'? 'Zerado' : (badge==='bg-warning'? 'Baixo' : 'Normal'))),
                      h('td',null, ultimaStr),
                      h('td',null, h('div',{className:'btn-group btn-group-sm'}, [ h('a',{href:'/produtos/'+encodeURIComponent(p.produto_id), className:'btn btn-outline-primary'}, [h('i',{className:'fas fa-eye'}),' Ver']) ]))
                    ]);
                  }))
                ])
              ]);
            })())
          ])
        ])
      ])
    ]);
  }
  function mountEstoque(){
    var rootEl = document.getElementById('estoque-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'estoque-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(EstoquePage));
  }
  window.PluckApp.mountEstoque = mountEstoque;
  function MovsPage(){
    var _a = useState([]), items = _a[0], setItems = _a[1];
    var _b = useState({ current_page:1, per_page: Number((function(){ try{ return localStorage.getItem('movs.per_page')||20; } catch(_){ return 20; } })()), total_pages:1, total:0 }), pagination = _b[0], setPagination = _b[1];
    var _c = useState(true), loading = _c[0], setLoading = _c[1];
    var _d = useState(''), error = _d[0], setError = _d[1];
    var _e = useState(''), tipo = _e[0], setTipo = _e[1];
    var _f = useState(''), produto = _f[0], setProduto = _f[1];
    var _g = useState(''), dataInicio = _g[0], setDataInicio = _g[1];
    var _h = useState(''), dataFim = _h[0], setDataFim = _h[1];
    var _i = useState('desc'), ordem = _i[0], setOrdem = _i[1];
    var _j = useState( (window.matchMedia && window.matchMedia('(max-width: 768px)').matches) ? true : false ), isMobile = _j[0], setIsMobile = _j[1];
    var _k = useState(false), showTransfer = _k[0], setShowTransfer = _k[1];
    var _m = useState(false), showSaida = _m[0], setShowSaida = _m[1];
    var _l = useState({ centrais:[], almox:[], subs:[], mapCentrais:{} }), locaisCache = _l[0], setLocaisCache = _l[1];
    useEffect(function(){ var mq = window.matchMedia? window.matchMedia('(max-width: 768px)') : null; var handler = function(e){ setIsMobile(!!(e && e.matches)); }; if (mq){ if (mq.addEventListener) mq.addEventListener('change', handler); else if (mq.addListener) mq.addListener(handler);} return function(){ if (mq){ if (mq.removeEventListener) mq.removeEventListener('change', handler); else if (mq.removeListener) mq.removeListener(handler);} }; },[]);
    function load(page){
      setLoading(true); setError('');
      var params = new URLSearchParams();
      if (tipo) params.set('tipo', tipo);
      if (produto) params.set('produto', produto);
      if (dataInicio) params.set('data_inicio', dataInicio);
      if (dataFim) params.set('data_fim', dataFim);
      params.set('page', String(page || (pagination.current_page||1)));
      params.set('per_page', String(pagination.per_page||20));
      params.set('ordem', ordem);
      window.fetchJson('/api/movimentacoes?' + params.toString())
        .then(function(data){
          setItems(Array.isArray(data.items)? data.items : []);
          var pg = data.pagination || {};
          setPagination({ current_page: Number(pg.current_page||1), per_page: Number(pg.per_page||pagination.per_page||20), total_pages: Number(pg.total_pages||1), total: Number(pg.total||0) });
          setLoading(false);
        })
        .catch(function(err){ setError(err && err.message? String(err.message) : 'Erro ao carregar'); setLoading(false); });
    }
    useEffect(function(){ load(1); },[]);
    useEffect(function(){
      try{
        var h = String(window.location.hash||'').toLowerCase();
        if (h==='#transferencia') setShowTransfer(true);
        else if (h==='#saida') setShowSaida(true);
        window.addEventListener('hashchange', function(){
          var hh = String(window.location.hash||'').toLowerCase();
          if (hh==='#transferencia') setShowTransfer(true); else if (hh==='#saida') setShowSaida(true);
        });
      }catch(_){ }
    },[]);
    useEffect(function(){ var t = setTimeout(function(){ load(1); }, 300); return function(){ clearTimeout(t); }; }, [tipo, produto, dataInicio, dataFim, ordem]);
    function onFiltrar(){ load(1); }
    function toggleOrdenacao(){ var novo = ordem==='desc'? 'asc' : 'desc'; setOrdem(novo); }
    function setPerPageUI(n){ var v = Number(n)||20; try{ localStorage.setItem('movs.per_page', String(v)); }catch(_){ } setPagination(function(p){ return Object.assign({}, p, { per_page: v }); }); load(1); }
    function goToPage(p){ var target = Math.max(1, Math.min(Number(p)||1, pagination.total_pages||1)); load(target); }
    function TipoCell(t){ var v = String(t||'').toLowerCase(); var icon = v==='entrada'? 'fas fa-arrow-down text-success' : ((v==='saida'||v==='distribuicao'||v==='distribuição')? 'fas fa-arrow-up text-danger' : (v==='transferencia'? 'fas fa-exchange-alt text-primary' : 'fas fa-question')); var label = v==='entrada'? 'Entrada' : ((v==='saida'||v==='distribuicao'||v==='distribuição')? 'Saída' : (v==='transferencia'? 'Transferência' : t)); return h('span', null, [ h('i',{className:icon}), ' ', label ]); }
    function LocCell(m){ var o = m.origem_nome||''; var d = m.destino_nome||''; var txt = (o&&d)? (o+' → '+d) : (o||d||'-'); return h('span', null, txt); }
    var filtros = h('div',{className:'card mb-3'}, h('div',{className:'card-body'}, h('div',{className:'row g-3'}, [
      h('div',{className:'col-md-3'}, [ h('label',{className:'form-label'},'Tipo'), h('select',{className:'form-select', value:tipo, onChange:function(e){ setTipo(e.target.value); }}, [ h('option',{value:''},'Todos'), h('option',{value:'ENTRADA'},'Entrada'), h('option',{value:'SAIDA'},'Saída'), h('option',{value:'TRANSFERENCIA'},'Transferência') ]) ]),
      h('div',{className:'col-md-3'}, [ h('label',{className:'form-label'},'Produto'), h('input',{className:'form-control', placeholder:'Nome ou código', value:produto, onChange:function(e){ setProduto(e.target.value); }}) ]),
      h('div',{className:'col-md-2'}, [ h('label',{className:'form-label'},'Data Início'), h('input',{type:'date', className:'form-control', value:dataInicio, onChange:function(e){ setDataInicio(e.target.value); }}) ]),
      h('div',{className:'col-md-2'}, [ h('label',{className:'form-label'},'Data Fim'), h('input',{type:'date', className:'form-control', value:dataFim, onChange:function(e){ setDataFim(e.target.value); }}) ]),
      h('div',{className:'col-md-2 d-flex align-items-end'}, h('div',{className:'d-flex w-100 gap-2'}, [ h('button',{type:'button', className:'btn btn-primary flex-fill', onClick:onFiltrar}, [h('i',{className:'fas fa-search'}),' ','Filtrar']), h('button',{type:'button', className:'btn btn-outline-secondary', onClick:function(){ setTipo(''); setProduto(''); setDataInicio(''); setDataFim(''); setTimeout(function(){ load(1); },0); }}, [h('i',{className:'fas fa-times'}),' ','Limpar']) ]))
    ])));
    var chipsWrap = (function(){ var chips=[]; if(tipo) chips.push(h('span',{className:'badge bg-primary me-2'}, ['Tipo: ', tipo])); if(produto) chips.push(h('span',{className:'badge bg-secondary me-2'}, ['Produto: ', produto])); if(dataInicio) chips.push(h('span',{className:'badge bg-info me-2'}, ['Início: ', dataInicio])); if(dataFim) chips.push(h('span',{className:'badge bg-info me-2'}, ['Fim: ', dataFim])); return chips.length? h('div',{className:'px-3 pb-3'}, h('div',{className:'d-flex flex-wrap align-items-center'}, chips)) : null; })();
    function openNovaTransferencia(){ setShowTransfer(true); }
    function openDistribuicao(){ setShowSaida(true); }
    var header = h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [
      h('h2',null,[h('i',{className:'fas fa-exchange-alt'}),' ','Movimentações']),
      h('div',null,[
        h('button',{type:'button', className:'btn btn-primary me-2', onClick:openNovaTransferencia}, [h('i',{className:'fas fa-plus'}),' ','Nova Transferência']),
        h('button',{type:'button', className:'btn btn-success me-3', onClick:openDistribuicao}, [h('i',{className:'fas fa-arrow-up'}),' ','Saída']),
        h('div',{className:'btn-group'}, [
          h('button',{className:'btn btn-outline-secondary btn-sm', onClick:function(){ setPerPageUI(10); }},'10'),
          h('button',{className:'btn btn-outline-secondary btn-sm', onClick:function(){ setPerPageUI(20); }},'20'),
          h('button',{className:'btn btn-outline-secondary btn-sm', onClick:function(){ setPerPageUI(50); }},'50')
        ])
      ])
    ]);
    var ordenacaoBtn = h('div',{className:'d-flex justify-content-end mb-2'}, h('button',{type:'button', className:(ordem==='desc'? 'btn btn-outline-secondary btn-sm' : 'btn btn-outline-primary btn-sm'), onClick:toggleOrdenacao, title:(ordem==='desc'? 'Mostrar mais antigas primeiro' : 'Mostrar mais recentes primeiro')}, [ h('i',{className:(ordem==='desc'? 'fas fa-sort-amount-down' : 'fas fa-sort-amount-up')}),' ', (ordem==='desc'? 'Mais recentes primeiro' : 'Mais antigas primeiro') ]));

  function TransferModal(props){
      var _a = useState(''), q = _a[0], setQ = _a[1];
      var _b = useState([]), sugest = _b[0], setSugest = _b[1];
      var _c = useState(null), prodSel = _c[0], setProdSel = _c[1];
      var _d = useState([]), origemOpts = _d[0], setOrigemOpts = _d[1];
      var _e = useState(null), origemSel = _e[0], setOrigemSel = _e[1];
      var _f = useState(''), motivo = _f[0], setMotivo = _f[1];
      var _g = useState(''), obs = _g[0], setObs = _g[1];
      var _h = useState('sub_almoxarifado'), destTipo = _h[0], setDestTipo = _h[1];
      var _i = useState(''), destCentral = _i[0], setDestCentral = _i[1];
      var _j = useState(''), destLocal = _j[0], setDestLocal = _j[1];
      var _k = useState(false), submitting = _k[0], setSubmitting = _k[1];
      var _l = useState(''), submitErr = _l[0], setSubmitErr = _l[1];
      var _m = useState(false), sugestLoading = _m[0], setSugestLoading = _m[1];
      var _n = useState(-1), sugestActive = _n[0], setSugestActive = _n[1];
      var modalId = 'reactTransferModal';
      var modalInst = useRef(null);
      var lastOpen = useRef(false);
      var lastActionTs = useRef(0);

      useEffect(function(){
        var t = setTimeout(function(){ if (!q) { setSugest([]); setSugestLoading(false); setSugestActive(-1); return; } setSugestLoading(true); setSugestActive(-1); window.fetchJson('/api/produtos?search='+encodeURIComponent(q)+'&per_page=20').then(function(d){ setSugest(Array.isArray(d.items)? d.items : []); setSugestLoading(false); }).catch(function(){ setSugest([]); setSugestLoading(false); }); }, 250);
        return function(){ clearTimeout(t); };
      }, [q]);
      useEffect(function(){ if (!prodSel) { setOrigemOpts([]); setOrigemSel(null); return; } window.fetchJson('/api/produtos/'+prodSel.id+'/estoque').then(function(d){ var itens = Array.isArray(d.estoques)? d.estoques : []; var rows = itens.map(function(it){ return { tipo:String(it.tipo).toLowerCase(), id:String(it.local_id), nome:it.nome_local, disp:Number(it.quantidade_disponivel||it.quantidade||0) }; }).filter(function(row){ return row.disp>0 && row.tipo!=='setor'; }); setOrigemOpts(rows); }).catch(function(){ setOrigemOpts([]); }); }, [prodSel]);
      useEffect(function(){ (async function(){ if ((locaisCache.centrais||[]).length) return; var c = []; var a = []; var s = []; var mapC = {}; try{ var dc = await window.fetchJson('/api/centrais?per_page=1000'); c = Array.isArray(dc.items)? dc.items : []; }catch(_){ } try{ var da = await window.fetchJson('/api/almoxarifados?per_page=1000'); a = Array.isArray(da.items)? da.items : []; }catch(_){ } try{ var ds = await window.fetchJson('/api/sub-almoxarifados?per_page=1000'); s = Array.isArray(ds.items)? ds.items : []; }catch(_){ } for (var i=0;i<c.length;i++){ var it=c[i]; mapC[String(it.id||it._id||it.codigo||i)] = it.nome||it.descricao||String(it.id||it._id||''); } setLocaisCache({ centrais:c, almox:a, subs:s, mapCentrais:mapC }); })(); }, []);
      useEffect(function(){
        try{
          var el = document.getElementById(modalId); if (!el) return;
          var m = bootstrap.Modal.getOrCreateInstance(el, { backdrop:true, keyboard:true });
          if (!modalInst.current) modalInst.current = m;
          var now = Date.now();
          if (props.open !== lastOpen.current && (now - lastActionTs.current) > 300){
            lastActionTs.current = now;
            if (props.open){ m.show(); }
            else { m.hide(); }
            lastOpen.current = props.open;
          }
          try {
            var bds = document.querySelectorAll('.modal-backdrop');
            if (bds.length > 1) { for (var i=1;i<bds.length;i++){ bds[i].remove(); } }
            var anyShown = document.querySelectorAll('.modal.show').length > 0;
            if (!anyShown){ document.body.classList.remove('modal-open'); document.body.style.paddingRight=''; }
          } catch(_){ }
        } catch(_){ }
      }, [props.open]);

      useEffect(function(){
        try{
          var el = document.getElementById(modalId); if (!el) return;
          var onHidden = function(){ try{ setShowTransfer(false); }catch(_){} try { lastOpen.current = false; } catch(_){} try { var inst = bootstrap.Modal.getInstance(el); if (inst && inst.hide) inst.hide(); if (inst && inst.dispose) inst.dispose(); modalInst.current = null; } catch(_){ } try { document.querySelectorAll('.modal-backdrop').forEach(function(n){ n.remove(); }); } catch(_){} try { document.body.classList.remove('modal-open'); } catch(_){} try { document.body.style.paddingRight=''; } catch(_){} if (props.onClose) try{ props.onClose(); }catch(_){} };
          var onShown = function(){ try{ var inp = document.getElementById('produtoBuscaReact'); if (inp) inp.focus(); }catch(_){} try{ var bds = document.querySelectorAll('.modal-backdrop'); if (bds.length > 1) { for (var i=1;i<bds.length;i++){ bds[i].remove(); } } }catch(_){} };
          el.addEventListener('hidden.bs.modal', onHidden);
          el.addEventListener('shown.bs.modal', onShown);
          return function(){ try{ el.removeEventListener('hidden.bs.modal', onHidden); el.removeEventListener('shown.bs.modal', onShown); } catch(_){} };
        } catch(_){ }
      }, []);
      useEffect(function(){ if (props.open){ setQ(''); setSugest([]); setProdSel(null); setOrigemOpts([]); setOrigemSel(null); setMotivo(''); setObs(''); setDestTipo('sub_almoxarifado'); setDestCentral(''); setDestLocal(''); setSubmitting(false); setSubmitErr(''); } }, [props.open]);

      var destCentraisOpts = (locaisCache.centrais||[]).map(function(c){ return h('option',{value:String(c.id||c._id||c.codigo||'')}, (c.nome||c.descricao||String(c.id||c._id||''))); });
      var destLocaisOpts = (function(){ if (destTipo==='central'){ var listC = (locaisCache.centrais||[]); return listC.map(function(c){ return h('option',{value:String(c.id||c._id||c.codigo||'')}, (c.nome||c.descricao||String(c.id||c._id||''))); }); } var list = destTipo==='almoxarifado'? (locaisCache.almox||[]) : (locaisCache.subs||[]); var filtered = list.filter(function(x){ return destCentral? String(x.central_id)===String(destCentral) : true; }); return filtered.map(function(x){ var cn = locaisCache.mapCentrais[String(x.central_id)] || String(x.central_id||''); var label = (x.nome||x.descricao||('-')) + ' • C'+cn; return h('option',{value:String(x.id||x._id||'')}, label); }); })();

      function onSubmit(){ if (!prodSel || !origemSel || !destLocal) return; var quantidade = parseFloat((document.getElementById('quantTransferenciaReact')||{}).value || '0'); if (!(quantidade>0)) return; setSubmitting(true); setSubmitErr(''); var payload = { produto_id: String(prodSel.id||prodSel._id||''), quantidade: quantidade, motivo: motivo||null, observacoes: obs||null, origem: { tipo: String(origemSel.tipo), id: String(origemSel.id) }, destino: { tipo: String(destTipo), id: String(destLocal) } }; window.fetchJson('/api/movimentacoes/transferencia', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) }).then(function(){ setSubmitting(false); setShowTransfer(false); load(1); }).catch(function(err){ setSubmitting(false); var msg = (err && err.message)? String(err.message) : 'Falha ao executar transferência'; setSubmitErr(msg); }); }

      var modal = h('div',{id:modalId, className:'modal', tabIndex:-1, 'data-bs-backdrop':'static', 'data-bs-keyboard':'false'}, h('div',{className:'modal-dialog modal-xl'}, h('div',{className:'modal-content'}, [
        h('div',{className:'modal-header'}, [ h('h5',{className:'modal-title'}, 'Nova Transferência'), h('button',{type:'button', className:'btn-close', onClick:function(){ try{ var el = document.getElementById(modalId); if (!el) return; bootstrap.Modal.getOrCreateInstance(el).hide(); }catch(_){ } setShowTransfer(false); }}) ]),
        h('div',{className:'modal-body'}, [
          h('div',{className:'row g-3'}, [
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-search'}),' Selecionar Produto' ]), h('div',{className:'card-body'}, [ h('input',{id:'produtoBuscaReact', type:'text', className:'form-control mb-2', placeholder:'Buscar produto por nome ou código...', value:q, onChange:function(e){ setQ(e.target.value); }, onKeyDown:function(e){ var len = (sugest||[]).length; if (e.key==='ArrowDown'){ e.preventDefault(); setSugestActive(function(idx){ var n = idx+1; return (n>=len? len-1 : n); }); } else if (e.key==='ArrowUp'){ e.preventDefault(); setSugestActive(function(idx){ var n = idx-1; return (n<0? 0 : n); }); } else if (e.key==='Enter'){ if (len>0){ var i = sugestActive>=0? sugestActive : 0; var p = sugest[i]; if (p){ setProdSel(p); setSugest([]); setQ(p.nome||p.codigo||''); } } } else if (e.key==='Escape'){ setSugest([]); } }}), h('div',{className:'list-group', style:{maxHeight:'280px', overflowY:'auto'}}, [].concat((sugestLoading? [h('div',{className:'list-group-item disabled'}, 'Carregando...')] : [])).concat((sugest||[]).map(function(p,idx){ return h('button',{type:'button', className:'list-group-item list-group-item-action '+(idx===sugestActive?'active':''), onClick:function(){ setProdSel(p); }, key:String(p.id||p._id||p.codigo||Math.random())}, [ h('div',{className:'fw-bold'}, p.nome), h('small',{className:'text-muted ms-2'}, p.codigo) ]); }))) ]) ]) ]),
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-boxes'}),' Origem' ]), h('div',{className:'card-body'}, [ h('div',{className:'list-group', style:{maxHeight:'280px', overflowY:'auto'}}, (origemOpts||[]).map(function(o){ return h('button',{type:'button', className:'list-group-item list-group-item-action '+(origemSel && String(origemSel.tipo)==String(o.tipo) && String(origemSel.id)==String(o.id)? 'active':''), onClick:function(){ setOrigemSel(o); }, key:o.tipo+'-'+o.id}, [ h('div',{className:'d-flex justify-content-between align-items-center'}, [ h('div',null, (o.nome||'-') + ' • '+o.tipo ), h('div',null, ['Disp: ', h('strong',null, String(o.disp)) ]) ]) ]); })) ]) ]) ])
          ]),
          h('hr'),
          (function(){
            var stockByTipo = {}; (origemOpts||[]).forEach(function(o){ var t=String(o.tipo); var id=String(o.id); if(!stockByTipo[t]) stockByTipo[t]=new Set(); stockByTipo[t].add(id); });
            var tipoBtns = h('div',{className:'col-md-3'}, [ h('label',{className:'form-label'}, 'Tipo de Destino'), h('div',null, [ h('button',{type:'button', className:'btn w-100 mb-2 '+(destTipo==='sub_almoxarifado'?'btn-primary':'btn-outline-primary'), onClick:function(){ setDestTipo('sub_almoxarifado'); setDestLocal(''); }}, 'Sub‑Almoxarifado'), h('button',{type:'button', className:'btn w-100 mb-2 '+(destTipo==='almoxarifado'?'btn-primary':'btn-outline-primary'), onClick:function(){ setDestTipo('almoxarifado'); setDestLocal(''); }}, 'Almoxarifado') ]) ]);
            var centraisChips = (locaisCache.centrais||[]).map(function(c){ var id = String(c.id||c._id||c.codigo||''); var act = String(destCentral)===id; return h('button',{type:'button', className:'btn btn-sm '+(act?'btn-primary':'btn-outline-primary')+' me-2 mb-2', onClick:function(){ setDestCentral(id); setDestLocal(''); }}, (c.nome||c.descricao||id)); });
            var list = destTipo==='almoxarifado'? (locaisCache.almox||[]) : (locaisCache.subs||[]);
            var filtered = list.filter(function(x){ return destCentral? String(x.central_id)===String(destCentral) : true; });
            var locItems = h('div',{className:'list-group', style:{maxHeight:'220px', overflowY:'auto'}}, filtered.map(function(x){ var id = String(x.id||x._id||''); var act = String(destLocal)===id; var has = !!(stockByTipo[destTipo] && stockByTipo[destTipo].has(id)); var cn = locaisCache.mapCentrais[String(x.central_id)] || String(x.central_id||''); var label = (x.nome||x.descricao||('-')) + ' • C'+cn; return h('button',{type:'button', className:'list-group-item list-group-item-action '+(act?'active':''), onClick:function(){ setDestLocal(id); }}, [ h('div',{className:'d-flex justify-content-between align-items-center'}, [ h('div',null, label), (has? h('span',{className:'badge bg-success'}, 'Estoque') : null) ]) ]); }));
            return h('div',{className:'row g-3'}, [ tipoBtns, h('div',{className:'col-md-4'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-building'}),' Central do Destino' ]), h('div',{className:'card-body'}, h('div',{className:'d-flex flex-wrap'}, centraisChips)) ]) ]), h('div',{className:'col-md-5'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-map-marker-alt'}),' Local de Destino' ]), h('div',{className:'card-body'}, h('div',{className:'list-group', style:{maxHeight:'300px', overflowY:'auto'}}, locItems.props.children)) ]) ]) ]);
          })(),
          h('div',{className:'row mt-3'}, [
            h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'}, 'Quantidade *'), h('input',{type:'number', className:'form-control', id:'quantTransferenciaReact', min:'0.001', step:'0.001'}) ]),
            h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'}, 'Motivo'), h('input',{type:'text', className:'form-control', value:motivo, onChange:function(e){ setMotivo(e.target.value); }}) ]),
            h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'}, 'Observações'), h('input',{type:'text', className:'form-control', value:obs, onChange:function(e){ setObs(e.target.value); }}) ])
          ])
          , (submitErr? h('div',{className:'alert alert-danger mt-3'}, submitErr) : null)
        ]),
        h('div',{className:'modal-footer'}, [ h('button',{type:'button', className:'btn btn-secondary', onClick:function(){ try{ var el = document.getElementById(modalId); if (!el) return; bootstrap.Modal.getOrCreateInstance(el).hide(); }catch(_){ } setShowTransfer(false); }}, 'Cancelar'), h('button',{type:'button', className:'btn btn-primary', disabled:submitting || !prodSel || !origemSel || !destLocal, onClick:onSubmit}, [ h('i',{className:'fas fa-exchange-alt'}), ' ', (submitting? 'Enviando...' : 'Executar Transferência') ]) ])
      ])));
      return modal;
    }
    function SaidaModal(props){
      var _a = useState(''), q = _a[0], setQ = _a[1];
      var _b = useState([]), sugest = _b[0], setSugest = _b[1];
      var _c = useState(null), prodSel = _c[0], setProdSel = _c[1];
      var _d = useState([]), origemOpts = _d[0], setOrigemOpts = _d[1];
      var _e = useState(null), origemSel = _e[0], setOrigemSel = _e[1];
      var _f = useState([]), setores = _f[0], setSetores = _f[1];
      var _g = useState(''), filtroSetor = _g[0], setFiltroSetor = _g[1];
      var _h = useState([]), destinosSel = _h[0], setDestinosSel = _h[1];
      var _i = useState(''), motivo = _i[0], setMotivo = _i[1];
      var _j = useState(''), obs = _j[0], setObs = _j[1];
      var _k2 = useState(false), submitting = _k2[0], setSubmitting = _k2[1];
      var _k3 = useState(''), submitErr = _k3[0], setSubmitErr = _k3[1];
      var _k4 = useState(false), sugestLoading = _k4[0], setSugestLoading = _k4[1];
      var _k5 = useState(-1), sugestActive = _k5[0], setSugestActive = _k5[1];
      var modalId = 'reactSaidaModal';
      var modalInst = useRef(null);
      var lastOpen = useRef(false);
      var lastActionTs = useRef(0);

      useEffect(function(){
        var t = setTimeout(function(){ if (!q) { setSugest([]); setSugestLoading(false); setSugestActive(-1); return; } setSugestLoading(true); setSugestActive(-1); window.fetchJson('/api/produtos?search='+encodeURIComponent(q)+'&per_page=20').then(function(d){ setSugest(Array.isArray(d.items)? d.items : []); setSugestLoading(false); }).catch(function(){ setSugest([]); setSugestLoading(false); }); }, 250);
        return function(){ clearTimeout(t); };
      }, [q]);
      useEffect(function(){ if (!prodSel) { setOrigemOpts([]); setOrigemSel(null); return; } window.fetchJson('/api/produtos/'+prodSel.id+'/estoque').then(function(d){ var itens = Array.isArray(d.estoques)? d.estoques : []; var rows = itens.map(function(it){ return { tipo:String(it.tipo).toLowerCase(), id:String(it.local_id), nome:it.nome_local, disp:Number(it.quantidade_disponivel||it.quantidade||0) }; }).filter(function(row){ return row.disp>0 && row.tipo!=='setor'; }); setOrigemOpts(rows); }).catch(function(){ setOrigemOpts([]); }); }, [prodSel]);
      useEffect(function(){ (async function(){ try{ var data = await window.fetchJson('/api/setores?per_page=1000'); setSetores(Array.isArray(data.items)? data.items : []); }catch(_){ setSetores([]); } })(); }, []);

      useEffect(function(){
        try{
          var el = document.getElementById(modalId); if (!el) return;
          var m = bootstrap.Modal.getOrCreateInstance(el, { backdrop:true, keyboard:true });
          if (!modalInst.current) modalInst.current = m;
          var now = Date.now();
          if (props.open !== lastOpen.current && (now - lastActionTs.current) > 300){
            lastActionTs.current = now;
            if (props.open){ m.show(); }
            else { m.hide(); }
            lastOpen.current = props.open;
          }
          try {
            var bds = document.querySelectorAll('.modal-backdrop');
            if (bds.length > 1) { for (var i=1;i<bds.length;i++){ bds[i].remove(); } }
            var anyShown = document.querySelectorAll('.modal.show').length > 0;
            if (!anyShown){ document.body.classList.remove('modal-open'); document.body.style.paddingRight=''; }
          } catch(_){ }
        } catch(_){ }
      }, [props.open]);

      useEffect(function(){
        try{
          var el = document.getElementById(modalId); if (!el) return;
          var onHidden = function(){ try{ setShowSaida(false); }catch(_){} try { lastOpen.current = false; } catch(_){} try { var inst = bootstrap.Modal.getInstance(el); if (inst && inst.hide) inst.hide(); if (inst && inst.dispose) inst.dispose(); modalInst.current = null; } catch(_){ } try { document.querySelectorAll('.modal-backdrop').forEach(function(n){ n.remove(); }); } catch(_){ } try { document.body.classList.remove('modal-open'); } catch(_){ } try { document.body.style.paddingRight=''; } catch(_){ } if (props.onClose) try{ props.onClose(); }catch(_){} };
          var onShown = function(){ try{ var inp = document.getElementById('produtoBuscaSaidaReact'); if (inp) inp.focus(); }catch(_){} try{ var bds = document.querySelectorAll('.modal-backdrop'); if (bds.length > 1) { for (var i=1;i<bds.length;i++){ bds[i].remove(); } } }catch(_){ } };
          el.addEventListener('hidden.bs.modal', onHidden);
          el.addEventListener('shown.bs.modal', onShown);
          return function(){ try{ el.removeEventListener('hidden.bs.modal', onHidden); el.removeEventListener('shown.bs.modal', onShown); } catch(_){ } };
        } catch(_){ }
      }, []);

      useEffect(function(){ if (props.open){ setQ(''); setSugest([]); setProdSel(null); setOrigemOpts([]); setOrigemSel(null); setFiltroSetor(''); setDestinosSel([]); setMotivo(''); setObs(''); setSubmitting(false); setSubmitErr(''); } }, [props.open]);

      function addDestino(s){ var id = String(s.id||s._id||''); setDestinosSel(function(list){ if (list.some(function(d){ return String(d.id)===id; })) return list; return list.concat([{ id:id, nome:(s.nome||s.descricao||id), quantidade: 0 }]); }); }
      function removeDestino(id){ setDestinosSel(function(list){ return list.filter(function(d){ return String(d.id)!==String(id); }); }); }
      function updateQuantidade(id, val){ var v = parseFloat(val||'0'); if (!isFinite(v) || v<0) v=0; setDestinosSel(function(list){ return list.map(function(d){ return String(d.id)===String(id)? Object.assign({}, d, { quantidade: v }) : d; }); }); }

      function onSubmit(){ if (!prodSel || !origemSel || !destinosSel.length) return; var dests = destinosSel.filter(function(d){ return d.quantidade>0; }).map(function(d){ return { id: String(d.id), quantidade: Number(d.quantidade) }; }); if (!dests.length) return; setSubmitting(true); setSubmitErr(''); var payload = { produto_id: String(prodSel.id||prodSel._id||''), origem: { tipo: String(origemSel.tipo), id: String(origemSel.id) }, destinos: dests, motivo: motivo||null, observacoes: obs||null }; window.fetchJson('/api/movimentacoes/distribuicao', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) }).then(function(){ setSubmitting(false); setShowSaida(false); load(1); }).catch(function(err){ setSubmitting(false); var msg = (err && err.message)? String(err.message) : 'Falha ao executar distribuição'; setSubmitErr(msg); }); }

      var modal = h('div',{id:modalId, className:'modal', tabIndex:-1, 'data-bs-backdrop':'static', 'data-bs-keyboard':'false'}, h('div',{className:'modal-dialog modal-xl'}, h('div',{className:'modal-content'}, [
        h('div',{className:'modal-header'}, [ h('h5',{className:'modal-title'}, 'Saída para Setores'), h('button',{type:'button', className:'btn-close', onClick:function(){ try{ var el = document.getElementById(modalId); if (!el) return; bootstrap.Modal.getOrCreateInstance(el).hide(); }catch(_){ } setShowSaida(false); }}) ]),
        h('div',{className:'modal-body'}, [
          h('div',{className:'row g-3'}, [
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-search'}),' Selecionar Produto' ]), h('div',{className:'card-body'}, [ h('input',{id:'produtoBuscaSaidaReact', type:'text', className:'form-control mb-2', placeholder:'Buscar produto por nome ou código...', value:q, onChange:function(e){ setQ(e.target.value); }, onKeyDown:function(e){ var len = (sugest||[]).length; if (e.key==='ArrowDown'){ e.preventDefault(); setSugestActive(function(idx){ var n = idx+1; return (n>=len? len-1 : n); }); } else if (e.key==='ArrowUp'){ e.preventDefault(); setSugestActive(function(idx){ var n = idx-1; return (n<0? 0 : n); }); } else if (e.key==='Enter'){ if (len>0){ var i = sugestActive>=0? sugestActive : 0; var p = sugest[i]; if (p){ setProdSel(p); setSugest([]); setQ(p.nome||p.codigo||''); } } } else if (e.key==='Escape'){ setSugest([]); } }}), h('div',{className:'list-group', style:{maxHeight:'280px', overflowY:'auto'}}, [].concat((sugestLoading? [h('div',{className:'list-group-item disabled'}, 'Carregando...')] : [])).concat((sugest||[]).map(function(p,idx){ return h('button',{type:'button', className:'list-group-item list-group-item-action '+(idx===sugestActive?'active':''), onClick:function(){ setProdSel(p); }, key:String(p.id||p._id||p.codigo||Math.random())}, [ h('div',{className:'fw-bold'}, p.nome), h('small',{className:'text-muted ms-2'}, p.codigo) ]); }))) ]) ]) ]),
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-boxes'}),' Origem' ]), h('div',{className:'card-body'}, [ h('div',{className:'list-group', style:{maxHeight:'280px', overflowY:'auto'}}, (origemOpts||[]).map(function(o){ return h('button',{type:'button', className:'list-group-item list-group-item-action '+(origemSel && String(origemSel.tipo)==String(o.tipo) && String(origemSel.id)==String(o.id)? 'active':''), onClick:function(){ setOrigemSel(o); }, key:o.tipo+'-'+o.id}, [ h('div',{className:'d-flex justify-content-between align-items-center'}, [ h('div',null, (o.nome||'-') + ' • '+o.tipo ), h('div',null, ['Disp: ', h('strong',null, String(o.disp)) ]) ]) ]); })) ]) ]) ])
          ]),
          h('hr'),
          h('div',{className:'row g-3'}, [
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('span',null,[h('i',{className:'fas fa-users'}),' Setores']), h('input',{type:'text', className:'form-control form-control-sm', placeholder:'Filtrar setores...', value:filtroSetor, onChange:function(e){ setFiltroSetor(e.target.value); }, style:{maxWidth:'240px'} }) ]), h('div',{className:'card-body'}, [ h('div',{className:'list-group', style:{maxHeight:'300px', overflowY:'auto'}}, (setores||[]).filter(function(s){ var t=String(filtroSetor||'').trim().toLowerCase(); if(!t) return true; var nm = String(s.nome||s.descricao||'').toLowerCase(); return nm.indexOf(t)>=0; }).map(function(s){ var id = String(s.id||s._id||''); var added = destinosSel.some(function(d){ return String(d.id)===id; }); return h('div',{className:'list-group-item d-flex justify-content-between align-items-center', key:id}, [ h('div',null, s.nome||s.descricao||id ), h('div',null, h('div',{className:'btn-group btn-group-sm'}, [ h('button',{className:'btn '+(added?'btn-secondary':'btn-outline-primary'), disabled:added, onClick:function(){ addDestino(s); }}, [h('i',{className:'fas fa-plus'}),' Adicionar']) ]) ) ]); })) ]) ]) ]),
            h('div',{className:'col-md-6'}, [ h('div',{className:'card h-100'}, [ h('div',{className:'card-header'}, [ h('i',{className:'fas fa-list'}),' Setores Selecionados' ]), h('div',{className:'card-body'}, [ (destinosSel.length? h('div',{className:'table-responsive'}, h('table',{className:'table table-sm'}, [ h('thead',null, h('tr',null,[ h('th',null,'Setor'), h('th',{className:'text-end'}, 'Quantidade'), h('th',null,'') ])), h('tbody',null, destinosSel.map(function(d){ return h('tr',{key:d.id}, [ h('td',null, d.nome||d.id ), h('td',{className:'text-end'}, h('input',{type:'number', className:'form-control form-control-sm', min:'0.001', step:'0.001', value:String(d.quantidade), onChange:function(e){ updateQuantidade(d.id, e.target.value); }})), h('td',null, h('button',{className:'btn btn-sm btn-outline-danger', onClick:function(){ removeDestino(d.id); }}, [h('i',{className:'fas fa-trash'}),' Remover']) ) ]); })) ]) ) : h('div',{className:'text-muted'}, 'Nenhum setor selecionado')) ]) ]) ])
          ]),
          h('div',{className:'row mt-3'}, [
            h('div',{className:'col-md-6'}, [ h('label',{className:'form-label'}, 'Motivo'), h('input',{type:'text', className:'form-control', value:motivo, onChange:function(e){ setMotivo(e.target.value); }}) ]),
            h('div',{className:'col-md-6'}, [ h('label',{className:'form-label'}, 'Observações'), h('input',{type:'text', className:'form-control', value:obs, onChange:function(e){ setObs(e.target.value); }}) ])
          ])
          , (submitErr? h('div',{className:'alert alert-danger mt-3'}, submitErr) : null)
        ]),
        h('div',{className:'modal-footer'}, [ h('button',{type:'button', className:'btn btn-secondary', onClick:function(){ try{ var el = document.getElementById(modalId); if (!el) return; bootstrap.Modal.getOrCreateInstance(el).hide(); }catch(_){ } setShowSaida(false); }}, 'Cancelar'), h('button',{type:'button', className:'btn btn-success', disabled:submitting || !prodSel || !origemSel || !destinosSel.length, onClick:onSubmit}, [ h('i',{className:'fas fa-arrow-up'}), ' ', (submitting? 'Enviando...' : 'Executar Saída') ]) ])
      ])));
      return modal;
    }
    var tableHead = h('thead',{className:'table-light'}, h('tr',null,[ h('th',null,'Data'), h('th',null,'Tipo'), h('th',null,'Produto'), h('th',null,'Quantidade'), h('th',null,'Local'), h('th',null,'Responsável'), h('th',null,'Motivo') ]));
    var rows = (items && items.length? items.map(function(m){ return h('tr',{key:(m.data_movimentacao+'-'+m.produto_codigo+'-'+m.usuario_responsavel)}, [ h('td',null,[ h('div',null,(new Date(m.data_movimentacao)).toLocaleDateString('pt-BR')), h('small',{className:'text-muted'}, (new Date(m.data_movimentacao)).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}) ) ]), h('td',null, TipoCell(m.tipo_movimentacao)), h('td',null,[ h('strong',null,m.produto_nome), h('br'), h('small',null,m.produto_codigo) ]), h('td',null, (parseFloat(m.quantidade)||0).toLocaleString('pt-BR') + ' ' + (m.produto_unidade||'')), h('td',null, LocCell(m) ), h('td',null, m.usuario_responsavel ), h('td',null, m.motivo||'-' ) ]); }) : [ h('tr',{key:'empty'}, h('td',{colSpan:7, className:'text-center text-muted'}, [ h('i',{className:'fas fa-inbox'}),' ','Nenhuma movimentação encontrada' ])) ]);
    var tableBody = h('tbody',null, rows);
    var mobileCards = (items && items.length? items.map(function(m){ return h('div',{className:'card mb-2', key:(m.data_movimentacao+'-'+m.produto_codigo+'-'+m.usuario_responsavel)}, h('div',{className:'card-body'}, [ h('div',{className:'d-flex justify-content-between align-items-center mb-2'}, [ h('div',null,[ (new Date(m.data_movimentacao)).toLocaleDateString('pt-BR'), ' ', h('small',{className:'text-muted ms-1'}, (new Date(m.data_movimentacao)).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}) ) ]), h('div',null, TipoCell(m.tipo_movimentacao) ) ]), h('div',{className:'fw-bold'}, m.produto_nome), h('div',{className:'text-muted'}, m.produto_codigo), h('div',{className:'mt-2'}, [ (parseFloat(m.quantidade)||0).toLocaleString('pt-BR'), ' ', (m.produto_unidade||'') ]), h('div',{className:'mt-2'}, LocCell(m)), h('div',{className:'mt-2'}, m.usuario_responsavel), h('div',{className:'mt-2'}, m.motivo||'-') ])); }) : h('div',{className:'text-center text-muted py-3'}, [ h('i',{className:'fas fa-inbox'}),' ','Nenhuma movimentação encontrada' ]));
    var table = isMobile? h('div',null, mobileCards) : h('div',{className:'table-responsive'}, h('table',{className:'table table-hover'}, [ tableHead, tableBody ]));
    var pag = pagination; var pages = []; var start = Math.max(1, (pag.current_page||1)-2); var end = Math.min(pag.total_pages||1, (pag.current_page||1)+2); for (var i=start;i<=end;i++){ pages.push(i); }
    var paginationNav = h('nav',{ 'aria-label':'Paginação', className:'sticky-bottom bg-white py-2' }, h('ul',{className:'pagination justify-content-center mb-0'}, [ (pag.current_page>1? h('li',{className:'page-item'}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); goToPage((pag.current_page||1)-1); } }, 'Anterior')) : null), pages.map(function(i){ return h('li',{className:'page-item '+(i==pag.current_page?'active':''), key:i}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); goToPage(i); }}, String(i))); }), (pag.current_page<pag.total_pages? h('li',{className:'page-item'}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); goToPage((pag.current_page||1)+1); }}, 'Próximo')) : null) ]));
    return h('div',{className:'container-fluid'}, [ h('div',{className:'row'}, h('div',{className:'col-12'}, [ header, filtros, chipsWrap, h('div',{className:'card'}, h('div',{className:'card-body'}, [ ordenacaoBtn, (loading? h('div',{className:'px-2'}, [ h('div',{className:'placeholder-glow mb-2'}, h('span',{className:'placeholder col-12'})), h('div',{className:'placeholder-glow mb-2'}, h('span',{className:'placeholder col-12'})), h('div',{className:'placeholder-glow mb-2'}, h('span',{className:'placeholder col-12'})) ]) : (error? h('div',{className:'text-center text-danger'}, error) : table)), paginationNav ])), h(TransferModal,{open:showTransfer, onClose:function(){ setShowTransfer(false); }}), h(SaidaModal,{open:showSaida, onClose:function(){ setShowSaida(false); }}) ]) ) ]);
  }
  function mountMovimentacoes(){
    var rootEl = document.getElementById('movs-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'movs-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(MovsPage));
  }
  window.PluckApp.mountMovimentacoes = mountMovimentacoes;
  function DemandasGerenciaPage(){
    var _a = useState([]), pendentes = _a[0], setPendentes = _a[1];
    var _b = useState([]), resolvidas = _b[0], setResolvidas = _b[1];
    var _c = useState(false), loadingPend = _c[0], setLoadingPend = _c[1];
    var _d = useState(''), errPend = _d[0], setErrPend = _d[1];
    var _e = useState(false), loadingRes = _e[0], setLoadingRes = _e[1];
    var _f = useState(''), errRes = _f[0], setErrRes = _f[1];
    function nf0(n){ try{ return Number(n||0).toLocaleString('pt-BR',{maximumFractionDigits:0}); }catch(_){ return String(n||0); } }
    async function loadPendentes(){ setLoadingPend(true); setErrPend(''); try{ var data = await window.fetchJson('/api/demandas?status=pendente&per_page=50'); var items = Array.isArray(data.items)? data.items : []; setPendentes(items); } catch(e){ setErrPend(String(e && e.message || 'Erro ao listar')); setPendentes([]); } setLoadingPend(false); }
    async function loadResolvidas(){ setLoadingRes(true); setErrRes(''); try{ var at = await window.fetchJson('/api/demandas?status=atendido&per_page=50'); var parc = await window.fetchJson('/api/demandas?status=parcialmente_atendido&per_page=50'); var neg = await window.fetchJson('/api/demandas?status=negado&per_page=50'); var items = [].concat(Array.isArray(at.items)?at.items:[], Array.isArray(parc.items)?parc.items:[], Array.isArray(neg.items)?neg.items:[]); items.sort(function(a,b){ var pa = Date.parse(a.updated_at||a.created_at||'')||0; var pb = Date.parse(b.updated_at||b.created_at||'')||0; return pb-pa; }); setResolvidas(items); } catch(e){ setErrRes(String(e && e.message || 'Erro ao listar')); setResolvidas([]); } setLoadingRes(false); }
    useEffect(function(){ loadPendentes(); loadResolvidas(); },[]);
    useEffect(function(){ try{ window.PluckApp = window.PluckApp || {}; window.PluckApp.refreshDemandasGerencia = function(){ try{ loadPendentes(); loadResolvidas(); } catch(_){ } }; } catch(_){ } },[]);
    function abrirModal(d){ try{ var btn = document.createElement('button'); btn.setAttribute('data-demanda', encodeURIComponent(JSON.stringify(d))); if (window.abrirModalAtenderDemanda) window.abrirModalAtenderDemanda(btn); } catch(_){ } }
    function rejeitar(d){ try{ if (window.atualizarStatus) window.atualizarStatus(String(d.id||d.display_id||''), 'negado'); } catch(_){ } }
    function renderLista(items){ if (!items.length) return h('div',{className:'text-muted'}, 'Nenhuma demanda.'); return h('div',{className:'table-responsive'}, h('table',{className:'table table-sm table-striped'}, [ h('thead',null, h('tr',null,[ h('th',null,'ID'), h('th',null,'Produto'), h('th',null,'Setor'), h('th',{className:'text-end'},'Qtd'), h('th',null,'Destino'), h('th',null,'Ações') ])), h('tbody',null, items.map(function(d,idx){ var isGrupo = Number(d.items_count||0) > 0 || String(d.produto_nome||'').startsWith('Lista ('); var unidade = isGrupo? '' : (d.unidade_medida? ' '+String(d.unidade_medida) : ''); return h('tr',{key:String(idx)}, [ h('td',null, String(d.display_id||d.id||'')), h('td',null, String(d.produto_nome||d.produto_id||'')), h('td',null, String(d.setor_nome||d.setor_id||'')), h('td',{className:'text-end'}, nf0(d.quantidade_solicitada)+' '+unidade), h('td',null, String(d.destino_tipo||'')), h('td',null, h('div',{className:'btn-group btn-group-sm', role:'group'}, [ h('button',{className:'btn btn-primary', onClick:function(){ abrirModal(d); }}, [h('i',{className:'fas fa-paper-plane'}),' Enviar']), h('button',{className:'btn btn-outline-danger', onClick:function(){ rejeitar(d); }}, [h('i',{className:'fas fa-ban'}),' Rejeitar']) ])) ] ); })) ])); }
    return h('div',{className:'container-fluid'}, [ h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [ h('h2',null,[h('i',{className:'fas fa-tasks'}),' Demandas • Gerência']) ]))), h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'card'}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-clock'}),' Pendentes']), h('div',null, h('button',{className:'btn btn-sm btn-outline-primary', onClick:loadPendentes}, [h('i',{className:'fas fa-sync-alt'}),' Atualizar'])) ]), h('div',{className:'card-body'}, [ loadingPend? h('div',{className:'text-center py-3'}, h('div',{className:'spinner-border spinner-border-sm', role:'status'}, h('span',{className:'visually-hidden'},'Carregando...'))) : (errPend? h('div',{className:'alert alert-danger'}, errPend) : renderLista(pendentes)) ]) ]))), h('div',{className:'row mt-4'}, h('div',{className:'col-12'}, h('div',{className:'card'}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-check-circle'}),' Resolvidas']), h('div',null, h('button',{className:'btn btn-sm btn-outline-primary', onClick:loadResolvidas}, [h('i',{className:'fas fa-sync-alt'}),' Atualizar'])) ]), h('div',{className:'card-body'}, [ loadingRes? h('div',{className:'text-center py-3'}, h('div',{className:'spinner-border spinner-border-sm', role:'status'}, h('span',{className:'visually-hidden'},'Carregando...'))) : (errRes? h('div',{className:'alert alert-danger'}, errRes) : renderLista(resolvidas)) ]) ]))) ]);
  }
  function mountDemandasGerencia(){
    var rootEl = document.getElementById('demandas-gerencia-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'demandas-gerencia-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(DemandasGerenciaPage));
  }
  window.PluckApp.mountDemandasGerencia = mountDemandasGerencia;
  function LoginPage(props){
    var _a = useState(''), username = _a[0], setUsername = _a[1];
    var _b = useState(''), password = _b[0], setPassword = _b[1];
    var _c = useState(false), remember = _c[0], setRemember = _c[1];
    var _d = useState(false), loading = _d[0], setLoading = _d[1];
    useEffect(function(){ try{ var u = document.getElementById('username'); if (u) u.focus(); } catch(_){ } },[]);
    function onSubmit(){ setLoading(true); }
    return h('div',{className:'login-container'},[
      h('div',{className:'login-header'},[
        h('h1',null, h('img',{src:'/static/logo_pluck.svg', alt:'Logo PluckLog', style:{width:'280px',height:'auto',verticalAlign:'middle'}})),
        h('p',null,'Sistema de Gerenciamento de Almoxarifado')
      ]),
      h('form',{method:'POST', id:'loginForm', onSubmit:onSubmit},[
        h('input',{type:'hidden', name:'csrf_token', value:(props && props.csrf) || (window.CSRF_TOKEN||'')}),
        h('div',{className:'form-floating'},[
          h('input',{type:'text', className:'form-control', id:'username', name:'username', placeholder:'Usuário', required:true, value:username, onChange:function(e){ setUsername(e.target.value); }}),
          h('label',{htmlFor:'username'}, [h('i',{className:'bi bi-person'}),' Usuário'])
        ]),
        h('div',{className:'form-floating'},[
          h('input',{type:'password', className:'form-control', id:'password', name:'password', placeholder:'Senha', required:true, value:password, onChange:function(e){ setPassword(e.target.value); }}),
          h('label',{htmlFor:'password'}, [h('i',{className:'bi bi-lock'}),' Senha'])
        ]),
        h('div',{className:'form-check'},[
          h('input',{className:'form-check-input', type:'checkbox', id:'remember_me', name:'remember_me', checked:remember, onChange:function(e){ setRemember(!!e.target.checked); }}),
          h('label',{className:'form-check-label', htmlFor:'remember_me'},'Lembrar-me')
        ]),
        h('button',{type:'submit', className:'btn btn-login', disabled:loading},[
          h('span',{className:'login-text', style:{display: loading? 'none' : 'inline-flex'}}, [h('i',{className:'bi bi-box-arrow-in-right'}),' Entrar']),
          h('span',{className:'loading', style:{display: loading? 'inline-flex' : 'none'}}, [ h('span',{className:'spinner-border spinner-border-sm', role:'status'}), ' Entrando...' ])
        ])
      ]),
      h('div',{className:'system-info'}, [ h('h6',null,'Níveis de Acesso'), h('small',null,[ h('i',{className:'bi bi-shield-check'}),' Acesso exclusivo a usuários cadastrados. • Para liberação, entre em contato com o administrador. ' ]) ])
    ]);
  }
  function mountLogin(){
    var rootEl = document.getElementById('login-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'login-root'; document.body.appendChild(rootEl); }
    var ctx = document.getElementById('login-context');
    var csrf = ctx && ctx.dataset ? (ctx.dataset.csrf || '') : (window.CSRF_TOKEN||'');
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(LoginPage, { csrf: csrf }));
  }
  window.PluckApp.mountLogin = mountLogin;
  function ConfigPage(){
    var _a = useState([]), backups = _a[0], setBackups = _a[1];
    var _b = useState(''), selectedFile = _b[0], setSelectedFile = _b[1];
    var _c = useState('substituir'), restoreMode = _c[0], setRestoreMode = _c[1];
    var _d = useState(false), loading = _d[0], setLoading = _d[1];
    var _e = useState(''), archiveCollection = _e[0], setArchiveCollection = _e[1];
    var _f = useState(''), archiveQuery = _f[0], setArchiveQuery = _f[1];
    var _g = useState(false), schEnabled = _g[0], setSchEnabled = _g[1];
    var _h = useState('diario'), schInterval = _h[0], setSchInterval = _h[1];
    var _i = useState('02:00'), schTime = _i[0], setSchTime = _i[1];
    var _j = useState(7), schRetention = _j[0], setSchRetention = _j[1];
    useEffect(function(){ refreshBackupList(); },[]);
    async function refreshBackupList(){ try{ setLoading(true); var data = await window.fetchJson('/api/admin/backup/list'); setBackups(Array.isArray(data.items)? data.items : []); } catch(_){ } setLoading(false); }
    async function createBackup(){ try{ setLoading(true); var res = await window.fetchJson('/api/admin/backup/create', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({}) }); if (window.showNotification) window.showNotification('success', 'Backup criado: '+String(res.file||'')); refreshBackupList(); } catch(e){ if (window.showNotification) window.showNotification('danger', String(e && e.message || 'Erro ao criar backup')); } setLoading(false); }
    async function restoreSelected(){ try{ if (!selectedFile) { if (window.showNotification) window.showNotification('warning','Selecione um arquivo de backup'); return; } await window.fetchJson('/api/admin/backup/restore', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ file: selectedFile, mode: restoreMode }) }); if (window.showNotification) window.showNotification('success','Restauração concluída'); } catch(e){ if (window.showNotification) window.showNotification('danger', String(e && e.message || 'Erro na restauração')); } }
    async function resetDatabase(){ try{ var preserveAdmin = false; var el = document.getElementById('chkPreserveAdmin'); if (el) preserveAdmin = !!el.checked; await window.fetchJson('/api/admin/reset-db', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ preserve_admin: preserveAdmin }) }); if (window.showNotification) window.showNotification('success','Banco zerado com sucesso'); } catch(e){ if (window.showNotification) window.showNotification('danger', String(e && e.message || 'Erro ao zerar banco')); } }
    function showConfirmReset(){ var modalEl = document.getElementById('confirmResetModal'); if (!modalEl){ resetDatabase(); return; } var input = document.getElementById('confirmText'); var proceed = document.getElementById('confirmProceed'); if (input) input.value=''; if (proceed) proceed.disabled = true; if (input) input.oninput = function(){ if (proceed) proceed.disabled = (String(input.value||'').trim().toUpperCase() !== 'APAGAR'); }; if (proceed) proceed.onclick = function(){ var bs = bootstrap.Modal.getOrCreateInstance(modalEl); bs.hide(); resetDatabase(); }; var bs = bootstrap.Modal.getOrCreateInstance(modalEl); bs.show(); }
    async function runArchive(){ try{ var raw = String(archiveQuery||'').trim(); var query = raw? JSON.parse(raw) : {}; if (!archiveCollection){ if (window.showNotification) window.showNotification('warning','Informe a coleção'); return; } var res = await window.fetchJson('/api/admin/archive', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ collection: archiveCollection, query: query }) }); if (window.showNotification) window.showNotification('success','Arquivados: '+String((res && res.moved) || 0)); } catch(e){ if (window.showNotification) window.showNotification('danger', String(e && e.message || 'Erro ao arquivar')); } }
    async function saveSchedule(){ try{ await window.fetchJson('/api/admin/backup/schedule', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ enabled: schEnabled, interval: schInterval, time: schTime, retention: Number(schRetention||7) }) }); if (window.showNotification) window.showNotification('success','Agendamento salvo'); } catch(e){ if (window.showNotification) window.showNotification('danger', String(e && e.message || 'Erro ao salvar agendamento')); } }
    var backupOptions = backups.map(function(b,idx){ var name = String(b && b.name || ''); var size = Number(b && b.size || 0); return h('option',{value:name, key:String(idx)}, name+' ('+String(Math.round(size/1024))+' KB)'); });
    return h('div',{className:'container-fluid'},[
      h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [ h('h2',null,[h('i',{className:'fas fa-cog'}),' Configurações']) ]))),
      h('div',{className:'row'},[
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'},[
          h('div',{className:'card-header d-flex justify-content-between align-items-center'},[ h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-database'}),' Backup']), h('div',null, h('button',{className:'btn btn-sm btn-outline-primary', onClick:createBackup, disabled:loading}, [h('i',{className:'fas fa-sync-alt'}),' Criar Backup']) ) ]),
          h('div',{className:'card-body'}, [ loading? h('div',{className:'text-center py-2'}, h('i',{className:'fas fa-spinner fa-spin'})) : null, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Arquivos'), h('select',{className:'form-select', value:selectedFile, onChange:function(e){ setSelectedFile(e.target.value); }}, [ h('option',{value:''},'Selecione um backup'), backupOptions ]) ]), h('div',{className:'row g-2'}, [ h('div',{className:'col-md-6'}, [ h('label',{className:'form-label'},'Modo'), h('select',{className:'form-select', value:restoreMode, onChange:function(e){ setRestoreMode(e.target.value); }}, [ h('option',{value:'substituir'},'Substituir'), h('option',{value:'mesclar'},'Mesclar') ]) ]), h('div',{className:'col-md-6 d-flex align-items-end'}, h('button',{className:'btn btn-outline-success w-100', onClick:restoreSelected}, [h('i',{className:'fas fa-upload'}),' Restaurar']) ) ]) ] )
        ])),
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'},[
          h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-trash-alt'}),' Apagar Banco']) ),
          h('div',{className:'card-body'}, [ h('div',{className:'mb-2 text-muted'}, 'Remove dados e pode preservar usuário admin.'), h('button',{className:'btn btn-danger', onClick:showConfirmReset}, [h('i',{className:'fas fa-exclamation-triangle'}),' Confirmar']) ])
        ]))
      ]),
      h('div',{className:'row'},[
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'},[
          h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-archive'}),' Arquivamento']) ),
          h('div',{className:'card-body'}, [ h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Coleção'), h('input',{className:'form-control', value:archiveCollection, onChange:function(e){ setArchiveCollection(e.target.value); }}) ]), h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Query JSON'), h('textarea',{className:'form-control', rows:3, value:archiveQuery, onChange:function(e){ setArchiveQuery(e.target.value); }}) ]), h('div',null, h('button',{className:'btn btn-outline-primary', onClick:runArchive}, [h('i',{className:'fas fa-box'}),' Arquivar']) ) ])
        ])),
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'},[
          h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-clock'}),' Agendamento']) ),
          h('div',{className:'card-body'}, [ h('div',{className:'form-check form-switch mb-3'}, [ h('input',{className:'form-check-input', type:'checkbox', id:'schEnabled', checked:schEnabled, onChange:function(e){ setSchEnabled(!!e.target.checked); }}), h('label',{className:'form-check-label', htmlFor:'schEnabled'}, 'Habilitar') ]), h('div',{className:'row g-2'}, [ h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'},'Intervalo'), h('select',{className:'form-select', value:schInterval, onChange:function(e){ setSchInterval(e.target.value); }}, [ h('option',{value:'diario'},'Diário'), h('option',{value:'semanal'},'Semanal'), h('option',{value:'mensal'},'Mensal') ]) ]), h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'},'Hora'), h('input',{type:'time', className:'form-control', value:schTime, onChange:function(e){ setSchTime(e.target.value); }}) ]), h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'},'Retenção (dias)'), h('input',{type:'number', className:'form-control', value:schRetention, onChange:function(e){ setSchRetention(Number(e.target.value||7)); }}) ]) ]), h('div',{className:'mt-3'}, h('button',{className:'btn btn-outline-success', onClick:saveSchedule}, [h('i',{className:'fas fa-save'}),' Salvar']) ) ])
        ]))
      ])
    ]);
  }
  function mountConfiguracoes(){
    var rootEl = document.getElementById('config-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'config-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(ConfigPage));
  }
  window.PluckApp.mountConfiguracoes = mountConfiguracoes;
  function CadastroProdutoPage(){
    var _a = useState(''), centralId = _a[0], setCentralId = _a[1];
    var _b = useState(''), codigo = _b[0], setCodigo = _b[1];
    var _c = useState(''), nome = _c[0], setNome = _c[1];
    var _d = useState(''), descricao = _d[0], setDescricao = _d[1];
    var _e = useState(''), observacaoExtra = _e[0], setObservacaoExtra = _e[1];
    var _f = useState(''), categoriaId = _f[0], setCategoriaId = _f[1];
    var _g = useState(''), unidadeMedida = _g[0], setUnidadeMedida = _g[1];
    var _h = useState(true), ativo = _h[0], setAtivo = _h[1];
    var _i = useState([]), categorias = _i[0], setCategorias = _i[1];
    var _j = useState([]), centrais = _j[0], setCentrais = _j[1];
    var _k = useState(false), genLoading = _k[0], setGenLoading = _k[1];
    var _l = useState(false), submitLoading = _l[0], setSubmitLoading = _l[1];
    var _m = useState(null), produtoIdCriado = _m[0], setProdutoIdCriado = _m[1];
    var _n = useState(false), codigoInvalid = _n[0], setCodigoInvalid = _n[1];
    var lastGenKey = useRef('');
    useEffect(function(){ try{ var init = Array.isArray(window.CATEGORIAS_INIT)? window.CATEGORIAS_INIT : []; setCategorias(init); } catch(_){ } var run = async function(){ try{ var data = await window.fetchJson('/api/centrais?ativo=true&per_page=1000'); var items = Array.isArray(data.items)? data.items : []; setCentrais(items); } catch(_){ } try{ if (!Array.isArray(init) || init.length === 0){ var cdata = await window.fetchJson('/api/categorias?ativo=true&per_page=1000'); var citems = Array.isArray(cdata.items)? cdata.items : []; if (citems.length) setCategorias(citems); } } catch(_){ } try{ var u = document.getElementById('central_id'); if (u) u.focus(); } catch(_){ } }; run(); var irBtn = document.getElementById('irParaRecebimento'); if (irBtn){ irBtn.addEventListener('click', function(){ if (produtoIdCriado){ window.location.href = '/produtos/'+encodeURIComponent(String(produtoIdCriado))+'/recebimento'; } }); } }, [produtoIdCriado]);
    useEffect(function(){ try{ var key = String(centralId||'')+'|'+String(categoriaId||''); if (centralId && categoriaId && lastGenKey.current !== key){ lastGenKey.current = key; gerarCodigo(); } } catch(_){ } }, [centralId, categoriaId]);
    async function gerarCodigo(){ if (!centralId || !categoriaId) return; setGenLoading(true); try{ var res = await window.fetchJson('/api/produtos/gerar-codigo', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ central_id: centralId, categoria_id: categoriaId }) }); if (res && res.success && res.codigo){ setCodigo(String(res.codigo)); } } catch(e){ } setGenLoading(false); }
    async function verificarCodigo(val){ var v = String(val||'').trim(); if (!v) { setCodigoInvalid(false); return; } try{ var data = await window.fetchJson('/api/produtos?search='+encodeURIComponent(v)); var items = Array.isArray(data.items)? data.items : []; var ex = items.find(function(p){ return String(p.codigo||'').toLowerCase() === v.toLowerCase(); }); setCodigoInvalid(!!ex); } catch(_){ setCodigoInvalid(false); } }
    async function onSubmit(e){ if (e && e.preventDefault) e.preventDefault(); var data = { central_id: centralId, codigo: String(codigo||'').trim(), nome: String(nome||'').trim(), descricao: String(descricao||'').trim(), observacao_extra: String(observacaoExtra||'').trim()||null, categoria_id: categoriaId, unidade_medida: unidadeMedida, ativo: !!ativo }; if (!data.central_id || !data.codigo || !data.nome){ return; } setSubmitLoading(true); try{ var res = await window.fetchJson('/api/produtos', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) }); if (res && res.id){ setProdutoIdCriado(res.id); var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('sucessoModal')); modal.show(); limpar(); } } catch(e){ } setSubmitLoading(false); }
    function limpar(){ setCentralId(''); setCodigo(''); setNome(''); setDescricao(''); setObservacaoExtra(''); setCategoriaId(''); setUnidadeMedida(''); setAtivo(true); }
    var gerarDisabled = !(centralId && categoriaId) || genLoading;
    var centralOpts = [ h('option',{value:''},'Selecione uma Central') ].concat(centrais.map(function(c){ return h('option',{value:String(c.id||''), key:String(c.id||'')}, String(c.nome||'')); }));
    var categoriaOpts = categorias.map(function(cat){ return h('option',{value:String(cat.id||''), key:String(cat.id||'')}, (cat.codigo||'')+' - '+(cat.nome||'')); });
    return h('div',{className:'container-fluid'}, [
      h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [ h('h2',null,[h('i',{className:'fas fa-plus-circle'}),' Cadastro de Produto']), h('a',{href:'/produtos', className:'btn btn-outline-secondary'}, [h('i',{className:'fas fa-arrow-left'}),' Voltar']) ]))),
      h('div',{className:'row justify-content-center'}, h('div',{className:'col-lg-8'}, h('div',{className:'card'}, h('div',{className:'card-body'}, [
        h('form',{id:'produtoForm', onSubmit:onSubmit},[
          h('div',{className:'row'},[
            h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'central_id'},'Central *'), h('select',{className:'form-select', id:'central_id', name:'central_id', required:true, value:centralId, onChange:function(e){ setCentralId(e.target.value); }}, centralOpts), h('div',{className:'invalid-feedback'},'Por favor, selecione a Central responsável pelo produto.') ])),
            h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'codigo'},'Código *'), h('div',{className:'input-group'}, [ h('input',{type:'text', className:'form-control'+(codigoInvalid?' is-invalid':''), id:'codigo', name:'codigo', readOnly:true, value:codigo, onBlur:function(e){ verificarCodigo(e.target.value); }, onChange:function(e){ setCodigo(e.target.value); }}), h('button',{className:'btn btn-outline-secondary', type:'button', id:'gerarCodigo', disabled:gerarDisabled, onClick:gerarCodigo}, [ genLoading? h('i',{className:'fas fa-spinner fa-spin'}) : h('i',{className:'fas fa-sync-alt'}), ' Gerar' ]) ]), h('div',{className:'invalid-feedback'},'Por favor, gere o código do produto.'), h('small',{className:'form-text text-muted'},'Selecione Central e Categoria para gerar automaticamente') ]))
          ]),
          h('div',{className:'row'}, h('div',{className:'col-md-12'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'nome'},'Nome *'), h('input',{type:'text', className:'form-control', id:'nome', name:'nome', required:true, value:nome, onChange:function(e){ setNome(e.target.value); }}), h('div',{className:'invalid-feedback'},'Por favor, informe o nome do produto.') ]))),
          h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'descricao'},'Descrição'), h('textarea',{className:'form-control', id:'descricao', name:'descricao', rows:3, placeholder:'Descrição detalhada do produto...', value:descricao, onChange:function(e){ setDescricao(e.target.value); }}) ]),
          h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'observacao_extra'},'Observação Extra'), h('textarea',{className:'form-control', id:'observacao_extra', name:'observacao_extra', rows:2, placeholder:'Ex.: Tombamento prefeitura, nº de patrimônio, etiqueta, etc.', value:observacaoExtra, onChange:function(e){ setObservacaoExtra(e.target.value); }}), h('div',{className:'form-text'},'Campo opcional para informações adicionais do produto.') ]),
          h('div',{className:'row'},[
            h('div',{className:'col-md-12'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'categoriasCadastro'},'Categoria do Produto *'), h('select',{className:'form-select', id:'categoriasCadastro', name:'categoriasCadastro', required:true, value:categoriaId, onChange:function(e){ setCategoriaId(e.target.value); }}, categoriaOpts), h('div',{className:'form-text'},'Selecione a categoria do produto.'), h('div',{className:'invalid-feedback'},'Por favor, selecione a categoria.') ])),
            h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label', htmlFor:'unidade_medida'},'Unidade de Medida *'), h('select',{className:'form-select', id:'unidade_medida', name:'unidade_medida', required:true, value:unidadeMedida, onChange:function(e){ setUnidadeMedida(e.target.value); }}, [ h('option',{value:''},'Selecione uma unidade'), h('option',{value:'UN'},'Unidade (UN)'), h('option',{value:'CX'},'Caixa (CX)'), h('option',{value:'PC'},'Pacote (PC)'), h('option',{value:'FR'},'Frasco (FR)'), h('option',{value:'AMP'},'Ampola (AMP)'), h('option',{value:'CP'},'Comprimido (CP)'), h('option',{value:'ML'},'Mililitro (ML)'), h('option',{value:'L'},'Litro (L)'), h('option',{value:'KG'},'Quilograma (KG)'), h('option',{value:'G'},'Grama (G)'), h('option',{value:'M'},'Metro (M)'), h('option',{value:'CM'},'Centímetro (CM)') ]), h('div',{className:'invalid-feedback'},'Por favor, selecione a unidade de medida.') ])),
            h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Status'), h('div',{className:'form-check form-switch'}, [ h('input',{className:'form-check-input', type:'checkbox', id:'ativo', name:'ativo', checked:ativo, onChange:function(e){ setAtivo(!!e.target.checked); }}), h('label',{className:'form-check-label', htmlFor:'ativo'}, 'Produto ativo') ]) ]))
          ]),
          h('div',{className:'d-grid gap-2 d-md-flex justify-content-md-end'}, [ h('button',{type:'button', className:'btn btn-outline-secondary me-md-2', onClick:limpar}, [h('i',{className:'fas fa-eraser'}),' Limpar']), h('button',{type:'submit', className:'btn btn-primary', id:'submitBtn', disabled:submitLoading}, [ submitLoading? h('i',{className:'fas fa-spinner fa-spin'}) : h('i',{className:'fas fa-save'}), ' Salvar Produto' ]) ])
        ])
      ]))))
    ]);
  }
  function mountCadastroProduto(){
    var rootEl = document.getElementById('cadastro-produto-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'cadastro-produto-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(CadastroProdutoPage));
  }
  window.PluckApp.mountCadastroProduto = mountCadastroProduto;
  function DemandasPage(){
    var _a = useState(''), produtoId = _a[0], setProdutoId = _a[1];
    var _b = useState(''), quantidade = _b[0], setQuantidade = _b[1];
    var _c = useState('setor'), destino = _c[0], setDestino = _c[1];
    var _d = useState(''), observacoes = _d[0], setObservacoes = _d[1];
    var _e = useState([]), lista = _e[0], setLista = _e[1];
    var _f = useState([]), minhas = _f[0], setMinhas = _f[1];
    var _g = useState(''), searchMinhas = _g[0], setSearchMinhas = _g[1];
    var nf0 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
    useEffect(function(){ carregarLista(); carregarMinhas(); },[]);
    async function resolverProdutoId(raw){ var val = String(raw||'').trim(); if (!val) return ''; if (/^\d+$/.test(val)) return val; try{ var data = await window.fetchJson('/api/produtos?search='+encodeURIComponent(val)+'&per_page=1'); var item = (data.items||[])[0]; return item && (item.id!=null)? String(item.id) : val; } catch(_){ return val; } }
    async function enviarDemanda(){ try{ var pid = await resolverProdutoId(produtoId); var qtd = parseFloat(String(quantidade||'').replace(',','.')); if (!pid || !qtd || !(qtd>0)){ alert('Informe Produto ID e quantidade válida.'); return; } var res = await window.fetchJson('/api/demandas', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ produto_id: pid, quantidade: qtd, destino_tipo: destino, observacoes: String(observacoes||'').trim() }) }); if (res && res.error){ alert(res.error); return; } limparForm(); carregarMinhas(); } catch(e){ alert('Erro ao enviar: '+String(e && e.message || e)); } }
    async function adicionarItemLista(){ try{ var pid = await resolverProdutoId(produtoId); var qtd = parseFloat(String(quantidade||'').replace(',','.')); var obs = String(observacoes||'').trim(); if (!pid || !qtd || !(qtd>0)){ alert('Informe Produto ID e quantidade válida.'); return; } var res = await window.fetchJson('/api/demandas/lista', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ produto_id: pid, quantidade: qtd, observacao: obs }) }); if (res && res.error){ alert(res.error); return; } carregarLista(); } catch(e){ alert('Erro ao adicionar: '+String(e && e.message || e)); } }
    async function carregarLista(){ try{ var data = await window.fetchJson('/api/demandas/lista'); setLista(Array.isArray(data.items)? data.items : []); } catch(_){ setLista([]); } }
    async function removerItemLista(id){ try{ var res = await window.fetchJson('/api/demandas/lista/'+encodeURIComponent(String(id||'')), { method:'DELETE' }); if (res && res.error){ alert(res.error); return; } carregarLista(); } catch(e){ alert('Erro ao remover: '+String(e && e.message || e)); } }
    async function limparLista(){ try{ var res = await window.fetchJson('/api/demandas/lista/clear', { method:'POST' }); if (res && res.error){ alert(res.error); return; } carregarLista(); } catch(e){ alert('Erro ao limpar: '+String(e && e.message || e)); } }
    async function finalizarLista(){ try{ var res = await window.fetchJson('/api/demandas/finalizar', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ destino_tipo: destino }) }); if (res && res.error){ alert(res.error); return; } limparForm(); carregarLista(); carregarMinhas(); } catch(e){ alert('Erro ao finalizar: '+String(e && e.message || e)); } }
    function limparForm(){ setProdutoId(''); setQuantidade(''); setObservacoes(''); }
    async function carregarMinhas(){ try{ var data = await window.fetchJson('/api/demandas?mine=true&per_page=50'); var items = Array.isArray(data.items)? data.items : []; setMinhas(items); } catch(_){ setMinhas([]); } }
    var listaRows = (lista.length? lista.map(function(it,idx){ var qtdStr = nf0.format(Number(it.quantidade||0)); var unidade = it.unidade_medida? (' '+String(it.unidade_medida)) : ''; return h('tr',{key:String(idx)}, [ h('td',null,[ h('strong',null, String(it.produto_nome||'')), ' ', h('span',{className:'text-muted'}, String(it.produto_codigo||'')) ]), h('td',{className:'text-end'}, qtdStr+unidade), h('td',null, String(it.observacao||'')), h('td',{className:'text-end'}, h('button',{className:'btn btn-sm btn-outline-danger', onClick:function(){ removerItemLista(it.id); }}, h('i',{className:'fas fa-trash'})) ) ]); }) : [ h('tr',{key:'empty'}, h('td',{colSpan:4}, h('div',{className:'text-muted'},'Nenhum item na lista.')) ) ]);
    var minhasFilt = (function(){ var q = String(searchMinhas||'').trim().toLowerCase(); if (!q) return minhas; return minhas.filter(function(d){ var a = String(d.display_id||d.id||'').toLowerCase(); var b = String(d.produto_nome||d.produto_id||'').toLowerCase(); var c = String(d.status||'').toLowerCase(); var e = String(d.created_at||'').toLowerCase(); return a.includes(q)||b.includes(q)||c.includes(q)||e.includes(q); }); })();
    var minhasRows = (minhasFilt.length? minhasFilt.map(function(d,idx){ var qtdStr = nf0.format(Number(d.quantidade_solicitada||0)); var unidade = d.unidade_medida? (' '+String(d.unidade_medida)) : ''; var st = String(d.status||'').toLowerCase(); return h('tr',{key:String(idx)}, [ h('td',null, String(d.display_id||d.id||'')), h('td',null,[ h('strong',null, String(d.produto_nome||d.produto_id||'')) ]), h('td',{className:'text-end'}, qtdStr+unidade), h('td',null, String(st)), h('td',null, String(d.created_at||'')) ]); }) : [ h('tr',{key:'empty'}, h('td',{colSpan:5}, h('div',{className:'text-muted'},'Nenhuma demanda encontrada.')) ) ]);
    return h('div',{className:'container-fluid'}, [
      h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [ h('h2',null,[h('i',{className:'fas fa-clipboard-list'}),' Demandas de Produtos']), h('div',null, h('a',{href:'/demandas/gerencia', className:'btn btn-outline-primary'}, [h('i',{className:'fas fa-tasks'}),' Gerenciar Demandas']) ) ]))),
      h('div',{className:'row'}, [
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'}, [ h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-plus-circle'}),' Nova Demanda'])), h('div',{className:'card-body'}, [ h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Buscar Produto'), h('input',{type:'text', className:'form-control', placeholder:'Digite nome, código ou ID...', value:produtoId, onChange:function(e){ setProdutoId(e.target.value); }}) ]), h('div',{className:'row'}, [ h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Quantidade'), h('input',{type:'number', className:'form-control', min:'0.001', step:'0.001', value:quantidade, onChange:function(e){ setQuantidade(e.target.value); }}) ])), h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Destino'), h('select',{className:'form-select', value:destino, onChange:function(e){ setDestino(e.target.value); }}, [ h('option',{value:'setor'},'Setor'), h('option',{value:'almoxarifado'},'Almoxarifado'), h('option',{value:'sub_almoxarifado'},'Sub‑Almoxarifado') ]) ])) ]), h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Observações'), h('textarea',{className:'form-control', rows:2, placeholder:'Motivo, urgência, detalhes...', value:observacoes, onChange:function(e){ setObservacoes(e.target.value); }}) ]), h('div',{className:'d-flex justify-content-end gap-2'}, [ h('button',{className:'btn btn-outline-primary', type:'button', onClick:adicionarItemLista}, [h('i',{className:'fas fa-plus'}),' Adicionar à Lista']), h('button',{className:'btn btn-primary', type:'button', onClick:enviarDemanda}, [h('i',{className:'fas fa-paper-plane'}),' Enviar']) ]) ]) ])),
        h('div',{className:'col-lg-6'}, h('div',{className:'card mb-4'}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-list-ul'}),' Lista de Demanda (rascunho)']), h('div',{className:'d-flex gap-2'}, [ h('button',{className:'btn btn-sm btn-outline-secondary', onClick:carregarLista}, [h('i',{className:'fas fa-sync-alt'}),' Atualizar']), h('button',{className:'btn btn-sm btn-outline-danger', onClick:limparLista}, [h('i',{className:'fas fa-trash'}),' Limpar']), h('button',{className:'btn btn-sm btn-success', onClick:finalizarLista}, [h('i',{className:'fas fa-check'}),' Finalizar']) ]) ]), h('div',{className:'card-body'}, h('div',{className:'table-responsive'}, h('table',{className:'table table-sm'}, [ h('thead',null, h('tr',null, [ h('th',null,'Produto'), h('th',{className:'text-end'},'Qtd'), h('th',null,'Obs'), h('th',null,'') ])), h('tbody',null, listaRows) ]))) ]) )
      ]),
      h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'card'}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-inbox'}),' Minhas Demandas']), h('div',null, h('input',{type:'text', className:'form-control form-control-sm', placeholder:'Buscar...', value:searchMinhas, onChange:function(e){ setSearchMinhas(e.target.value); }}) ) ]), h('div',{className:'card-body'}, h('div',{className:'table-responsive'}, h('table',{className:'table table-sm table-striped'}, [ h('thead',null, h('tr',null, [ h('th',null,'ID'), h('th',null,'Produto'), h('th',{className:'text-end'},'Qtd'), h('th',null,'Status'), h('th',null,'Data') ])), h('tbody',null, minhasRows) ]))) ])))
    ]);
  }
  function mountDemandas(){
    var rootEl = document.getElementById('demandas-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'demandas-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(DemandasPage));
  }
  window.PluckApp.mountDemandas = mountDemandas;
  function RecebimentoPage(){
    var _a = useState(''), termo = _a[0], setTermo = _a[1];
    var _b = useState([]), resultados = _b[0], setResultados = _b[1];
    var _c = useState(null), produto = _c[0], setProduto = _c[1];
    var _d = useState([]), almoxes = _d[0], setAlmoxes = _d[1];
    var _e = useState(''), almoxId = _e[0], setAlmoxId = _e[1];
    var _f = useState(''), quantidade = _f[0], setQuantidade = _f[1];
    var _g = useState(''), precoUnit = _g[0], setPrecoUnit = _g[1];
    var _h = useState(''), lote = _h[0], setLote = _h[1];
    var _i = useState(''), fornecedor = _i[0], setFornecedor = _i[1];
    var _j = useState(''), dataFab = _j[0], setDataFab = _j[1];
    var _k = useState(''), dataVenc = _k[0], setDataVenc = _k[1];
    var _l = useState(''), notaFiscal = _l[0], setNotaFiscal = _l[1];
    var _m = useState(''), observacoes = _m[0], setObservacoes = _m[1];
    var _n = useState(''), dataReceb = _n[0], setDataReceb = _n[1];
    var _o = useState(false), submitting = _o[0], setSubmitting = _o[1];
    var valorTotal = (function(){ var q = parseFloat(String(quantidade||'').replace(',','.'))||0; var p = parseFloat(String(precoUnit||'').replace(',','.'))||0; return q*p; })();
    useEffect(function(){ try{ var agora = new Date(); agora.setMinutes(agora.getMinutes()-agora.getTimezoneOffset()); setDataReceb(agora.toISOString().slice(0,16)); }catch(_){ } var path = window.location.pathname; var after = (path.split('/produtos/')[1]||''); var idSeg = (after.split('/')[0]||'').trim(); if (idSeg){ window.fetchJson('/api/produtos/'+encodeURIComponent(idSeg)).then(function(p){ if (!p.error){ selecionarProduto(p); } }); } },[]);
    useEffect(function(){ var t = setTimeout(function(){ buscar(); }, 300); return function(){ clearTimeout(t); }; }, [termo]);
    async function buscar(){ var s = String(termo||'').trim(); if (s.length<2){ setResultados([]); return; } try{ var data = await window.fetchJson('/api/produtos?search='+encodeURIComponent(s)+'&limit=10'); setResultados(Array.isArray(data.items)? data.items : []); } catch(_){ setResultados([]); } }
    async function selecionarProduto(p){ setProduto(p||null); setResultados([]); setTermo(p && p.nome ? p.nome : ''); setAlmoxId(''); try{ var data = await window.fetchJson('/api/produtos/'+encodeURIComponent(String(p.id))+'/almoxarifados'); if (data && data.success){ setAlmoxes(Array.isArray(data.almoxarifados)? data.almoxarifados : []); } else { setAlmoxes([]); } } catch(_){ setAlmoxes([]); } try{ var agora = new Date(); agora.setMinutes(agora.getMinutes()-agora.getTimezoneOffset()); setDataReceb(agora.toISOString().slice(0,16)); } catch(_){ } }
    function limparSelecao(){ setProduto(null); setAlmoxes([]); setAlmoxId(''); setQuantidade(''); setPrecoUnit(''); setLote(''); setFornecedor(''); setDataFab(''); setDataVenc(''); setNotaFiscal(''); setObservacoes(''); }
    function vencAlert(){ if (!dataVenc) return ''; try{ var hoje = new Date(); var v = new Date(dataVenc); var dias = Math.ceil((v - hoje)/(1000*60*60*24)); if (dias<0) return 'Produto já vencido!'; if (dias<=30) return 'Vence em breve!'; if (dias<=90) return 'Vencimento próximo'; return 'Validade adequada'; } catch(_){ return ''; } }
    async function onSubmit(e){ if (e && e.preventDefault) e.preventDefault(); if (!produto){ alert('Selecione um produto primeiro'); return; } var q = parseFloat(String(quantidade||'').replace(',','.')); if (!q || q<=0){ alert('Quantidade deve ser maior que zero'); return; } if (!almoxId){ alert('Selecione um almoxarifado'); return; } var payload = { produto_id: produto.id, quantidade: q, preco_unitario: (precoUnit? parseFloat(String(precoUnit).replace(',','.')) : null), lote: (lote||'').trim()||null, fornecedor: (fornecedor||'').trim()||null, data_fabricacao: dataFab||null, data_vencimento: dataVenc||null, nota_fiscal: (notaFiscal||'').trim()||null, observacoes: (observacoes||'').trim()||null, data_recebimento: dataReceb }; payload.almoxarifado_id = (/^\d+$/.test(String(almoxId)))? parseInt(String(almoxId), 10) : almoxId; setSubmitting(true); try{ var res = await window.fetchJson('/api/produtos/'+encodeURIComponent(String(produto.id))+'/recebimento', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) }); if (res && res.error){ throw new Error(res.error); } var total = q * (payload.preco_unitario || 0); var resumo = h('div',{className:'row'}, [ h('div',{className:'col-12 mb-3'}, [ h('h6',null, h('strong',null, String(produto.nome||''))), h('small',{className:'text-muted'}, 'Código: '+String(produto.codigo||'')) ]), h('div',{className:'col-6'}, [ h('strong',null,'Quantidade:'), h('br'), String(q)+' '+String(produto.unidade_medida||'') ]), h('div',{className:'col-6'}, [ h('strong',null,'Lote:'), h('br'), String(payload.lote||'-') ]), h('div',{className:'col-6'}, [ h('strong',null,'Preço Unitário:'), h('br'), (payload.preco_unitario? Number(payload.preco_unitario).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}) : '-') ]), h('div',{className:'col-6'}, [ h('strong',null,'Valor Total:'), h('br'), Number(total).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}) ]), h('div',{className:'col-6'}, [ h('strong',null,'Fornecedor:'), h('br'), String(payload.fornecedor||'-') ]), h('div',{className:'col-6'}, [ h('strong',null,'Nota Fiscal:'), h('br'), String(payload.nota_fiscal||'-') ]), h('div',{className:'col-6'}, [ h('strong',null,'Data do Recebimento:'), h('br'), (payload.data_recebimento? (new Date(payload.data_recebimento)).toLocaleDateString('pt-BR') : '-') ]) , h('div',{className:'col-6'}, [ h('strong',null,'Data de Fabricação:'), h('br'), (payload.data_fabricacao? (new Date(payload.data_fabricacao)).toLocaleDateString('pt-BR') : '-') ]), h('div',{className:'col-6'}, [ h('strong',null,'Data de Vencimento:'), h('br'), (payload.data_vencimento? (new Date(payload.data_vencimento)).toLocaleDateString('pt-BR') : '-') ]), h('div',{className:'col-12'}, [ h('strong',null,'Observações:'), h('br'), String(payload.observacoes||'-') ]) ]);
      var cont = document.createElement('div'); ReactDOM.createRoot(cont).render(resumo); var target = document.getElementById('resumoRecebimento'); if (target){ target.innerHTML = ''; target.appendChild(cont); }
      var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('confirmacaoModal')); modal.show(); } catch(e){ alert('Erro ao registrar recebimento: '+String(e && e.message || e)); } setSubmitting(false); }
    function verDetalhes(){ try{ var destinoId = produto && produto.id ? produto.id : null; if (!destinoId){ var path = window.location.pathname; var after = (path.split('/produtos/')[1]||''); var fromUrl = (after.split('/')[0]||'').trim(); if (fromUrl) destinoId = fromUrl; } if (destinoId) window.location.href = '/produtos/'+encodeURIComponent(String(destinoId)); } catch(_){ } }
    var headerRow = h('div',{className:'row'}, [
      h('div',{className:'col-12'},
        h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [
          h('h2',null,[h('i',{className:'fas fa-plus-circle'}),' Recebimento de Produto']),
          h('div',null,[
            h('a',{href:'/produtos', className:'btn btn-outline-secondary me-2'}, [h('i',{className:'fas fa-list'}),' Lista de Produtos']),
            h('button',{className:'btn btn-outline-primary', onClick:verDetalhes, style:{display: (produto? 'inline-block':'none')}}, [h('i',{className:'fas fa-eye'}),' Ver Detalhes'])
          ])
        ])
      )
    ]);
    var leftCol = h('div',{className:'col-lg-4'}, h('div',{className:'card mb-4'}, [ h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-search'}),' Selecionar Produto'])), h('div',{className:'card-body'}, [ h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Buscar Produto'), h('input',{type:'text', className:'form-control', id:'buscarProduto', placeholder:'Digite código ou nome do produto...', value:termo, onChange:function(e){ setTermo(e.target.value); }}), h('div',{className:'form-text'}, 'Digite pelo menos 2 caracteres') ]), (resultados.length? h('div',null, [ h('label',{className:'form-label'},'Resultados:'), h('div',{className:'list-group'}, resultados.map(function(p,idx){ return h('a',{href:'#', key:String(idx), className:'list-group-item list-group-item-action', onClick:function(e){ e.preventDefault(); selecionarProduto(p); }}, [ h('div',{className:'d-flex w-100 justify-content-between'}, [ h('h6',{className:'mb-1'}, String(p.nome||'')), h('small',{className:'badge bg-primary'}, String(p.codigo||'')) ]), h('p',{className:'mb-1'}, String(p.descricao||'Sem descrição')), h('small',null, 'Unidade: '+String(p.unidade_medida||'')) ]); })) ]) : null), (produto? h('div',{id:'produtoSelecionado'}, h('div',{className:'alert alert-success'}, [ h('h6',null, [h('i',{className:'fas fa-check-circle'}),' Produto Selecionado']), h('div',{id:'infoProdutoSelecionado'}, [ h('strong',null, String(produto.nome||'')), h('br'), h('small',{className:'text-muted'}, 'Código: '+String(produto.codigo||'')+' | Unidade: '+String(produto.unidade_medida||'')) ]), h('button',{className:'btn btn-sm btn-outline-secondary mt-2', onClick:limparSelecao}, [h('i',{className:'fas fa-times'}),' Alterar Produto']) ])) : null) ]) ]));
    var formChildren = [
      h('div',{className:'row'}, [
        h('div',{className:'col-md-4'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Quantidade Recebida *'), h('div',{className:'input-group'}, [ h('input',{type:'number', className:'form-control', min:'0.01', step:'0.01', required:true, value:quantidade, onChange:function(e){ setQuantidade(e.target.value); }}), h('span',{className:'input-group-text'}, String(produto && produto.unidade_medida || 'UN')) ]) ])),
        h('div',{className:'col-md-4'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Preço Unitário'), h('div',{className:'input-group'}, [ h('span',{className:'input-group-text'}, 'R$'), h('input',{type:'number', className:'form-control', min:'0', step:'0.01', value:precoUnit, onChange:function(e){ setPrecoUnit(e.target.value); }} ) ]) ])),
        h('div',{className:'col-md-4'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Almoxarifado *'), h('select',{className:'form-control', required:true, disabled:!almoxes.length, value:almoxId, onChange:function(e){ setAlmoxId(e.target.value); }}, [ h('option',{value:''}, produto? 'Selecione um almoxarifado' : 'Selecione um produto primeiro' ), almoxes.map(function(a){ var txt = String(a.nome||''); if (a.tem_estoque) txt += ' - Estoque: '+String(a.quantidade_atual||''); return h('option',{value:String(a.id||''), key:String(a.id||'')}, txt); }) ]) ]))
      ]),
      h('div',{className:'row'}, [
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Número do Lote'), h('input',{type:'text', className:'form-control', value:lote, onChange:function(e){ setLote(e.target.value); }}), h('div',{className:'form-text'}, 'Identificação do lote do fornecedor') ])),
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Fornecedor'), h('input',{type:'text', className:'form-control', value:fornecedor, onChange:function(e){ setFornecedor(e.target.value); }}) ]))
      ]),
      h('div',{className:'row'}, [
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Data de Fabricação'), h('input',{type:'date', className:'form-control', value:dataFab, onChange:function(e){ setDataFab(e.target.value); }}) ])),
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Data de Vencimento'), h('input',{type:'date', className:'form-control', value:dataVenc, onChange:function(e){ setDataVenc(e.target.value); }}), h('div',{className:'form-text'}, vencAlert()) ]))
      ]),
      h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Nota Fiscal'), h('input',{type:'text', className:'form-control', value:notaFiscal, onChange:function(e){ setNotaFiscal(e.target.value); }}) ]),
      h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Observações'), h('textarea',{className:'form-control', rows:3, value:observacoes, onChange:function(e){ setObservacoes(e.target.value); }}) ]),
      h('div',{className:'row'}, [
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Valor Total'), h('div',{className:'input-group'}, [ h('span',{className:'input-group-text'}, 'R$'), h('input',{type:'text', className:'form-control', readOnly:true, value: Number(valorTotal).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}) }) ]), h('div',{className:'form-text'}, 'Calculado automaticamente') ])),
        h('div',{className:'col-md-6'}, h('div',{className:'mb-3'}, [ h('label',{className:'form-label'},'Data do Recebimento'), h('input',{type:'datetime-local', className:'form-control', value:dataReceb, onChange:function(e){ setDataReceb(e.target.value); }}) ]))
      ]),
      h('div',{className:'d-grid gap-2 d-md-flex justify-content-md-end'}, [
        h('button',{type:'button', className:'btn btn-outline-secondary me-md-2', onClick:limparSelecao}, [h('i',{className:'fas fa-eraser'}),' Limpar']),
        h('button',{type:'submit', className:'btn btn-success', id:'submitBtn', disabled:submitting}, [ submitting? h('i',{className:'fas fa-spinner fa-spin'}) : h('i',{className:'fas fa-check'}), ' Registrar Recebimento' ])
      ])
    ];
    var rightCardChildren = [
      h('div',{className:'card-header'}, h('h5',{className:'mb-0'}, [h('i',{className:'fas fa-clipboard-list'}),' Dados do Recebimento'])),
      h('div',{className:'card-body'}, [ produto? h('form',{onSubmit:onSubmit}, formChildren) : h('div',{id:'mensagemSelecao', className:'text-center py-5'}, [ h('i',{className:'fas fa-arrow-left fa-3x text-muted mb-3'}), h('h5',{className:'text-muted'},'Selecione um produto para continuar'), h('p',{className:'text-muted'},'Use a busca ao lado para encontrar o produto que deseja receber') ]) ])
    ];
    var rightCol = h('div',{className:'col-lg-8'}, h('div',{className:'card'}, rightCardChildren));
    var contentRow = h('div',{className:'row'}, [ leftCol, rightCol ]);
    return h('div',{className:'container-fluid'}, [ headerRow, contentRow ]);
  }
  function mountRecebimento(){
    var rootEl = document.getElementById('recebimento-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'recebimento-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(RecebimentoPage));
  }
  window.PluckApp.mountRecebimento = mountRecebimento;
  function CategoriasPage(){
    var _a = useState(''), search = _a[0], setSearch = _a[1];
    var _b = useState(''), status = _b[0], setStatus = _b[1];
    var _c = useState(1), page = _c[0], setPage = _c[1];
    var _d = useState([]), items = _d[0], setItems = _d[1];
    var _e = useState({ pages:1, current_page:1, has_prev:false, has_next:false, prev_num:1, next_num:1 }), meta = _e[0], setMeta = _e[1];
    var _f = useState(false), loading = _f[0], setLoading = _f[1];
    useEffect(function(){ load(); }, [search, status, page]);
    async function load(){ try{ setLoading(true); var params = new URLSearchParams(); params.set('page', String(page||1)); params.set('per_page', '10'); if (search) params.set('search', search.trim()); if (status) params.set('ativo', status); var resp = await fetch('/api/categorias?'+params.toString()); var data = await resp.json(); if (resp.ok){ setItems(Array.isArray(data.items)? data.items : []); setMeta({ pages: Number(data.pages||1), current_page: Number(data.current_page||page||1), has_prev: !!data.has_prev, has_next: !!data.has_next, prev_num: Number(data.prev_num||Math.max(1,(page||1)-1)), next_num: Number(data.next_num||Math.min(Number(data.pages||1), (page||1)+1)) }); } } catch(_){ setItems([]); setMeta({ pages:1, current_page:1, has_prev:false, has_next:false, prev_num:1, next_num:1 }); } setLoading(false); }
    function applyFilters(){ setPage(1); }
    function clearFilters(){ setSearch(''); setStatus(''); setPage(1); }
    function changePage(p){ setPage(p); }
    var rows = (items.length? items.map(function(c,idx){ return h('tr',{key:String(idx)}, [ h('td',null, h('span',{className:'badge', style:{backgroundColor:String(c.cor||'#007bff'), color:'white'}}, String(c.codigo||'')) ), h('td',null, String(c.nome||'')), h('td',null, String(c.descricao||'-')), h('td',null, h('div',{className:'d-flex align-items-center'}, [ h('div',{className:'color-preview me-2', style:{width:'20px',height:'20px',backgroundColor:String(c.cor||'#007bff'),borderRadius:'3px',border:'1px solid #ddd'}}, null), h('small',{className:'text-muted'}, String(c.cor||'')) ])), h('td',null, h('span',{className:'badge bg-info'}, String(c.produtos_count||0))), h('td',null, h('span',{className:'badge bg-secondary'}, String(c.usuarios_count||0))), h('td',null, h('span',{className:'badge '+(c.ativo? 'bg-success' : 'bg-danger')}, (c.ativo? 'Ativo' : 'Inativo') ) ), h('td',null, h('div',{className:'btn-group btn-group-sm', role:'group'}, [ h('button',{type:'button', className:'btn btn-outline-primary', title:'Editar', onClick:function(){ if (window.editCategoria) window.editCategoria(c.id); }}, h('i',{className:'fas fa-edit'})), h('button',{type:'button', className:'btn btn-outline-warning', title:(c.ativo? 'Desativar':'Ativar'), onClick:function(){ if (window.toggleStatus) window.toggleStatus(c.id, c.ativo); }}, h('i',{className:'fas fa-'+(c.ativo? 'eye-slash':'eye')})), h('button',{type:'button', className:'btn btn-outline-danger', title:'Excluir', onClick:function(){ if (window.confirmDelete) window.confirmDelete(c.id, c.nome); }}, h('i',{className:'fas fa-trash'})) ]) ) ]); }) : [ h('tr',{key:'empty'}, h('td',{colSpan:8, className:'text-center text-muted py-4'}, [ h('i',{className:'fas fa-inbox fa-2x mb-2'}), h('br'), 'Nenhuma categoria encontrada' ])) ]);
    var pagination = (meta.pages>1? h('nav',{id:'navPaginationCategorias', 'aria-label':'Paginação de categorias'}, h('ul',{className:'pagination justify-content-center'}, [ (meta.has_prev? h('li',{className:'page-item'}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); changePage(meta.prev_num); }}, 'Anterior')) : null), (function(){ var nodes=[]; for(var i=1;i<=meta.pages;i++){ if (i===meta.current_page){ nodes.push(h('li',{className:'page-item active', key:String(i)}, h('span',{className:'page-link'}, String(i)))); } else if (i===1 || i===meta.pages || Math.abs(i-meta.current_page)<=2){ nodes.push(h('li',{className:'page-item', key:String(i)}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); changePage(i); }}, String(i)))); } } return nodes; })(), (meta.has_next? h('li',{className:'page-item'}, h('a',{className:'page-link', href:'#', onClick:function(e){ e.preventDefault(); changePage(meta.next_num); }}, 'Próximo')) : null) ])) : null);
    return h('div',{className:'container-fluid'}, [
      h('div',{className:'row'}, h('div',{className:'col-12'}, h('div',{className:'d-flex justify-content-between align-items-center mb-4'}, [ h('h2',null,[h('i',{className:'fas fa-tags'}),' Categorias']), h('button',{id:'newCategoriaBtn', className:'btn btn-primary', onClick:function(){ if (window.openCategoriaModal) window.openCategoriaModal(null); }}, [h('i',{className:'fas fa-plus'}),' Nova Categoria']) ]))),
      h('div',{className:'card mb-4'}, h('div',{className:'card-body'}, [ h('div',{className:'row'}, [ h('div',{className:'col-md-4'}, [ h('label',{className:'form-label'}, 'Buscar'), h('input',{type:'text', id:'searchInput', className:'form-control', placeholder:'Nome, código ou descrição...', value:search, onChange:function(e){ setSearch(e.target.value); applyFilters(); }}) ]), h('div',{className:'col-md-3'}, [ h('label',{className:'form-label'}, 'Status'), h('select',{id:'statusFilter', className:'form-select', value:status, onChange:function(e){ setStatus(e.target.value); applyFilters(); }}, [ h('option',{value:''},'Todos'), h('option',{value:'true'},'Ativos'), h('option',{value:'false'},'Inativos') ]) ]), h('div',{className:'col-md-5 d-flex align-items-end justify-content-end'}, h('div',{className:'d-flex gap-2'}, [ h('button',{className:'btn btn-outline-secondary', onClick:clearFilters}, [h('i',{className:'fas fa-times'}),' Limpar']), h('button',{className:'btn btn-outline-primary', onClick:function(){ load(); }}, [h('i',{className:'fas fa-sync-alt'}),' Atualizar']) ])) ] ) ])),
      h('div',{className:'card'}, [ h('div',{className:'card-body'}, [ (loading? h('div',{className:'text-center py-4'}, [ h('i',{className:'fas fa-spinner fa-spin'}),' Carregando categorias...' ]) : h('div',{className:'table-responsive'}, h('table',{className:'table table-striped'}, [ h('thead',null, h('tr',null, [ h('th',null,'Código'), h('th',null,'Nome'), h('th',null,'Descrição'), h('th',null,'Cor'), h('th',null,'Produtos'), h('th',null,'Usuários'), h('th',null,'Status'), h('th',null,'Ações') ])), h('tbody',null, rows) ])) ), h('div',{className:'d-flex justify-content-center mt-2'}, pagination) ]) ])
    ]);
  }
  function mountCategorias(){
    var rootEl = document.getElementById('categorias-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'categorias-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(CategoriasPage));
  }
  window.PluckApp.mountCategorias = mountCategorias;
  function OperadorSetorPage(){
    var _a = useState(''), termo = _a[0], setTermo = _a[1];
    var _b = useState([]), resultados = _b[0], setResultados = _b[1];
    var _c = useState(null), produto = _c[0], setProduto = _c[1];
    var _d = useState(''), setorNome = _d[0], setSetorNome = _d[1];
    var _e = useState({ total:0, disponivel:0, reservado:0, atualizado:'', unidade:'' }), estoque = _e[0], setEstoque = _e[1];
    var _f = useState({ almox:0, sub:0, usado:0, disp:0 }), resumo = _f[0], setResumo = _f[1];
    var _g = useState([]), lotes = _g[0], setLotes = _g[1];
    var _h = useState(''), consumoQtd = _h[0], setConsumoQtd = _h[1];
    var _i = useState(''), consumoStatus = _i[0], setConsumoStatus = _i[1];
    var _j = useState(false), loadingBusca = _j[0], setLoadingBusca = _j[1];

    var setorId = (function(){ var el = document.getElementById('operador-setor-context'); var raw = el && el.dataset ? el.dataset.setorId || '' : ''; return normalizeIdStr(raw); })();

    useEffect(function(){ if (!setorId) { setSetorNome('-'); return; } window.fetchJson('/api/setores/'+encodeURIComponent(setorId)).then(function(d){ setSetorNome(String(d.nome||d.descricao||'Setor')); }).catch(function(){ setSetorNome(setorId); }); }, []);

    useEffect(function(){ var t = setTimeout(function(){ var s = String(termo||'').trim(); if (!s && !produto) { window.fetchJson('/api/produtos?per_page=10').then(function(d){ setResultados(Array.isArray(d.items)? d.items: []); }); return; } if (!s) { setResultados([]); return; } setLoadingBusca(true); window.fetchJson('/api/produtos?search='+encodeURIComponent(s)+'&per_page=10').then(function(d){ setResultados(Array.isArray(d.items)? d.items : []); }).catch(function(){ setResultados([]); }).finally(function(){ setLoadingBusca(false); }); }, 300); return function(){ clearTimeout(t); }; }, [termo]);

    function selecionarProduto(p){ setProduto(p); setResultados([]); setTermo(''); carregarEstoque(p); carregarResumoDia(p); carregarLotes(p); }
    async function carregarEstoque(p){ var pid = normalizeIdStr(p && (p.id!=null? p.id : (p._id || p._id_str))); if (!pid) return; try{ var data = await window.fetchJson('/api/produtos/'+encodeURIComponent(pid)+'/estoque'); var meusetorStr = setorId; var candidatos = []; if (meusetorStr) candidatos.push(String(meusetorStr)); try{ var info = await window.fetchJson('/api/setores/'+encodeURIComponent(meusetorStr)); if (info && (info.id!=null)) candidatos.push(String(info.id)); }catch(_){ } var setorItem = null; var rows = Array.isArray(data.estoques)? data.estoques : []; for (var i=0;i<rows.length;i++){ var it = rows[i]; var tipo = String(it.tipo||'').toLowerCase(); var lid = normalizeIdStr(it.local_id != null? it.local_id : (it.setor_id != null? it.setor_id : '')); if (tipo==='setor' && candidatos.indexOf(String(lid))!==-1){ setorItem = it; break; } } if (!setorItem){ setEstoque({total:0, disponivel:0, reservado:0, atualizado:'', unidade: String(p.unidade_medida||'')}); return; } var total = Number(setorItem.quantidade||0); var disponivel = Number((setorItem.quantidade_disponivel != null)? setorItem.quantidade_disponivel : setorItem.quantidade||0); var reservado = Math.max(0, total - disponivel); var atualizado = setorItem.data_atualizacao? new Date(setorItem.data_atualizacao).toLocaleString('pt-BR') : '-'; setEstoque({ total: total, disponivel: disponivel, reservado: reservado, atualizado: atualizado, unidade: String(p.unidade_medida||'') }); }catch(_){ setEstoque({total:0, disponivel:0, reservado:0, atualizado:'', unidade: String(p && p.unidade_medida || '')}); } }
    async function carregarResumoDia(p){ var pid = normalizeIdStr(p && (p.id!=null? p.id : (p._id || p._id_str))); if (!pid || !setorId) return; try{ var data = await window.fetchJson('/api/setores/'+encodeURIComponent(setorId)+'/produtos/'+encodeURIComponent(pid)+'/resumo-dia'); var rpo = data.recebido_hoje_por_origem || {}; setResumo({ almox: Number(rpo.almoxarifado||0), sub: Number(rpo.sub_almoxarifado||0), usado: Number(data.usado_hoje_total||0), disp: Number(data.estoque_disponivel||data.estoque_atual||0) }); }catch(_){ setResumo({ almox:0, sub:0, usado:0, disp:0 }); } }
    async function carregarLotes(p){ var pid = normalizeIdStr(p && (p.id!=null? p.id : (p._id || p._id_str))); if (!pid || !setorId) { setLotes([]); return; } try{ async function fetchBy(tipo, id){ var res = await window.fetchJson('/api/produtos/'+encodeURIComponent(pid)+'/lotes?local_tipo='+encodeURIComponent(tipo)+'&local_id='+encodeURIComponent(id)); return Array.isArray(res.items)? res.items : []; } async function fetchGlobal(){ var res = await window.fetchJson('/api/produtos/'+encodeURIComponent(pid)+'/lotes'); return Array.isArray(res.items)? res.items : []; } async function resolveHier(){ try{ var info = await window.fetchJson('/api/setores/'+encodeURIComponent(setorId)); var subIds = Array.isArray(info.sub_almoxarifado_ids)? info.sub_almoxarifado_ids.map(normalizeIdStr) : []; var almoxIds = Array.isArray(info.almoxarifado_ids)? info.almoxarifado_ids.map(normalizeIdStr) : []; var centralIds = Array.isArray(info.central_ids)? info.central_ids.map(normalizeIdStr) : []; if (!subIds.length && info.sub_almoxarifado_id) subIds = [normalizeIdStr(info.sub_almoxarifado_id)]; if (!almoxIds.length && info.almoxarifado_id) almoxIds = [normalizeIdStr(info.almoxarifado_id)]; if (!centralIds.length && info.central_id) centralIds = [normalizeIdStr(info.central_id)]; return { sub: subIds, almox: almoxIds, central: centralIds }; }catch(_){ return { sub:[], almox:[], central:[] }; } } var items = await fetchBy('setor', setorId); var origemAtual = 'setor'; if (!items.length){ var h = await resolveHier(); for (var i=0;i<h.central.length;i++){ var citems = await fetchBy('central', h.central[i]); if (citems.length){ items = citems; origemAtual = 'central'; break; } } } if (!items.length){ var h2 = await resolveHier(); for (var j=0;j<h2.almox.length;j++){ var aitems = await fetchBy('almoxarifado', h2.almox[j]); if (aitems.length){ items = aitems; origemAtual = 'almoxarifado'; break; } } } if (!items.length){ var h3 = await resolveHier(); for (var k=0;k<h3.sub.length;k++){ var sitems = await fetchBy('sub_almoxarifado', h3.sub[k]); if (sitems.length){ items = sitems; origemAtual = 'sub_almoxarifado'; break; } } } if (!items.length){ var g = await fetchGlobal(); if (g.length){ items = g; origemAtual = 'produto'; } } var hoje = new Date(); var mapped = items.map(function(l){ var df = parseDateFlexible(l.data_fabricacao); var dv = parseDateFlexible(l.data_vencimento); var status = '-'; var vencStr = '-'; if (dv && !isNaN(dv)){ vencStr = dv.toLocaleDateString('pt-BR'); var diffMs = dv.getTime() - hoje.getTime(); var dias = Math.ceil(diffMs/(1000*60*60*24)); if (dias < 0) status = 'Vencido'; else if (dias <= 30) status = 'Vence em '+String(dias)+' dias'; else status = 'Válido'; } return { numero_lote: String(l.numero_lote||'-'), venc: vencStr, status: status }; }); setLotes(mapped); }catch(_){ setLotes([]); } }
    async function registrarConsumo(){ if (!produto) { setConsumoStatus('Selecione um produto primeiro.'); return; } var pid = normalizeIdStr(produto && (produto.id!=null? produto.id : (produto._id || produto._id_str))); var valor = parseFloat(String(consumoQtd||'').replace(',','.')); if (!valor || !(valor>0)){ setConsumoStatus('Informe uma quantidade maior que zero.'); return; } try{ await window.fetchJson('/api/setor/registro', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ produto_id: pid, saida_dia: valor }) }); setConsumoStatus('Consumo registrado.'); setConsumoQtd(''); carregarEstoque(produto); carregarResumoDia(produto); }catch(_){ setConsumoStatus('Erro ao registrar consumo.'); } }

    var resultadosList = (resultados.length? h('div',{className:'list-group'}, resultados.map(function(p,idx){ return h('a',{href:'#', key:String(idx), className:'list-group-item list-group-item-action', onClick:function(e){ e.preventDefault(); selecionarProduto(p); }}, [ h('div',{className:'d-flex w-100 justify-content-between'}, [ h('h6',{className:'mb-1'}, String(p.nome||p.descricao||'')), h('small',null, String(p.codigo||'')) ]), h('small',{className:'text-muted'}, String(p.categoria_nome||'')) ]); })) : (loadingBusca? h('div',{className:'text-muted'}, 'Carregando...') : h('div',{className:'text-muted'}, 'Nenhum produto encontrado.')));

    var produtoInfo = (produto? h('div',{className:'row'}, [ h('div',{className:'col-12 col-md-6'}, [ h('strong',null,'Nome:'), ' ', String(produto.nome||'-') ]), h('div',{className:'col-12 col-md-3'}, [ h('strong',null,'Código:'), ' ', String(produto.codigo||'-') ]), h('div',{className:'col-12 col-md-3'}, [ h('strong',null,'Unidade:'), ' ', String(produto.unidade_medida||'-') ]) ]) : null);

    var estoqueRows = [
      h('div',{className:'col-12 col-md-4'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Quantidade total'), h('div',{className:'h5 mb-0'}, String((estoque.total||0).toLocaleString('pt-BR')) + (estoque.unidade? ' '+estoque.unidade : '') ) ])),
      h('div',{className:'col-6 col-md-4'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Disponível'), h('div',{className:'h5 mb-0'}, String((estoque.disponivel||0).toLocaleString('pt-BR')) + (estoque.unidade? ' '+estoque.unidade : '') ) ])),
      h('div',{className:'col-6 col-md-4'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Reservado'), h('div',{className:'h5 mb-0'}, String((estoque.reservado||0).toLocaleString('pt-BR')) + (estoque.unidade? ' '+estoque.unidade : '') ) ])),
      h('div',{className:'col-12'}, h('small',{className:'text-muted'}, 'Atualizado em: '+String(estoque.atualizado||'-')) )
    ];
    var resumoRows = [
      h('div',{className:'col-6 col-lg-3'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Recebido (Almox)'), h('div',{className:'h5 mb-0'}, String(resumo.almox.toLocaleString('pt-BR')) ) ])),
      h('div',{className:'col-6 col-lg-3'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Recebido (Sub)'), h('div',{className:'h5 mb-0'}, String(resumo.sub.toLocaleString('pt-BR')) ) ])),
      h('div',{className:'col-6 col-lg-3'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Usado hoje'), h('div',{className:'h5 mb-0'}, String(resumo.usado.toLocaleString('pt-BR')) ) ])),
      h('div',{className:'col-6 col-lg-3'}, h('div',{className:'border rounded p-2 bg-white h-100'}, [ h('div',{className:'text-muted small'}, 'Disponível'), h('div',{className:'h5 mb-0'}, String(resumo.disp.toLocaleString('pt-BR')) ) ]))
    ];
    var lotesBody = (lotes.length? lotes.map(function(l,idx){ var cls = (l.status==='Vencido')? 'table-danger' : (String(l.status||'').indexOf('Vence em')===0? 'table-warning' : ''); return h('tr',{key:String(idx), className:cls}, [ h('td',null, l.numero_lote||'-'), h('td',null, l.venc||'-'), h('td',null, l.status||'-') ]); }) : [ h('tr',{key:'empty'}, h('td',{colSpan:3}, h('div',{className:'text-muted'}, 'Sem lotes cadastrados.')) ) ]);
    var estoqueCard = (produto? h('div',{className:'border rounded p-3 bg-light'}, [
      h('div',{className:'d-flex align-items-center mb-2'}, [ h('i',{className:'fas fa-warehouse me-2'}), h('strong',null,'Estoque no meu setor:') ]),
      h('div',{className:'small mb-2'}, [ h('strong',null,'Setor atual:'), ' ', h('span',null, setorNome || '-') ]),
      h('div',null, h('div',{className:'row g-3'}, estoqueRows)),
      h('div',{className:'mt-2'}, [
        h('div',{className:'d-flex align-items-center mb-2'}, [ h('i',{className:'fas fa-calendar-day me-2'}), h('strong',null,'Resumo do dia:') ]),
        h('div',null, h('div',{className:'row g-3'}, resumoRows)),
        h('form',{className:'mt-2', onSubmit:function(e){ e.preventDefault(); registrarConsumo(); }}, [
          h('div',{className:'input-group input-group-sm', style:{maxWidth:'260px'}}, [ h('span',{className:'input-group-text'}, 'Usado hoje'), h('input',{type:'number', step:'0.01', min:'0', className:'form-control', placeholder:'0', value:consumoQtd, onChange:function(e){ setConsumoQtd(e.target.value); } }), h('button',{className:'btn btn-outline-danger', type:'submit'}, 'Registrar') ]),
          h('div',{className:'small mt-1'}, consumoStatus || '')
        ])
      ]),
      h('div',{className:'mt-2'}, [
        h('div',{className:'d-flex align-items-center mb-2'}, [ h('i',{className:'fas fa-tags me-2'}), h('strong',null,'Lotes no setor (validade):') ]),
        h('div',{className:'table-responsive'}, h('table',{className:'table table-sm mb-0'}, [ h('thead',null, h('tr',null, [ h('th',null,'Lote'), h('th',null,'Data de Vencimento'), h('th',null,'Status') ])), h('tbody',null, lotesBody) ]))
      ])
    ]) : null);

    return h('div',{className:'container-fluid'}, [
      h('div',{className:'row mb-3'}, h('div',{className:'col-12'}, [ h('h4',{className:'mb-0'}, [ h('i',{className:'fas fa-clipboard-list me-2'}), 'Gestão do Setor (Operador)' ]), h('small',{className:'text-muted'}, 'Visualize o estoque do seu setor e os lotes com validade por produto.') ])),
      h('div',{className:'row'}, [
        h('div',{className:'col-12 col-lg-6'}, h('div',{className:'card'}, [ h('div',{className:'card-header'}, h('h5',{className:'card-title mb-0'}, [ h('i',{className:'fas fa-search me-2'}), 'Selecionar Produto' ])), h('div',{className:'card-body'}, [ h('div',{className:'input-group mb-3'}, [ h('input',{type:'text', className:'form-control', id:'busca-produto-react', placeholder:'Buscar por nome, código ou descrição...', value:termo, onChange:function(e){ setTermo(e.target.value); }}), h('button',{className:'btn btn-primary', onClick:function(){ var s = String(termo||'').trim(); if (!s){ window.fetchJson('/api/produtos?per_page=10').then(function(d){ setResultados(Array.isArray(d.items)? d.items : []); }); return; } setLoadingBusca(true); window.fetchJson('/api/produtos?search='+encodeURIComponent(s)+'&per_page=10').then(function(d){ setResultados(Array.isArray(d.items)? d.items : []); }).catch(function(){ setResultados([]); }).finally(function(){ setLoadingBusca(false); }); }}, h('i',{className:'fas fa-search'}) ) ]), resultadosList ]) ])),
        h('div',{className:'col-12 col-lg-6'}, h('div',{className:'card', style:{display: produto? '' : 'none'}}, [ h('div',{className:'card-header d-flex justify-content-between align-items-center'}, [ h('h5',{className:'card-title mb-0'}, [ h('i',{className:'fas fa-box me-2'}), 'Produto Selecionado' ]), h('button',{className:'btn btn-sm btn-outline-secondary', onClick:function(){ setProduto(null); setResultados([]); setConsumoStatus(''); }}, 'Trocar') ]), h('div',{className:'card-body'}, [ produtoInfo, estoqueCard ]) ]))
      ])
    ]);
  }
  function mountOperadorSetor(){
    var rootEl = document.getElementById('operador-setor-root');
    if (!rootEl){ rootEl = document.createElement('div'); rootEl.id = 'operador-setor-root'; document.body.appendChild(rootEl); }
    var root = ReactDOM.createRoot(rootEl);
    root.render(h(OperadorSetorPage));
  }
  window.PluckApp.mountOperadorSetor = mountOperadorSetor;
})();
