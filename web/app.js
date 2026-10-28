'use strict';
const $ = id => document.getElementById(id);
const number = value => Number(value).toLocaleString('en-US', {maximumFractionDigits:2});
const colors = ['#315681','#7a9e8e','#c19859','#756b9d','#6c9eb8','#ab7781','#828f65','#77958f'];
let mineReport, mineChart, source = '', batch = 0, mineVersion = 0, contactVersion = 0;

function metric(parent, title, value) {
  const box = document.createElement('div'); box.className = 'metric';
  const label = document.createElement('span'); label.textContent = title;
  const amount = document.createElement('strong'); amount.textContent = value;
  box.append(label, amount); parent.append(box);
}

function row(parent, values) {
  const tr = document.createElement('tr');
  for (const value of values) { const td = document.createElement('td'); td.textContent = value; tr.append(td); }
  parent.append(tr); return tr;
}

function query() {
  const parameters = new URLSearchParams();
  for (const key of ['degree','iqr','z','window','moving_percent','alpha']) parameters.set(key, $(key).value);
  if (source) parameters.set('source', source);
  return parameters;
}

async function readJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request could not be completed');
  return data;
}

async function refreshMines() {
  const version = ++mineVersion;
  $('mine-error').textContent = ''; $('refresh-sheet').disabled = true; $('pdf').disabled = true;
  try {
    const result = await readJson('/api/task5?' + query());
    if (version !== mineVersion) return;
    mineReport = result;
    const selection = $('mine-select').value;
    $('mine-select').replaceChildren();
    for (const name of ['Total', ...result.series.filter(s => s.name !== 'Total').map(s => s.name)]) {
      const option = document.createElement('option'); option.value = name; option.textContent = name; $('mine-select').append(option);
    }
    if (result.series.some(s => s.name === selection)) $('mine-select').value = selection;
    $('source-status').textContent = source ? 'Live Google Sheets export' : 'Saved sample';
    $('mine-period').textContent = `${result.dates[0]} — ${result.dates.at(-1)} · ${result.dates.length} days`;
    $('mine-table').replaceChildren();
    for (const s of result.series) row($('mine-table'), [s.name,number(s.mean),number(s.standard_deviation),number(s.median),number(s.iqr),s.anomalies.length]);
    $('analysis-note').textContent = result.notes.moving_average + ' ' + result.notes.grubbs;
    renderMineChart();
    $('pdf').disabled = false;
  } catch (error) { $('mine-error').textContent = error.message; }
  finally { if (version === mineVersion) $('refresh-sheet').disabled = false; }
}

function renderMineChart() {
  if (!mineReport) return;
  const mode = $('chart-type').value;
  $('mine-select').disabled = mode === 'stacked';
  if (mode === 'stacked') $('mine-select').value = 'Total';
  const series = mineReport.series.find(s => s.name === $('mine-select').value);
  const anomalyIndices = new Set(series.anomalies.map(a => a.index));
  $('chart-title').textContent = `${series.name} · daily output`;
  $('mine-metrics').replaceChildren();
  metric($('mine-metrics'), 'Mean daily output, t', number(series.mean));
  metric($('mine-metrics'), 'Standard deviation, t', number(series.standard_deviation));
  metric($('mine-metrics'), 'Median output, t', number(series.median));
  metric($('mine-metrics'), 'Anomalous observations', series.anomalies.length);
  let datasets;
  if (mode === 'stacked') {
    datasets = mineReport.series.filter(s => s.name !== 'Total').map((s,i) => ({label:s.name,data:s.values,backgroundColor:colors[i%colors.length],borderWidth:0,stack:'mines'}));
  } else {
    datasets = [{label:series.name,data:series.values,borderColor:colors[0],backgroundColor:mode==='bar'?colors[0]:'#31568115',pointRadius:ctx=>anomalyIndices.has(ctx.dataIndex)?4:0,pointBackgroundColor:ctx=>anomalyIndices.has(ctx.dataIndex)?'#b83240':colors[0],borderWidth:1.8,tension:0}];
  }
  if (mode === 'stacked') datasets.push({label:'Total outliers',type:'line',data:series.values.map((v,i)=>anomalyIndices.has(i)?v:null),showLine:false,pointRadius:4,pointBackgroundColor:'#b83240',stack:'markers',order:0});
  if (series.trend) datasets.push({label:`Polynomial trend (${ $('degree').value })`,type:'line',data:series.trend,borderColor:'#b47829',borderDash:[6,4],pointRadius:0,borderWidth:2,stack:'trend',order:0});
  if (mineChart) mineChart.destroy();
  mineChart = new Chart($('mine-chart'), {type:mode==='line'?'line':'bar',data:{labels:mineReport.dates,datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:mode==='stacked'||!!series.trend,position:'bottom'}},scales:{x:{stacked:mode==='stacked',grid:{display:false},ticks:{maxTicksLimit:8,maxRotation:0}},y:{stacked:mode==='stacked',beginAtZero:true,title:{display:true,text:'Tonnes / day'},grid:{color:'#eaf0f4'}}}}});
  $('anomaly-table').replaceChildren();
  for (const anomaly of series.anomalies) row($('anomaly-table'), [anomaly.date,number(anomaly.value),anomaly.kind,anomaly.tests.join(', ')]);
  if (!series.anomalies.length) row($('anomaly-table'), ['No observations exceeded the thresholds.','','','']);
}

