const password = sessionStorage.getItem("teacherPassword") || "";
const $ = id => document.getElementById(id);
if (!password) window.location.replace("index.html");

function formatDate(value) {
  if (!value) return "Нет данных";
  const normalized = String(value).replace(/T(\d{2})-(\d{2})-(\d{2})$/, "T$1:$2:$3");
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ru-RU");
}
function formatRemaining(attempt) {
  const seconds = Math.max(0, attempt.remaining_seconds || 0);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char])); }

async function loadMonitor() {
  try {
    const [activeResponse, completedResponse, configResponse] = await Promise.all([
      fetch(`/teacher/active_attempts?password=${encodeURIComponent(password)}`),
      fetch(`/teacher/results?password=${encodeURIComponent(password)}`),
      fetch(`/get_config?password=${encodeURIComponent(password)}`)
    ]);
    if (!activeResponse.ok || !completedResponse.ok || !configResponse.ok) {
      sessionStorage.removeItem("teacherPassword");
      window.location.replace("index.html");
      return;
    }
    const active = await activeResponse.json();
    const completed = await completedResponse.json();
    const config = await configResponse.json();
    if (config.error) {
      sessionStorage.removeItem("teacherPassword");
      window.location.replace("index.html");
      return;
    }
    const gradeThresholds = config.grade_thresholds || {"3": 52, "4": 68, "5": 84};
    $("active-count").textContent = active.length;
    $("updated").textContent = `Обновлено: ${new Date().toLocaleTimeString("ru-RU")}`;
    $("active-rows").innerHTML = active.length ? active.map(attempt => `<tr><td><strong>${escapeHtml(attempt.student)}</strong></td><td>${formatDate(attempt.start_time)}</td><td>${attempt.answered} из ${attempt.total}</td><td class="success">${attempt.correct}</td><td class="fail">${attempt.incorrect}</td><td>${formatRemaining(attempt)}</td><td class="success">на связи</td></tr>`).join("") : '<tr><td colspan="7" class="empty">Сейчас никто не проходит тест.</td></tr>';
    $("completed-rows").innerHTML = completed.length ? completed.map(result => {
      const grade = getGrade(result.correct_percent, gradeThresholds);
      return `<tr><td>${escapeHtml(result.student)}</td><td>${result.correct_percent}%</td><td><span class="grade-badge grade-${grade}">${grade}</span></td><td>${formatDate(result.end_time)}</td></tr>`;
    }).join("") : '<tr><td colspan="4" class="empty">Завершённых тестов пока нет.</td></tr>';
  } catch (error) {
    $("updated").textContent = "Не удалось обновить монитор";
  }
}
loadMonitor();
setInterval(loadMonitor, 5000);

function getGrade(percent, thresholds) {
  const score = Number(percent) || 0;
  if (score >= Number(thresholds["5"])) return 5;
  if (score >= Number(thresholds["4"])) return 4;
  if (score >= Number(thresholds["3"])) return 3;
  return 2;
}
