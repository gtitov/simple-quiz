const ACTIVE_QUIZ_KEY = "activeQuiz";

document.addEventListener("DOMContentLoaded", async function () {
  const studentsSelector = document.getElementById("students-selector");
  const getQuizButton = document.getElementById("get-quiz");
  const savedAttempt = loadAttempt();

  if (savedAttempt && await isAttemptSubmitted(savedAttempt)) {
    sessionStorage.removeItem(ACTIVE_QUIZ_KEY);
    loadStartPage(studentsSelector, getQuizButton);
  } else if (savedAttempt) {
    renderQuiz(savedAttempt);
  } else {
    loadStartPage(studentsSelector, getQuizButton);
  }

  setupTeacherLogin();
});

async function isAttemptSubmitted(attempt) {
  const attemptId = attempt.quiz && attempt.quiz.attempt_id;
  if (!attemptId) return false;
  try {
    const response = await fetch(`/submission_status/${encodeURIComponent(attemptId)}`, { cache: "no-store" });
    return response.ok && (await response.json()).submitted === true;
  } catch {
    return false;
  }
}

function loadAttempt() {
  try {
    const attempt = JSON.parse(sessionStorage.getItem(ACTIVE_QUIZ_KEY));
    if (!attempt || !attempt.quiz || (!attempt.endTimeMs && !attempt.endTime)) return null;
    attempt.endTimeMs = attempt.endTimeMs || attempt.endTime;
    attempt.serverOffsetMs = attempt.serverOffsetMs || 0;
    return attempt;
  } catch {
    sessionStorage.removeItem(ACTIVE_QUIZ_KEY);
    return null;
  }
}

function saveAttempt(attempt) {
  sessionStorage.setItem(ACTIVE_QUIZ_KEY, JSON.stringify(attempt));
}

function loadStartPage(studentsSelector, getQuizButton) {
  fetch("/hostip").then(r => r.json()).then(hostIp => {
    document.getElementById("host-ip").textContent += ` ${hostIp}:8000`;
  });

  fetch("/students").then(r => r.json()).then(students => {
    students.forEach(student => {
      const option = document.createElement("option");
      option.value = student.id;
      option.textContent = student.name;
      studentsSelector.appendChild(option);
    });
    studentsSelector.addEventListener("change", () => { getQuizButton.disabled = false; });
  });

  getQuizButton.addEventListener("click", function () {
    fetch("/get_quiz?" + new URLSearchParams({
      student_id: studentsSelector.value,
      student: studentsSelector.options[studentsSelector.selectedIndex].text
    })).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Не удалось получить тест");
      return data;
    }).then(quiz => {
      const attempt = {
        quiz,
        answers: {},
        endTimeMs: quiz.end_time_ms,
        serverOffsetMs: quiz.server_time_ms - Date.now()
      };
      saveAttempt(attempt);
      renderQuiz(attempt);
    }).catch(error => alert(error.message));
  });
}