async function refreshContacts() {
  const version = ++contactVersion;
  $('contact-error').textContent = '';
  $('next').disabled = true; $('previous').disabled = true;
  try {
    const parameters = new URLSearchParams({locale:$('locale').value,seed:$('seed').value,batch:String(batch),size:$('page-size').value});
    const result = await readJson('/api/task6?' + parameters);
    if (version !== contactVersion) return;
    $('contacts-table').replaceChildren();
    for (const user of result.users) {
      const tr = row($('contacts-table'), ['', '', user.address, `${user.latitude}, ${user.longitude}`,`${user.height_cm} cm · ${user.weight_kg} kg\n${user.eye_color}`]);
      const name = document.createElement('strong'); name.textContent = user.full_name;
      const id = document.createElement('small'); id.textContent = `#${user.index}`; tr.children[0].append(id,name);
      const mail = document.createElement('span'); mail.textContent = user.email;
      const phone = document.createElement('small'); phone.textContent = user.phone; tr.children[1].append(mail,phone);
    }
    $('batch-label').textContent = `Batch ${batch+1}`;
    $('generation-time').textContent = `${result.users.length} users · ${number(result.seconds*1000)} ms · ${number(result.users_per_second)} users/s for this request`;
  } catch (error) { $('contact-error').textContent = error.message; }
  finally { if (version === contactVersion) { $('next').disabled = false; $('previous').disabled = batch===0; } }
}

async function refreshSummary() {
  const result = await readJson('/api/task35');
  $('summary-metrics').replaceChildren();
  metric($('summary-metrics'), 'Books imported',number(result.books));
  metric($('summary-metrics'), 'Publication years',number(result.summary_rows));
  metric($('summary-metrics'), 'Database integrity',result.integrity);
  metric($('summary-metrics'), 'EUR → USD rate','1.20');
  const keys = ['publication_year','book_count','average_price'];
  $('summary-head').replaceChildren(); const head = document.createElement('tr');
  for (const key of keys) { const th = document.createElement('th'); th.textContent = key.replaceAll('_',' '); head.append(th); }
  $('summary-head').append(head); $('summary-table').replaceChildren();
  for (const item of result.summary) row($('summary-table'),keys.map(key=>item[key]));
  $('book-preview').replaceChildren();
  for (const book of result.example_books) row($('book-preview'),[book.id,book.title,book.publication_year,book.original_price,book.currency,(book.price_usd_mills/1000).toFixed(3)]);
}

async function downloadReport() {
  $('mine-error').textContent = ''; $('pdf').disabled = true;
  try {
    const response = await fetch('/api/task5/report.pdf?' + query());
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || 'The PDF report could not be generated');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = 'mine-production-report.pdf';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { $('mine-error').textContent = error.message; }
  finally { $('pdf').disabled = false; }
}

function showView() {
  const name = location.hash.slice(1) || 'home';
  for (const section of document.querySelectorAll('.view')) section.hidden = section.id !== name;
  if (name === 'mines' && !mineReport) refreshMines();
  if (name === 'contacts') refreshContacts();
  if (name === 'summary') refreshSummary().catch(error=>{$('summary-table').textContent=error.message;});
}

async function start() {
  const config = await readJson('/api/config');
  $('generator-link').href = config.sheet_url; $('sheet-source').value = config.sheet_url;
  $('refresh-sheet').onclick = () => { source=$('sheet-source').value.trim(); refreshMines(); };
  $('sample').onclick = () => {source='';refreshMines();};
  $('mine-select').onchange = renderMineChart; $('chart-type').onchange = renderMineChart;
  for (const key of ['degree','iqr','z','window','moving_percent','alpha']) $(key).onchange = refreshMines;
  $('pdf').onclick = downloadReport;
  for (const key of ['locale','seed','page-size']) $(key).onchange = () => {batch=0;refreshContacts();};
  $('next').onclick = () => {batch++;refreshContacts();};
  $('previous').onclick = () => {batch=Math.max(0,batch-1);refreshContacts();};
  window.addEventListener('hashchange',showView); showView();
}
start().catch(error=>{document.body.textContent=error.message;});
