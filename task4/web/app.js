'use strict';
const $=id=>document.getElementById(id);
const usd=cents=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
let data,selected,chart,catalog=[],bookIds=null,selectionVersion=0;
const cell=(row,text,cls)=>{const td=document.createElement('td');td.textContent=text;if(cls)td.className=cls;row.append(td);};
function renderBooks(){
 const q=$('book-search').value.toLocaleLowerCase();
 const rows=catalog.filter(b=>(bookIds===null||bookIds.includes(b.id))&&[b.title,b.author,b.genre].join(' ').toLocaleLowerCase().includes(q));
 $('books').replaceChildren();
 for(const b of rows){const tr=document.createElement('tr');[b.id,b.title,b.author,b.year??'—'].forEach(v=>cell(tr,v));$('books').append(tr);}
 $('catalog-count').textContent=`Показано ${rows.length} из ${catalog.length} книг`;
}
function renderChart(){
 const from=$('from').value,to=$('to').value;
 if(from&&to&&from>to){$('range-total').textContent='Начало периода должно быть не позже конца.';return;}
 const days=selected.daily_revenue.filter(d=>(!from||d.date>=from)&&(!to||d.date<=to));
 if(chart)chart.destroy();
 chart=new Chart($('revenue-chart'),{type:'line',data:{labels:days.map(d=>d.date),datasets:[{label:'Выручка USD',data:days.map(d=>d.revenue_cents/100),borderColor:'#167a6b',backgroundColor:'#167a6b14',borderWidth:1.6,pointRadius:0,pointHoverRadius:4,fill:true,tension:0}]},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>usd(Math.round(ctx.parsed.y*100))}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:6,maxRotation:0,font:{size:10},callback:function(v){return this.getLabelForValue(v).slice(0,7);}}},y:{beginAtZero:true,grid:{color:'#edf1f2'},ticks:{maxTicksLimit:5,font:{size:10},callback:v=>'$'+v.toLocaleString('en-US')}}}}});
 $('range-total').textContent=`За выбранный период: ${usd(days.reduce((sum,d)=>sum+d.revenue_cents,0))} · ${days.length} дней`;
}
async function selectStore(name){
 const version=++selectionVersion;catalog=[];
 selected=data.stores.find(s=>s.store===name);if(!selected)throw Error('Неизвестный магазин');
 document.querySelectorAll('#stores button').forEach(b=>b.setAttribute('aria-current',String(b.textContent===name)));
 $('period').textContent=`${name} · ${selected.audit.date_min} — ${selected.audit.date_max}`;
 $('revenue').textContent=usd(selected.total_revenue_cents);$('users').textContent=selected.unique_users.toLocaleString('ru');$('authors').textContent=selected.unique_author_sets;$('sold').textContent=selected.total_books_sold.toLocaleString('ru');$('orders').textContent=`${selected.order_count.toLocaleString('ru')} заказов`;
 $('top-days').replaceChildren();for(const day of selected.top_days){const row=document.createElement('tr');cell(row,day.date);cell(row,usd(day.revenue_cents),'num');$('top-days').append(row);}
 $('popular').textContent=selected.most_popular_author_sets.map(a=>a.authors.join(', ')).join(' / ');$('popular-count').textContent=selected.most_popular_author_sets.map(a=>`${a.books_sold} проданных экземпляров`).join('; ');
 $('buyer').textContent=selected.top_customers.map(c=>c.names.join(' / ')).join('; ');$('buyer-ids').textContent='Все ID: '+selected.top_customers.map(c=>JSON.stringify(c.user_ids)).join('; ');$('buyer-spent').textContent=selected.top_customers.map(c=>usd(c.total_spent_cents)).join('; ');
 $('audit').textContent=`Заказов в источнике: ${selected.audit.orders_input_rows}. Исключено: ${selected.audit.orders_quarantined}. Неразрешённых пар пользователей: ${selected.audit.identity_unresolved_candidate_pairs}. Записей пользователей до объединения: ${selected.user_record_count}.`;
 $('from').value=selected.audit.date_min;$('to').value=selected.audit.date_max;renderChart();bookIds=null;$('book-search').value='';
 renderBooks();const response=await fetch(`catalog-${name}.json`);if(!response.ok)throw Error('Не загружен каталог '+name);const loaded=await response.json();if(version!==selectionVersion)return;catalog=loaded;renderBooks();
}
function message(text,kind='assistant'){const div=document.createElement('div');div.className='message '+kind;div.textContent=text;$('chat-log').append(div);div.scrollIntoView({block:'nearest'});return div;}
async function applyAction(a){if(a.type!=='set_view')return;if(a.store!==selected.store)await selectStore(a.store);if(a.clear){bookIds=null;$('book-search').value='';$('from').value=selected.audit.date_min;$('to').value=selected.audit.date_max;}if(a.from)$('from').value=a.from;if(a.to)$('to').value=a.to;if(a.query!==undefined)$('book-search').value=a.query;if(a.book_ids!==undefined)bookIds=a.book_ids;renderBooks();renderChart();}
async function submitQuestion(event){event.preventDefault();const text=$('question').value.trim();if(!text)return;message(text,'user');$('question').value='';$('send').disabled=true;
 try{const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,store:selected.store})});const result=await response.json();if(!response.ok)throw Error(result.error||'Ошибка сервера');const div=message(result.answer);if(result.tools?.length){const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Запросы и проверяемые результаты';const pre=document.createElement('pre');pre.textContent=JSON.stringify(result.tools,null,2);details.append(summary,pre);div.append(details);}for(const action of result.actions||[])await applyAction(action);
 }catch(error){message('Не удалось получить ответ: '+error.message);}finally{$('send').disabled=false;}}
async function init(){try{const response=await fetch('data.json');if(!response.ok)throw Error('Не удалось загрузить расчёты');data=await response.json();for(const store of data.stores){const b=document.createElement('button');b.textContent=store.store;b.onclick=()=>selectStore(store.store).catch(showError);$('stores').append(b);}await selectStore(data.stores[0].store);
 $('from').onchange=renderChart;$('to').onchange=renderChart;$('reset').onclick=()=>{$('from').value=selected.audit.date_min;$('to').value=selected.audit.date_max;renderChart();};$('book-search').oninput=renderBooks;$('clear-books').onclick=()=>{bookIds=null;$('book-search').value='';renderBooks();};$('chat-form').onsubmit=submitQuestion;document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>{$('question').value=b.dataset.question;$('question').focus();});
 try{const r=await fetch('/api/status');const status=await r.json();$('ai-status').textContent=status.configured?`Модель: ${status.model}. Подключение проверяется при запросе.`:'AI пока не подключён. Расчёты и графики доступны; настоящее подключение модели ещё требуется завершить.';}catch{$('ai-status').textContent='Статические расчёты доступны. Подключение AI сейчас недоступно.';}
 }catch(e){showError(e);}}
function showError(error){$('error').hidden=false;$('error').textContent=error.message;}
init();
