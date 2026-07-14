const password=sessionStorage.getItem("teacherPassword")||"";let results=[];
const $=id=>document.getElementById(id);
function formatAnswer(value){if(Array.isArray(value))return value.length?value.join(", "):"Нет ответа";return value||"Нет ответа";}
function formatDate(value){
  if(!value)return "Дата неизвестна";
  const normalized=String(value).replace(/T(\d{2})-(\d{2})-(\d{2})$/,"T$1:$2:$3");
  const date=new Date(normalized);
  return Number.isNaN(date.getTime())?value:date.toLocaleString("ru-RU");
}
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));}
function render(){
  const student=$("student-filter").value.trim().toLowerCase(),topic=$("topic-filter").value;
  const filtered=results.filter(r=>(r.student||"").toLowerCase().includes(student)).map(r=>({...r,incorrect:r.incorrect.filter(q=>!topic||q.topic===topic)})).filter(r=>r.incorrect.length);
  $("summary").textContent=`Работ с ошибками: ${filtered.length} · Ошибок: ${filtered.reduce((sum,r)=>sum+r.incorrect.length,0)}`;$("results").innerHTML="";
  if(!filtered.length){$("results").innerHTML='<div class="card empty">По выбранным фильтрам неправильных ответов нет.</div>';return;}
  filtered.forEach(result=>{const card=document.createElement("details");card.className="card result-card";card.innerHTML=`<summary class="result-head"><span><strong>${escapeHtml(result.student)}</strong><br><small>${escapeHtml(formatDate(result.end_time))} · ${result.correct}/${result.total} правильных</small></span><span class="badge">${result.incorrect.length} ошибок · ${result.correct_percent}%</span></summary>`;result.incorrect.forEach(q=>{const block=document.createElement("div");block.className="incorrect";block.innerHTML=`<strong>${escapeHtml(q.question)}</strong><p class="stat">${escapeHtml(q.topic||"Без темы")}</p><div class="answers"><div class="given"><b>Ответ студента</b><br>${escapeHtml(formatAnswer(q.student_answer))}</div><div class="correct"><b>Правильный ответ</b><br>${escapeHtml(formatAnswer(q.correct_answer))}</div></div>`;card.appendChild(block);});$("results").appendChild(card);});
}
async function loadResults(){if(!password){window.location.replace("index.html");return;}$("message").textContent="Загрузка...";const response=await fetch(`/teacher/results?password=${encodeURIComponent(password||"")}`),data=await response.json();if(!response.ok){sessionStorage.removeItem("teacherPassword");window.location.replace("index.html");return;}results=data;const topics=[...new Set(results.flatMap(r=>r.incorrect.map(q=>q.topic)).filter(Boolean))].sort(),all=document.createElement("option");all.value="";all.textContent="Все темы";$("topic-filter").replaceChildren(all,...topics.map(t=>{const option=document.createElement("option");option.value=t;option.textContent=t;return option;}));$("message").textContent="";$("message").className="message";render();}
$("student-filter").oninput=render;$("topic-filter").onchange=render;$("reload").onclick=loadResults;loadResults();
