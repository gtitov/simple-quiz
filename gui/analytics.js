const password = sessionStorage.getItem("teacherPassword") || "";
const $ = id => document.getElementById(id);
if (!password) window.location.replace("index.html");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
}
function formatDate(value) {
  if (!value) return "Нет данных";
  const normalized = value.replace(/T(\d{2})-(\d{2})-(\d{2})$/, "T$1:$2:$3");
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ru-RU");
}
function metric(label, value, hint) {
  return `<article class="metric"><span>${label}</span><strong>${value}</strong><small>${hint}</small></article>`;
}
function bar(label, value, detail, danger=false) {
  return `<div class="bar-row"><div class="bar-label"><span>${escapeHtml(label)}</span><strong>${detail}</strong></div><div class="bar-track"><div class="bar-fill${danger?" danger":""}" style="width:${Math.max(2,value)}%"></div></div></div>`;
}
function renderAnalytics(data) {
  $("message").textContent = "";
  $("message").className = "message";
  $("analytics").hidden = false;
  $("updated").textContent = `обновлено ${new Date().toLocaleTimeString("ru-RU")}`;
  const s = data.summary;
  $("metrics").innerHTML = [
    metric("Попыток", s.attempts, `${s.students} студентов`),
    metric("Средний балл", `${s.average_score}%`, `медиана ${s.median_score}%`),
    metric("Успешность", `${s.pass_rate}%`, "результат от 50%"),
    metric("Вопросов в статистике", data.questions.length, `${data.topics.length} тем`)
  ].join("");
  const maxCount = Math.max(1, ...data.distribution.map(item => item.count));
  $("distribution").innerHTML = data.distribution.map(item => bar(item.label, item.count * 100 / maxCount, `${item.count}`)).join("");
  $("topics").innerHTML = data.topics.length ? data.topics.slice(0, 10).map(item => bar(item.topic, 100-item.accuracy, `${item.accuracy}% правильно`, true)).join("") : '<p class="empty">Нет данных</p>';
  $("questions").innerHTML = data.questions.length ? data.questions.slice(0, 30).map(item => `<tr><td>${escapeHtml(item.question)}</td><td>${escapeHtml(item.topic)}</td><td>${item.attempts}</td><td class="success">${item.accuracy}%</td><td class="fail">${item.incorrect}</td></tr>`).join("") : '<tr><td colspan="5" class="empty">Нет данных</td></tr>';
  $("students").innerHTML = data.students.length ? data.students.map(item => `<tr><td>${escapeHtml(item.student)}</td><td class="${item.percent>=50?"success":"fail"}">${item.percent}%</td><td>${item.correct} из ${item.total}</td><td>${formatDate(item.end_time)}</td></tr>`).join("") : '<tr><td colspan="4" class="empty">Нет данных</td></tr>';
}
async function loadAnalytics() {
  try {
    const response = await fetch(`/teacher/analytics?password=${encodeURIComponent(password)}`, { cache: "no-store" });
    if (!response.ok) {
      sessionStorage.removeItem("teacherPassword");
      window.location.replace("index.html");
      return;
    }
    renderAnalytics(await response.json());
  } catch {
    $("message").textContent = "Не удалось обновить аналитику";
    $("message").className = "message error";
  }
}

loadAnalytics();
setInterval(loadAnalytics, 10000);
