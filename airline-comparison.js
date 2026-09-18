(function () {
  'use strict';
  const root = document.getElementById('airline-price-comparison');
  const data = window.airlineComparisonData;
  if (!root || !data) return;
  const $ = selector => root.querySelector(selector);
  const format = value => Math.round(value).toLocaleString('tr-TR') + ' TL';
  const mean = values => values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
  const normalize = value => value.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i');
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = { first: 'TK', second: 'PC', city: data.cities.find(c => c.name === 'İstanbul').id };
  const colors = ['#007fe8', '#1f9d8a'];
  const anchor = new Date(data.asOf + 'T12:00:00Z');
  const months = Array.from({length: 12}, (_, index) => {
    const date = new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth() - 12 + index, 1));
    return { key: date.toISOString().slice(0, 7), month: date.getUTCMonth(), label: date.toLocaleDateString('tr-TR', {month:'long',year:'numeric',timeZone:'UTC'}), short: date.toLocaleDateString('tr-TR', {month:'short',timeZone:'UTC'}), year: date.getUTCFullYear() };
  });
  const hash = text => Array.from(text).reduce((sum, c) => (sum * 31 + c.charCodeAt(0)) >>> 0, 17);
  const seasonal = [0.86,0.88,1.02,1.04,1.10,1.24,1.36,1.30,1.08,0.96,0.89,1.02];
  const domestic = [['İstanbul',1850],['Ankara',1740],['İzmir',1890],['Antalya',1920],['Trabzon',2250],['Gaziantep',2170]];
  const international = [['Berlin',4350],['Londra',4650],['Paris',4890],['Amsterdam',4490],['Roma',4250]];
  // Adapter boundary: replace this deterministic mock provider with API records.
  // No generated quote is a claim of a scheduled/direct service or historical sale.
  function getComparison(selection) {
    const city = data.cities.find(c => c.id === selection.city);
    const airlines = [selection.first, selection.second].map(id => data.airlines.find(a => a.id === id));
    const routes = domestic.filter(r => r[0] !== city.name).slice(0,5).map(r => ({destination:r[0],base:r[1],scope:'domestic'}))
      .concat(international.map(r => ({destination:r[0],base:r[1],scope:'international'})));
    const tableRoutes = airlines.every(a => a.domestic > 0) ? routes.filter(r => r.scope === 'domestic').slice(0,3).concat(routes.filter(r => r.scope === 'international').slice(0,2)) : routes.filter(r => r.scope === 'international');
    function quote(airline, route, index, offer) {
      const factor = airline[route.scope];
      if (!factor || !city.factor) return null;
      const variation = 0.96 + (hash(airline.id + city.name + route.destination + index) % 13) / 100;
      const connection = city.name === 'İstanbul' ? 0 : route.scope === 'international' ? 1050 : route.destination === 'İstanbul' ? 0 : 550;
      const baseline = (route.base * city.factor + connection) * factor;
      const trend = offer ? 0.76 : 0.86 + index * 0.013;
      const month = offer ? anchor.getUTCMonth() : months[index].month;
      return Math.round(baseline * seasonal[month] * trend * variation / 10) * 10 + 9;
    }
    const rows = routes.map((route, index) => ({...route, origin:city.name, date:'2026-09-' + String(20 + index).padStart(2,'0'), values:airlines.map(a => quote(a,route,12,true)), monthly:airlines.map(a => months.map((_,i) => quote(a,route,i)))}));
    const tableRows = tableRoutes.map(route => rows.find(r => r.destination === route.destination));
    const series = airlines.map((airline, ai) => ({airline, color:colors[ai], values:months.map((_, mi) => mean(tableRows.map(r => r.monthly[ai][mi]).filter(v => v !== null)))}));
    return {city,airlines,rows,tableRows,series};
  }
  let current;
  const widgets = [];
  function createPicker(key, label, items, placeholder) {
    const host = document.createElement('div');
    host.className = 'ac-picker';
    const id = 'ac-' + key;
    host.innerHTML = '<span class="ac-field-label" id="'+id+'-label">'+label+'</span><button type="button" class="ac-picker-trigger" aria-labelledby="'+id+'-label '+id+'-value" aria-expanded="false" aria-controls="'+id+'-popup" aria-haspopup="dialog"><span id="'+id+'-value" class="ac-picker-value"></span><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></button><div class="ac-picker-popup" id="'+id+'-popup" role="dialog" aria-label="'+label+' seçimi" hidden><input class="ac-picker-search" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="'+id+'-list" aria-label="'+label+' ara" placeholder="'+placeholder+'" autocomplete="off"><div id="'+id+'-list" role="listbox" aria-label="'+label+' seçenekleri" class="ac-options"></div><p class="ac-picker-empty" role="status" hidden>Sonuç bulunamadı. Farklı bir ad deneyin.</p></div>';
    $('.ac-filters').append(host);
    const trigger = host.querySelector('button');
    const popup = host.querySelector('.ac-picker-popup');
    const input = host.querySelector('input');
    const list = host.querySelector('[role=listbox]');
    let active = -1;
    let options = [];
    const other = () => key === 'first' ? state.second : key === 'second' ? state.first : null;
    function sync() {
      const item = items.find(i => i.id === state[key]);
      host.querySelector('.ac-picker-value').innerHTML = (item.logo ? '<img src="'+item.logo+'" width="25" height="19" alt="">' : '<span class="ac-picker-symbol" aria-hidden="true">'+(key === 'city' ? '⌖' : item.id)+'</span>') + '<span>'+escape(item.short || item.name)+'</span>';
    }
    function mark(index) {
      options.forEach(o => o.classList.remove('is-active'));
      active = index;
      if (options[index]) {
        options[index].classList.add('is-active');
        input.setAttribute('aria-activedescendant', options[index].id);
        options[index].scrollIntoView({block:'nearest'});
      } else input.removeAttribute('aria-activedescendant');
    }
    function filter() {
      const query = normalize(input.value.trim());
      const filtered = items.filter(item => normalize(item.name + ' ' + (item.short || '') + ' ' + item.id + ' ' + (item.codes || '')).includes(query));
      list.innerHTML = filtered.map(item => '<button type="button" role="option" tabindex="-1" id="'+id+'-option-'+item.id+'" data-value="'+item.id+'" aria-selected="'+(state[key] === item.id)+'" '+(item.id === other() ? 'disabled' : '')+'><span>'+escape(item.name)+'</span><small>'+escape(item.codes || item.id)+(item.id === other() ? ' · seçili' : '')+'</small></button>').join('');
      host.querySelector('.ac-picker-empty').hidden = filtered.length !== 0;
      options = Array.from(list.querySelectorAll('button:not(:disabled)'));
      active = -1;
      input.removeAttribute('aria-activedescendant');
    }
    function close(restore) {
      popup.hidden = true;
      trigger.setAttribute('aria-expanded','false');
      input.setAttribute('aria-expanded','false');
      if (restore) trigger.focus();
    }
    function open() {
      widgets.forEach(w => w.close(false));
      popup.hidden = false;
      input.value = '';
      filter();
      trigger.setAttribute('aria-expanded','true');
      input.setAttribute('aria-expanded','true');
      input.focus();
    }
    function select(option) {
      if (!option || option.disabled) return;
      state[key] = option.dataset.value;
      sync(); close(true); render();
    }
    trigger.addEventListener('click', () => popup.hidden ? open() : close(true));
    trigger.addEventListener('keydown', e => {if (e.key === 'ArrowDown') {e.preventDefault();open();mark(0);}});
    input.addEventListener('input', filter);
    list.addEventListener('click', e => select(e.target.closest('[role=option]')));
    popup.addEventListener('keydown', e => {
      if (e.key === 'Escape') {e.preventDefault();close(true);}
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {e.preventDefault();mark(options.length ? (active + (e.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length : -1);}
      if (e.key === 'Enter') {e.preventDefault();select(options[active < 0 ? 0 : active]);}
      if (e.key === 'Home' && e.ctrlKey) {e.preventDefault();mark(0);}
      if (e.key === 'End' && e.ctrlKey) {e.preventDefault();mark(options.length - 1);}
    });
    host.addEventListener('focusout', () => {setTimeout(() => {if (!host.contains(document.activeElement)) close(false);}, 0);});
    document.addEventListener('click', e => {if (!host.contains(e.target)) close(false);});
    widgets.push({close,sync}); sync();
  }
  const sortedAirlines = data.airlines.slice().sort((a,b) => a.name.localeCompare(b.name,'tr'));
  createPicker('first','1. havayolu',sortedAirlines,'Havayolu adı veya kodu ara');
  createPicker('second','2. havayolu',sortedAirlines,'Havayolu adı veya kodu ara');
  createPicker('city','Kalkış şehri',data.cities,'Şehir veya havalimanı kodu ara');
  function cheapest(result, ai, rows) {
    return rows.filter(r => r.values[ai] !== null).map(r => ({...r,airline:result.airlines[ai],price:r.values[ai]})).sort((a,b) => a.price - b.price)[0];
  }
  function summary(result, scope) {
    const rows = scope ? result.rows.filter(r => r.scope === scope) : result.tableRows;
    const choices = result.airlines.map((airline,ai) => {
      const values = rows.flatMap(r => r.monthly[ai]).filter(v => v !== null);
      return {airline, average:mean(values), cheapest:cheapest(result,ai,rows)};
    }).filter(s => s.cheapest).sort((a,b) => a.average - b.average);
    if (!choices.length) return (scope === 'domestic' ? 'Yurt içi' : scope === 'international' ? 'Yurt dışı' : 'Bu şehir') + ' için seçili havayollarına ait karşılaştırılabilir örnek fiyat bulunmuyor.';
    const s = choices[0];
    const context = scope === 'domestic' ? 'Yurt içi rotalarda' : scope === 'international' ? 'Yurt dışı rotalarda' : 'Seçili rotaların 12 aylık örnek verisinde';
    return context+' en uygun ortalamayı '+s.airline.name+' '+format(s.average)+' ile sunuyor; en ucuz uçuşu '+s.cheapest.origin+' – '+s.cheapest.destination+' rotasında '+format(s.cheapest.price)+'.';
  }
  function render() {
    current = getComparison(state);
    const {city,airlines,tableRows,series} = current;
    const best = airlines.map((_,i) => cheapest(current,i,tableRows)).filter(Boolean).sort((a,b) => a.price - b.price);
    $('.ac-recommendation').textContent = best.length ? best.map(b => b.airline.short+' ile '+b.origin+' – '+b.destination+' uçuşunu '+format(b.price)).join(', ')+' üzerinden karşılaştırın.' : city.name+' için farklı bir havayolu veya kalkış şehri seçin.';
    $('.ac-chart-title').textContent = city.name+' kalkışlı uçuşlar';
    $('.ac-period').textContent = months[0].label+' – '+months[11].label;
    $('.ac-legend').innerHTML = series.map(s => '<li><i style="color:'+s.color+'" aria-hidden="true"></i>'+escape(s.airline.short)+'<strong>'+ (mean(s.values.filter(v => v !== null)) === null ? 'Veri yok' : format(mean(s.values.filter(v => v !== null)))) +'</strong><span>ort.</span></li>').join('');
    $('.ac-table-heading span').textContent = tableRows.some(r => r.values.some(v => v !== null)) ? '5 rota · Tek yön / kişi' : 'Örnek fiyat bulunamadı';
    $('.ac-table thead').innerHTML = '<tr><th scope="col">Rota</th><th scope="col">Tarih</th>'+airlines.map((a,i) => '<th scope="col"><span class="ac-airline-heading" style="--ac-color:'+colors[i]+'">'+escape(a.short)+'</span><small>Tek yön fiyatı</small></th>').join('')+'</tr>';
    $('.ac-table tbody').innerHTML = tableRows.some(r => r.values.some(v => v !== null)) ? tableRows.map(row => '<tr><th scope="row">'+escape(row.origin)+' <span aria-hidden="true">→</span> '+escape(row.destination)+'<small>'+(row.scope === 'domestic' ? 'Yurt içi' : 'Yurt dışı')+'</small></th><td>'+new Date(row.date+'T12:00:00Z').toLocaleDateString('tr-TR',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'})+'</td>'+row.values.map((value,i) => '<td data-airline="'+escape(airlines[i].short)+'"'+(value !== null && (row.values[1-i] === null || value < row.values[1-i]) ? ' class="ac-best-price"' : '')+'>'+(value === null ? '<span class="ac-no-price">Veri yok</span>' : format(value))+'</td>').join('')+'</tr>').join('') : '<tr><td colspan="4" class="ac-empty">Bu seçim için örnek uçuş bulunmuyor. Farklı bir şehir veya havayolu seçin.</td></tr>';
    renderChart();
  }
  function svgElement(tag, attrs, text) {
    const element = document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attrs || {}).forEach(([key,value]) => element.setAttribute(key,value));
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function renderChart() {
    const host = $('.ac-chart');
    const tooltip = $('.ac-tooltip');
    host.querySelectorAll('svg,.ac-empty').forEach(e => e.remove());
    tooltip.hidden = true;
    const series = current.series.filter(s => s.values.some(v => v !== null));
    if (!series.length) {const empty=document.createElement('p');empty.className='ac-empty';empty.textContent='Bu seçim için aylık örnek fiyat bulunmuyor.';host.append(empty);return;}
    const width = Math.max(820, host.clientWidth), height = 326;
    const pad = {left:74,right:34,top:38,bottom:48};
    const values = series.flatMap(s => s.values).filter(v => v !== null);
    const lowValue = Math.min(...values), highValue = Math.max(...values);
    const step = Math.max(500,Math.ceil((highValue-lowValue)/4/500)*500);
    const low = Math.max(0,Math.floor((lowValue-step*0.4)/step)*step), high = Math.ceil((highValue+step*0.4)/step)*step;
    const x = i => pad.left + i*(width-pad.left-pad.right)/11;
    const y = v => pad.top + (high-v)/(high-low)*(height-pad.top-pad.bottom);
    const svg = svgElement('svg',{viewBox:'0 0 '+width+' '+height,width,height,'aria-label':current.city.name+' için 12 aylık ortalama fiyat karşılaştırması',role:'group'});
    for (let tick = low; tick <= high; tick += step) {
      svg.append(svgElement('line',{class:'fpc-grid',x1:pad.left,x2:width-pad.right,y1:y(tick),y2:y(tick)}));
      svg.append(svgElement('text',{class:'fpc-axis',x:pad.left-12,y:y(tick)+4,'text-anchor':'end'},format(tick)));
    }
    const crosshair=svgElement('line',{class:'fpc-crosshair',x1:0,x2:0,y1:pad.top,y2:height-pad.bottom,opacity:0});
    svg.append(crosshair);
    series.forEach(s => {
      svg.append(svgElement('path',{class:'fpc-line',stroke:s.color,d:s.values.map((v,i) => (i ? 'L' : 'M')+x(i)+' '+y(v)).join(' ')}));
      s.values.forEach((v,i) => {
        svg.append(svgElement('circle',{class:'fpc-dot',cx:x(i),cy:y(v),r:4,fill:s.color}));
        const other=series.find(o => o !== s);
        const offset = other && v < other.values[i] ? 19 : -12;
        svg.append(svgElement('text',{class:'ac-point-label',x:x(i),y:y(v)+offset,'text-anchor':'middle',fill:s.color},v.toLocaleString('tr-TR')));
      });
    });
    function show(index) {
      crosshair.setAttribute('x1',x(index));crosshair.setAttribute('x2',x(index));crosshair.setAttribute('opacity','1');
      tooltip.innerHTML='<p class="flight-price-compare__tooltip-title">'+months[index].label+'</p><ul>'+current.series.map(s => '<li><i style="background:'+s.color+'"></i><span>'+escape(s.airline.short)+'</span><strong>'+(s.values[index] === null ? 'Veri yok' : format(s.values[index]))+'</strong></li>').join('')+'</ul>';
      tooltip.hidden=false;
      tooltip.style.left=Math.max(4,Math.min(x(index)-tooltip.offsetWidth/2,width-tooltip.offsetWidth-4))+'px';
      tooltip.style.top='6px';
    }
    function hide() {tooltip.hidden=true;crosshair.setAttribute('opacity','0');}
    months.forEach((month,i) => {
      svg.append(svgElement('text',{class:'fpc-axis',x:x(i),y:height-23,'text-anchor':'middle'},month.short));
      svg.append(svgElement('text',{class:'fpc-axis',x:x(i),y:height-7,'text-anchor':'middle'},month.year));
      const hit=svgElement('rect',{class:'fpc-hit',x:x(i)-27,y:pad.top-20,width:54,height:height-pad.top-pad.bottom+40,tabindex:'0',role:'button','aria-label':month.label+': '+current.series.map(s => s.airline.short+' '+(s.values[i] === null ? 'veri yok' : format(s.values[i]))).join(',')});
      hit.addEventListener('pointerenter',()=>show(i));
      hit.addEventListener('focus',()=>show(i));
      hit.addEventListener('click',()=>show(i));
      hit.addEventListener('blur',hide);
      hit.addEventListener('keydown',e=>{if(e.key==='Escape'){hide();}if(e.key==='Enter'||e.key===' '){e.preventDefault();show(i);}if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();const hits=svg.querySelectorAll('.fpc-hit');hits[(i+(e.key==='ArrowRight'?1:11))%12].focus();}});
      svg.append(hit);
    });
    svg.addEventListener('pointerleave',hide);
    host.append(svg);
  }
  let resizeFrame;
  const observer = new ResizeObserver(() => {cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(renderChart);});
  render();observer.observe($('.ac-chart-scroll'));
}());
