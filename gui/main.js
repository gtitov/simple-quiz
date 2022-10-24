document.addEventListener("DOMContentLoaded", function () {
    // console.log("ok")
    var students_selector = document.getElementById("students-selector")
    var get_quiz_button = document.getElementById("get-quiz")

    fetch("http://localhost:8000/students")
        .then(r => r.json())
        .then(students => {
            students.forEach(student => {
                students_selector.innerHTML += `<option value=${student.id}>${student.name}</option>`    
            })
            students_selector.addEventListener("change", function (e) {
                get_quiz_button.disabled = false
            },
                { once: true }
            )
        })

    get_quiz_button.addEventListener("click", function () {
        // console.log(students_selector.value)
        // console.log(students_selector.options[students_selector.selectedIndex].text)
        fetch('http://localhost:8000/get_quiz?' + new URLSearchParams({
            student_id: students_selector.value,
            student: students_selector.options[students_selector.selectedIndex].text
        }))
            .then(r => r.json())
            .then(quiz => {
                // console.log(quiz)
                var questions = quiz.questions

                var questions_html = "<form id='form' onkeydown='return event.keyCode != 13;'>"
                questions.forEach(q => {
                    console.log(q)
                    if (q.options) {
                        let options_div = ""
                        q.options.forEach(o => {
                            options_div += 
                            `<div>
                                <input type="radio" id="${o}" name="${q.id}" value="${o}">
                                <label for="${o}">${o}</label>
                            </div>`
                        })
                        const question_div = 
                        `<fieldset>
                            <legend>Выберите ответ:</legend>
                            ${options_div}
                        </fieldset>`
                        questions_html += 
                        `<article>
                            <h3>${q.question}</h3>
                            ${q.picture ? `<img src='${q.picture}'>` : ""}
                            ${question_div}
                        </article>`
                    } else {
                        const question_div = `<input type="text" id="${q.id}" name="${q.id}">`
                        questions_html += 
                        `<article>
                            <h3>${q.question}</h3>
                            ${q.picture ? `<img src='${q.picture}'>` : ""}
                            ${question_div}
                        </article>`
                    }
                })
                // console.log(questions_html)
                questions_html += "</form>"
                document.getElementById("header").innerHTML = `<h1>Тестирование</h1><p>${students_selector.options[students_selector.selectedIndex].text}</p>`
                document.getElementById("main").innerHTML = questions_html

                var button = document.createElement('button');
                button.innerHTML = 'Сдать';
                button.onclick = function () {
                    const form = document.getElementById('form');
                    const formData = new FormData(form);
                    console.log(formData)
                    for (const [key, value] of formData) {
                        console.log(quiz)
                        console.log(`${key}: ${value}\n`)  // assume questions are in the same order - can it make code simplier?
                        quiz.questions.find(q => q.id == key).student_answer = value
                        // console.log(quiz)
                    }
                    fetch('http://localhost:8000/save_student_answers?' + new URLSearchParams({
                        student_answers: JSON.stringify(quiz)
                    }))
                    document.getElementById("main").innerHTML = "<p>Тестирование окончено</p>"
                };
                // where do we want to have the button to appear?
                // you can append it to another element just by doing something like
                // document.getElementById('foobutton').appendChild(button);
                document.getElementById("main").appendChild(button)
            })
    })

    document.getElementById("end-quiz").addEventListener("click", function() {
        let pass = window.prompt("Уважаемый преподаватель, введите пароль, чтобы завершить тестирование для всех", "Я здесь случайно")
        // console.log(pass)
        fetch('http://localhost:8000/end_quiz?' + new URLSearchParams({
            password: pass
        }))
            .then(r => r.text())
            .then(text => window.alert(text))
    })
})