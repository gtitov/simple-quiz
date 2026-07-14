const password = sessionStorage.getItem("teacherPassword") || "";
const message = document.getElementById("access-message");
const tools = document.getElementById("teacher-tools");
const actions = document.getElementById("teacher-actions");

if (!password) {
  message.textContent = "Доступ не подтверждён. Вернитесь на главную страницу и войдите как преподаватель.";
  message.className = "message error";
} else {
  fetch("/get_config?password=" + encodeURIComponent(password))
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        sessionStorage.removeItem("teacherPassword");
        throw new Error("Неверный пароль");
      }
      message.textContent = "";
      tools.hidden = false;
      actions.hidden = false;
    })
    .catch(error => {
      message.textContent = error.message || "Не удалось проверить доступ";
      message.className = "message error";
    });
}

document.getElementById("end-quiz").addEventListener("click", function() {
  if (!confirm("Завершить тестирование для всех студентов?")) {
    return;
  }
  fetch("/end_quiz?password=" + encodeURIComponent(password))
    .then(response => response.json())
    .then(text => alert(text));
});
