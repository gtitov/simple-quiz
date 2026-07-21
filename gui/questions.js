const password = sessionStorage.getItem("teacherPassword") || "";
let questions = [], selectedId = null;
const $ = id => document.getElementById(id);
const api = path => `${path}${path.includes("?") ? "&" : "?"}password=${encodeURIComponent(password || "")}`;

function showMessage(text, error=false) { $("message").textContent=text; $("message").className=error?"message error":"message"; }
async function request(path, options) { const response=await fetch(api(path),options); const data=await response.json(); if(!response.ok) throw new Error(data.detail||"Ошибка запроса"); return data; }
function answerType(q) { return Array.isArray(q.answer)?"multiple":q.options?"single":"text"; }
function renderList() {
  const query=$("search").value.trim().toLowerCase();
  const filtered=questions.filter(q=>[q.question,q.topic,q.author].some(v=>(v||"").toLowerCase().includes(query)));
  $("count").textContent=`Вопросов: ${questions.length} · включено: ${questions.filter(q=>q.enabled!==false).length}`; $("question-list").innerHTML="";
  if(!filtered.length){$("question-list").innerHTML='<div class="empty">Вопросы не найдены</div>';return;}
  filtered.forEach(q=>{const button=document.createElement("button");button.type="button";button.className=`list-item${q.id===selectedId?" active":""}${q.enabled===false?" disabled-question":""}`;button.textContent=q.question;const meta=document.createElement("small");meta.textContent=`${q.enabled===false?"Выключен · ":""}${q.topic||"Без темы"} · ${answerType(q)==="text"?"текст":"варианты"}`;button.appendChild(meta);button.onclick=()=>editQuestion(q.id);$("question-list").appendChild(button);});
}
function addOption(value="",checked=false) {
  const row=document.createElement("div");row.className="option-row";
  const choice=document.createElement("input");choice.className="correct-option";choice.type=$("answer-type").value==="multiple"?"checkbox":"radio";choice.name="correct-option";choice.checked=checked;
  const input=document.createElement("input");input.className="option-value";input.value=value;input.placeholder="Вариант ответа";input.required=true;
  const remove=document.createElement("button");remove.type="button";remove.className="danger";remove.textContent="×";remove.onclick=()=>row.remove();
  row.append(choice,input,remove);$("options").appendChild(row);
}
function updateType(clear=true){const isText=$("answer-type").value==="text";$("text-answer-wrap").hidden=!isText;$("options-wrap").hidden=isText;if(!isText&&clear){$("options").innerHTML="";addOption();addOption();}}
function resetForm(){selectedId=null;$("question-form").reset();$("enabled").checked=true;$("options").innerHTML="";$("form-title").textContent="Новый вопрос";$("delete-question").hidden=true;updateType(false);showMessage("");renderList();$("question").focus();}
function editQuestion(id){const q=questions.find(item=>item.id===id);selectedId=id;$("form-title").textContent=`Вопрос №${id}`;$("question").value=q.question||"";$("topic").value=q.topic||"";$("author").value=q.author||"";$("picture").value=q.picture||"";$("enabled").checked=q.enabled!==false;$("answer-type").value=answerType(q);$("text-answer").value=answerType(q)==="text"?q.answer:"";$("options").innerHTML="";(q.options||[]).forEach(option=>addOption(option,Array.isArray(q.answer)?q.answer.includes(option):q.answer===option));updateType(false);$("delete-question").hidden=false;showMessage("");renderList();}
function formData(){const type=$("answer-type").value,rows=[...document.querySelectorAll(".option-row")],options=rows.map(r=>r.querySelector(".option-value").value.trim()).filter(Boolean);let answer=$("text-answer").value.trim();if(type==="single")answer=rows.find(r=>r.querySelector(".correct-option").checked)?.querySelector(".option-value").value.trim()||"";if(type==="multiple")answer=rows.filter(r=>r.querySelector(".correct-option").checked).map(r=>r.querySelector(".option-value").value.trim());return{question:$("question").value,topic:$("topic").value,author:$("author").value,picture:$("picture").value,enabled:$("enabled").checked,answer_type:type,options,answer};}
async function loadQuestions(){if(!password){window.location.replace("index.html");return;}try{questions=await request("/teacher/questions");$("topics").replaceChildren(...[...new Set(questions.map(q=>q.topic).filter(Boolean))].map(t=>{const option=document.createElement("option");option.value=t;return option;}));renderList();showMessage("");}catch(error){sessionStorage.removeItem("teacherPassword");window.location.replace("index.html");}}
$("question-form").onsubmit=async event=>{event.preventDefault();try{const path=selectedId?`/teacher/questions/${selectedId}`:"/teacher/questions";await request(path,{method:selectedId?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(formData())});await loadQuestions();resetForm();showMessage("Вопрос сохранён");}catch(error){showMessage(error.message,true);}};
$("delete-question").onclick=async()=>{if(!selectedId||!confirm("Удалить этот вопрос?"))return;try{await request(`/teacher/questions/${selectedId}`,{method:"DELETE"});await loadQuestions();resetForm();showMessage("Вопрос удалён");}catch(error){showMessage(error.message,true);}};
$("answer-type").onchange=()=>updateType(true);$("add-option").onclick=()=>addOption();$("new-question").onclick=resetForm;$("search").oninput=renderList;loadQuestions();