function renderQuiz(attempt) {
  const { quiz } = attempt;
  document.getElementById("header").innerHTML = `<h1>Тестирование</h1><p>${escapeHtml(quiz.student)}</p>`;
  const main = document.getElementById("main");
  main.innerHTML = "";

  const form = document.createElement("form");
  form.id = "form";
  form.addEventListener("keydown", event => {
    if (event.key === "Enter") event.preventDefault();
  });

  quiz.questions.forEach(question => {
    const article = document.createElement("article");
    const title = document.createElement("h3");
    title.textContent = question.question;
    article.appendChild(title);
    if (question.picture) {
      const image = document.createElement("img");
      image.src = question.picture;
      article.appendChild(image);
    }

    if (question.options) {
      const fieldset = document.createElement("fieldset");
      const legend = document.createElement("legend");
      legend.textContent = "Выберите ответ:";
      fieldset.appendChild(legend);
      question.options.forEach((option, index) => {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = question.is_multiple ? "checkbox" : "radio";
        input.name = String(question.id);
        input.value = option;
        input.id = `q-${question.id}-${index}`;
        const saved = attempt.answers[String(question.id)];
        input.checked = Array.isArray(saved) ? saved.includes(option) : saved === option;
        label.htmlFor = input.id;
        label.append(input, document.createTextNode(option));
        fieldset.appendChild(label);
      });
      article.appendChild(fieldset);
    } else {
      const input = document.createElement("input");
      input.type = "text";
      input.autocomplete = "off";
      input.name = String(question.id);
      input.value = attempt.answers[String(question.id)] || "";
      article.appendChild(input);
    }
    form.appendChild(article);
  });

  form.addEventListener("input", () => persistAnswers(attempt, form));
  form.addEventListener("change", () => persistAnswers(attempt, form));
  main.appendChild(form);

  const timer = document.createElement("div");
  main.appendChild(timer);
  let submitted = false;
  const showTime = () => {
    const correctedNow = Date.now() + attempt.serverOffsetMs;
    const seconds = Math.max(0, Math.ceil((attempt.endTimeMs - correctedNow) / 1000));
    timer.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    if (seconds === 0 && !submitted) submitQuiz();
  };
  showTime();
  const timerInterval = setInterval(showTime, 1000);

  const sendHeartbeat = () => {
    persistAnswers(attempt, form);
    const requestStartedAt = Date.now();
    fetch("/quiz_heartbeat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: quiz.student_id,
        student: quiz.student,
        start_time: quiz.start_time,
        total: quiz.questions.length,
        test_time: quiz.test_time,
        end_time_ms: attempt.endTimeMs,
        answers: answerList(attempt)
      })
    }).then(response => response.json()).then(status => {
      const requestFinishedAt = Date.now();
      if (status.server_time_ms) {
        const localMidpoint = (requestStartedAt + requestFinishedAt) / 2;
        attempt.serverOffsetMs = status.server_time_ms - localMidpoint;
      }
      if (status.end_time_ms) attempt.endTimeMs = status.end_time_ms;
      saveAttempt(attempt);
      if (status.expired && !submitted) submitQuiz();
    }).catch(() => {});
  };
  sendHeartbeat();
  const heartbeatInterval = setInterval(sendHeartbeat, 10000);

  const submitButton = document.createElement("button");
  submitButton.textContent = "Сдать тест";
  submitButton.style.margin = "20px";
  submitButton.type = "button";
  submitButton.addEventListener("click", submitQuiz);
  main.appendChild(submitButton);
  if (attempt.submissionPending) {
    setTimeout(submitQuiz, 0);
  }

  function submitQuiz() {
    if (submitted) return;
    submitted = true;
    persistAnswers(attempt, form);
    attempt.submissionPending = true;
    saveAttempt(attempt);
    quiz.questions.forEach(question => {
      question.student_answer = attempt.answers[String(question.id)] ?? (question.is_multiple ? [] : "");
    });
    fetch("/save_student_answers", { method: "POST", body: JSON.stringify(quiz) }).then(async response => {
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Не удалось сохранить результат");
      }
      sessionStorage.removeItem(ACTIVE_QUIZ_KEY);
      clearInterval(timerInterval);
      clearInterval(heartbeatInterval);
      main.innerHTML = "";
      const message = document.createElement("p");
      message.textContent = "Тестирование окончено";
      const nextButton = document.createElement("button");
      nextButton.textContent = "Начать тест для следующего пользователя";
      nextButton.addEventListener("click", () => window.location.reload());
      main.append(message, nextButton);
    }).catch(error => {
      submitted = false;
      alert(`${error.message}. Результат будет отправлен повторно после обновления страницы.`);
    });
  }
}

function persistAnswers(attempt, form) {
  attempt.quiz.questions.forEach(question => {
    const field = form.elements.namedItem(String(question.id));
    const inputs = Array.from(field ? (field.length === undefined ? [field] : field) : []);
    const selected = inputs.filter(input => ["radio", "checkbox"].includes(input.type) && input.checked).map(input => input.value);
    const text = inputs.find(input => !["radio", "checkbox"].includes(input.type));
    attempt.answers[String(question.id)] = question.is_multiple ? selected : (selected[0] || (text ? text.value : ""));
  });
  saveAttempt(attempt);
}

function answerList(attempt) {
  return attempt.quiz.questions.map(question => ({
    id: question.id,
    answer: attempt.answers[String(question.id)] ?? (question.is_multiple ? [] : "")
  }));
}

function setupTeacherLogin() {
  const dialog = document.getElementById("teacher-login");
  document.getElementById("teacher-page").addEventListener("click", function () {
    document.getElementById("teacher-login-error").textContent = "";
    dialog.showModal();
    document.getElementById("teacher-password").focus();
  });
  document.getElementById("teacher-login-cancel").addEventListener("click", () => dialog.close());
  document.getElementById("teacher-login-form").addEventListener("submit", function (event) {
    event.preventDefault();
    const password = document.getElementById("teacher-password").value;
    fetch("/get_config?password=" + encodeURIComponent(password)).then(r => r.json()).then(data => {
      if (data.error) {
        document.getElementById("teacher-login-error").textContent = "Неверный пароль";
        return;
      }
      sessionStorage.setItem("teacherPassword", password);
      window.location.href = "teacher.html";
    }).catch(() => {
      document.getElementById("teacher-login-error").textContent = "Не удалось проверить пароль";
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
}
