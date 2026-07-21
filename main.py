from fastapi import FastAPI, Body, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import random
import shutil
from pathlib import Path
from datetime import datetime
import socket
import csv
import io
import time
import hashlib
import threading
import uuid

from settings import WAVE, END_TEST_PASSWORD, QUIZ_LENGTH, QUESTIONS_FILE, STUDENTS_FILE

CONFIG_FILE = "config.json"


def load_config():
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "quiz_length": QUIZ_LENGTH,
            "topics": None,
            "test_time": 15,
            "activity_timeout": 30,
            "grade_thresholds": {"3": 52, "4": 68, "5": 84}
        }


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def save_students_json(students_list: list):
    data = {
        "version": 1,
        "students": students_list
    }
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_students_file():
    path = Path(STUDENTS_FILE)
    if path.exists():
        backup_dir = Path("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_path = backup_dir / f"students_{timestamp}.json"
        shutil.copy2(path, backup_path)


def backup_questions_file():
    path = Path(QUESTIONS_FILE)
    if path.exists():
        backup_dir = Path("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
        shutil.copy2(path, backup_dir / f"questions_{timestamp}.json")


def require_teacher(password: str):
    if password != END_TEST_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")


def prepare_questions(questions: list) -> list:
    existing_ids = {
        q["id"] for q in questions
        if isinstance(q.get("id"), int) and not isinstance(q.get("id"), bool)
    }
    next_id = max(existing_ids, default=0) + 1
    used_ids = set()
    prepared = []

    for question in questions:
        item = dict(question)
        if (
            not isinstance(item.get("id"), int)
            or isinstance(item.get("id"), bool)
            or item["id"] in used_ids
        ):
            while next_id in used_ids:
                next_id += 1
            item["id"] = next_id
            next_id += 1
        used_ids.add(item["id"])
        item["is_multiple"] = isinstance(item.get("answer"), list)
        item["enabled"] = item.get("enabled", True) is not False
        prepared.append(item)
    return prepared


def save_questions():
    data = {
        "version": questions_json.get("version", 2),
        "questions": [
            {key: value for key, value in q.items() if key != "is_multiple"}
            for q in all_questions
        ]
    }
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_question(data: dict, question_id=None) -> dict:
    question = str(data.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Введите текст вопроса")

    answer_type = data.get("answer_type", "text")
    options = [str(x).strip() for x in data.get("options", []) if str(x).strip()]
    raw_answer = data.get("answer", "")

    if answer_type == "multiple":
        answer = [str(x).strip() for x in raw_answer if str(x).strip()] if isinstance(raw_answer, list) else []
        if len(options) < 2 or not answer:
            raise HTTPException(status_code=400, detail="Добавьте варианты и отметьте правильные ответы")
        if any(value not in options for value in answer):
            raise HTTPException(status_code=400, detail="Правильные ответы должны входить в список вариантов")
    elif answer_type == "single":
        answer = str(raw_answer).strip()
        if len(options) < 2 or answer not in options:
            raise HTTPException(status_code=400, detail="Выберите правильный ответ из списка вариантов")
    else:
        answer = str(raw_answer).strip()
        options = []
        if not answer:
            raise HTTPException(status_code=400, detail="Введите правильный ответ")

    result = {
        "id": question_id,
        "topic": str(data.get("topic", "")).strip(),
        "author": str(data.get("author", "")).strip(),
        "question": question,
        "answer": answer,
        "enabled": data.get("enabled", True) is not False,
        "is_multiple": isinstance(answer, list)
    }
    picture = str(data.get("picture", "")).strip()
    if picture:
        result["picture"] = picture
    if options:
        result["options"] = options
    return result


def normalize_name(name: str) -> str:
    return " ".join(str(name).strip().split())


def parse_students_csv(file_obj):
    raw = file_obj.read()

    # пробуем utf-8-sig, потом utf-8, потом cp1251
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("Не удалось прочитать CSV. Сохраните файл как CSV UTF-8.")

    # пытаемся определить разделитель
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if row and any(str(cell).strip() for cell in row)]

    if not rows:
        raise ValueError("CSV-файл пуст.")

    first_row = [str(cell).strip().lower() for cell in rows[0]]
    students_list = []

    # Вариант 1: заголовки id,name
    if "id" in first_row and "name" in first_row:
        id_idx = first_row.index("id")
        name_idx = first_row.index("name")

        for row in rows[1:]:
            if len(row) <= max(id_idx, name_idx):
                continue

            student_id = row[id_idx]
            student_name = row[name_idx]

            if not str(student_name).strip():
                continue

            try:
                student_id = int(str(student_id).strip())
            except Exception:
                raise ValueError("В колонке 'id' должны быть числа.")

            students_list.append({
                "id": student_id,
                "name": normalize_name(student_name)
            })

    # Вариант 2: заголовок name
    elif "name" in first_row:
        name_idx = first_row.index("name")
        next_id = 1

        for row in rows[1:]:
            if len(row) <= name_idx:
                continue

            student_name = row[name_idx]
            if not str(student_name).strip():
                continue

            students_list.append({
                "id": next_id,
                "name": normalize_name(student_name)
            })
            next_id += 1

    # Вариант 3: заголовок ФИО
    elif len(first_row) >= 1 and first_row[0] in {"фио", "ф.и.о.", "student", "student_name"}:
        next_id = 1
        for row in rows[1:]:
            if not row:
                continue

            student_name = row[0]
            if not str(student_name).strip():
                continue

            students_list.append({
                "id": next_id,
                "name": normalize_name(student_name)
            })
            next_id += 1

    # Вариант 4: просто один столбец без заголовка
    elif all(len(row) == 1 for row in rows):
        next_id = 1
        for row in rows:
            student_name = row[0]
            if not str(student_name).strip():
                continue

            students_list.append({
                "id": next_id,
                "name": normalize_name(student_name)
            })
            next_id += 1

    else:
        raise ValueError(
            "Не удалось распознать формат CSV. Используйте один из вариантов: "
            "1) колонки id и name; "
            "2) колонка name; "
            "3) колонка ФИО; "
            "4) один столбец с ФИО."
        )

    if not students_list:
        raise ValueError("Не найдено ни одного студента.")

    # проверка дублей по ФИО
    seen_names = set()
    duplicate_names = set()
    for s in students_list:
        key = s["name"].casefold()
        if key in seen_names:
            duplicate_names.add(s["name"])
        seen_names.add(key)

    if duplicate_names:
        dupes = ", ".join(sorted(duplicate_names))
        raise ValueError(f"В списке есть дубли ФИО: {dupes}")

    # проверка дублей id
    ids = [s["id"] for s in students_list]
    if len(ids) != len(set(ids)):
        raise ValueError("В списке есть повторяющиеся id.")

    return students_list


config = load_config()
config.setdefault("activity_timeout", 30)
config.setdefault("grade_thresholds", {"3": 52, "4": 68, "5": 84})
submission_lock = threading.Lock()

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open(QUESTIONS_FILE, "r", encoding="UTF-8") as f:
    questions_json = json.load(f)
    all_questions = prepare_questions(questions_json["questions"])
    typed_questions = all_questions

with open(STUDENTS_FILE, "r", encoding="UTF-8") as f:
    students_json = json.load(f)
    students = students_json["students"]

Path("answers").mkdir(parents=True, exist_ok=True)
Path("results").mkdir(parents=True, exist_ok=True)
active_attempts = {}


@app.get("/get_config")
def get_config(password: str):
    if password != END_TEST_PASSWORD:
        return {"error": "Неверный пароль"}
    return config


@app.get("/get_topics")
def get_topics(password: str):
    if password != END_TEST_PASSWORD:
        return []
    return sorted(set(q["topic"] for q in all_questions if q.get("topic") and q.get("enabled", True)))


@app.get("/teacher/questions")
def get_teacher_questions(password: str):
    require_teacher(password)
    return sorted(all_questions, key=lambda q: (q.get("topic", "").casefold(), q["id"]))


@app.post("/teacher/questions")
def create_question(password: str, data: dict = Body()):
    require_teacher(password)
    next_id = max((q["id"] for q in all_questions), default=0) + 1
    question = validate_question(data, next_id)
    backup_questions_file()
    all_questions.append(question)
    save_questions()
    return question


@app.put("/teacher/questions/{question_id}")
def update_question(question_id: int, password: str, data: dict = Body()):
    require_teacher(password)
    index = next((i for i, q in enumerate(all_questions) if q["id"] == question_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    question = validate_question(data, question_id)
    backup_questions_file()
    all_questions[index] = question
    save_questions()
    return question


@app.delete("/teacher/questions/{question_id}")
def delete_question(question_id: int, password: str):
    require_teacher(password)
    index = next((i for i, q in enumerate(all_questions) if q["id"] == question_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    backup_questions_file()
    deleted = all_questions.pop(index)
    save_questions()
    return {"deleted": deleted["id"]}


@app.get("/teacher/results")
def get_teacher_results(password: str):
    require_teacher(password)
    results = []
    for path in Path("results").glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            incorrect = [
                {
                    "id": q.get("id"),
                    "topic": q.get("topic", ""),
                    "question": q.get("question", ""),
                    "student_answer": q.get("student_answer"),
                    "correct_answer": q.get("correct_answer")
                }
                for q in content.get("questions", [])
                if not q.get("is_correct", False)
            ]
            results.append({
                "student": content.get("student", ""),
                "student_id": content.get("student_id"),
                "correct": content.get("correct", 0),
                "total": len(content.get("questions", [])),
                "correct_percent": content.get("correct_percent", 0),
                "start_time": content.get("start_time"),
                "end_time": content.get("end_time"),
                "incorrect": incorrect
            })
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(results, key=lambda x: x.get("end_time") or "", reverse=True)


@app.get("/teacher/analytics")
def get_teacher_analytics(password: str):
    require_teacher(password)
    attempts = []
    question_stats = {}
    topic_stats = {}

    for path in Path("results").glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        questions = result.get("questions", [])
        if not questions:
            continue
        attempts.append({
            "student": result.get("student", ""),
            "percent": result.get("correct_percent", 0),
            "correct": result.get("correct", 0),
            "total": len(questions),
            "end_time": result.get("end_time")
        })

        for question in questions:
            question_id = str(question.get("id", question.get("question", "")))
            topic = question.get("topic") or "Без темы"
            q_stat = question_stats.setdefault(question_id, {
                "id": question.get("id"),
                "question": question.get("question", ""),
                "topic": topic,
                "attempts": 0,
                "correct": 0
            })
            t_stat = topic_stats.setdefault(topic, {
                "topic": topic,
                "attempts": 0,
                "correct": 0
            })
            q_stat["attempts"] += 1
            t_stat["attempts"] += 1
            if question.get("is_correct", False):
                q_stat["correct"] += 1
                t_stat["correct"] += 1

    scores = [attempt["percent"] for attempt in attempts]
    sorted_scores = sorted(scores)
    median_score = (
        sorted_scores[len(sorted_scores) // 2]
        if len(sorted_scores) % 2 == 1
        else round(sum(sorted_scores[len(sorted_scores) // 2 - 1:len(sorted_scores) // 2 + 1]) / 2, 1)
    ) if sorted_scores else 0

    def with_accuracy(stat):
        attempts_count = stat["attempts"]
        accuracy = round(stat["correct"] * 100 / attempts_count) if attempts_count else 0
        return {
            **stat,
            "incorrect": attempts_count - stat["correct"],
            "accuracy": accuracy
        }

    questions = sorted(
        (with_accuracy(stat) for stat in question_stats.values()),
        key=lambda stat: (stat["accuracy"], -stat["attempts"], stat["question"])
    )
    topics = sorted(
        (with_accuracy(stat) for stat in topic_stats.values()),
        key=lambda stat: (stat["accuracy"], -stat["attempts"], stat["topic"])
    )
    students = sorted(attempts, key=lambda attempt: (-attempt["percent"], attempt["student"]))
    distribution = [
        {"label": "0–49%", "count": sum(score < 50 for score in scores)},
        {"label": "50–69%", "count": sum(50 <= score < 70 for score in scores)},
        {"label": "70–84%", "count": sum(70 <= score < 85 for score in scores)},
        {"label": "85–100%", "count": sum(score >= 85 for score in scores)}
    ]

    return {
        "summary": {
            "attempts": len(attempts),
            "students": len({attempt["student"] for attempt in attempts if attempt["student"]}),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "median_score": median_score,
            "pass_rate": round(sum(score >= 50 for score in scores) * 100 / len(scores)) if scores else 0
        },
        "distribution": distribution,
        "students": students,
        "questions": questions,
        "topics": topics
    }


@app.get("/students")
def show_students():
    return students


@app.post("/quiz_heartbeat")
def quiz_heartbeat(data: dict = Body()):
    server_time_ms = round(time.time() * 1000)
    student_id = str(data.get("student_id", ""))
    if not student_id:
        return {"active": False, "server_time_ms": server_time_ms}

    if student_id not in active_attempts:
        if not data.get("student") or not data.get("start_time") or not data.get("total"):
            return {"active": False}
        try:
            start_time = datetime.fromisoformat(data.get("start_time", ""))
        except (TypeError, ValueError):
            start_time = datetime.now()
        test_time = max(1, int(data.get("test_time", 15)))
        maximum_end_time_ms = round(start_time.timestamp() * 1000) + test_time * 60_000
        proposed_end_time_ms = int(data.get("end_time_ms") or maximum_end_time_ms)
        active_attempts[student_id] = {
            "student_id": data.get("student_id"),
            "student": str(data.get("student", "")),
            "start_time": start_time,
            "last_seen": datetime.now(),
            "answered": 0,
            "correct": 0,
            "incorrect": 0,
            "total": max(0, int(data.get("total", 0))),
            "test_time": test_time,
            "end_time_ms": min(proposed_end_time_ms, maximum_end_time_ms)
        }

    attempt = active_attempts[student_id]
    attempt.setdefault(
        "end_time_ms",
        round(attempt["start_time"].timestamp() * 1000) + attempt["test_time"] * 60_000
    )
    if server_time_ms >= attempt["end_time_ms"]:
        active_attempts.pop(student_id, None)
        return {
            "active": False,
            "expired": True,
            "server_time_ms": server_time_ms,
            "end_time_ms": attempt["end_time_ms"]
        }

    attempt["last_seen"] = datetime.now()
    current_answers = data.get("answers", [])
    correct = 0
    incorrect = 0
    answered = 0
    for current in current_answers:
        question = next((q for q in all_questions if q["id"] == current.get("id")), None)
        if not question:
            continue
        student_answer = current.get("answer")
        is_answered = (
            bool(student_answer)
            if isinstance(student_answer, list)
            else bool(str(student_answer or "").strip())
        )
        if not is_answered:
            continue
        answered += 1
        if isinstance(student_answer, str) and isinstance(question["answer"], str):
            is_correct = student_answer.casefold() == question["answer"].casefold()
        elif isinstance(student_answer, list) and isinstance(question["answer"], list):
            is_correct = set(student_answer) == set(question["answer"])
        else:
            is_correct = False
        if is_correct:
            correct += 1
        else:
            incorrect += 1

    attempt["answered"] = answered
    attempt["correct"] = correct
    attempt["incorrect"] = incorrect
    return {
        "active": True,
        "expired": False,
        "server_time_ms": server_time_ms,
        "end_time_ms": attempt["end_time_ms"]
    }


@app.get("/teacher/active_attempts")
def get_active_attempts(password: str):
    require_teacher(password)
    now = datetime.now()
    now_ms = round(time.time() * 1000)
    expired = [
        student_id for student_id, attempt in active_attempts.items()
        if (now - attempt["last_seen"]).total_seconds() > config.get("activity_timeout", 30)
        or now_ms >= attempt.get(
            "end_time_ms",
            round(attempt["start_time"].timestamp() * 1000) + attempt["test_time"] * 60_000
        )
    ]
    for student_id in expired:
        active_attempts.pop(student_id, None)

    return [
        {
            "student_id": attempt["student_id"],
            "student": attempt["student"],
            "start_time": attempt["start_time"].isoformat(),
            "last_seen": attempt["last_seen"].isoformat(),
            "answered": attempt["answered"],
            "correct": attempt["correct"],
            "incorrect": attempt["incorrect"],
            "total": attempt["total"],
            "test_time": attempt["test_time"],
            "remaining_seconds": max(0, (attempt.get(
                "end_time_ms",
                round(attempt["start_time"].timestamp() * 1000) + attempt["test_time"] * 60_000
            ) - now_ms) // 1000)
        }
        for attempt in sorted(active_attempts.values(), key=lambda item: item["start_time"])
    ]


@app.post("/set_config")
async def set_config(password: str, data: dict = Body()):
    if password != END_TEST_PASSWORD:
        return "Неверный пароль"

    config["quiz_length"] = int(data.get("quiz_length", QUIZ_LENGTH))
    topics = data.get("topics")
    config["topics"] = topics if topics is not None else None
    config["test_time"] = int(data.get("test_time", 15))
    config["activity_timeout"] = max(15, min(3600, int(data.get("activity_timeout") or 30)))
    grade_thresholds = data.get("grade_thresholds") or {}
    config["grade_thresholds"] = {
        "3": max(0, min(100, int(grade_thresholds.get("3", 52)))),
        "4": max(0, min(100, int(grade_thresholds.get("4", 68)))),
        "5": max(0, min(100, int(grade_thresholds.get("5", 84))))
    }
    save_config(config)
    return "Настройки сохранены!"


@app.post("/upload_students")
def upload_students(password: str, file: UploadFile):
    if password != END_TEST_PASSWORD:
        return "Неверный пароль"

    try:
        filename = (file.filename or "").lower()

        global students

        if filename.endswith(".json"):
            content = json.load(file.file)
            if "students" not in content or not isinstance(content["students"], list):
                raise ValueError("Неверный JSON-формат. Ожидается объект с полем 'students'.")

            backup_students_file()
            students = content["students"]
            save_students_json(students)
            return f"JSON загружен успешно. Студентов: {len(students)}"

        elif filename.endswith(".csv"):
            parsed_students = parse_students_csv(file.file)

            backup_students_file()
            students = parsed_students
            save_students_json(students)
            return f"CSV обработан успешно. Студентов: {len(students)}"

        else:
            return "Поддерживаются только файлы .json и .csv"

    except Exception as e:
        return f"Ошибка: {str(e)}"


@app.get("/get_quiz")
def get_quiz(student_id, student: str):
    enabled_questions = [q for q in typed_questions if q.get("enabled", True)]
    if config.get("topics") is not None:
        selected_questions = [q for q in enabled_questions if q.get("topic") in config["topics"]]
    else:
        selected_questions = enabled_questions

    if not selected_questions:
        raise HTTPException(status_code=400, detail="Нет включённых вопросов для выбранных тем")

    questions_for_student = random.sample(
        selected_questions,
        min(config["quiz_length"], len(selected_questions))
    )

    remove_keys = ["author", "answer", "enabled"]
    quiz_questions = [{key: value for key, value in q.items() if key not in remove_keys} for q in questions_for_student]

    start_time = datetime.now()
    test_time = load_config().get("test_time", 15)
    server_time_ms = round(time.time() * 1000)
    end_time_ms = server_time_ms + test_time * 60_000
    active_attempts[str(student_id)] = {
        "student_id": student_id,
        "student": student,
        "start_time": start_time,
        "last_seen": start_time,
        "answered": 0,
        "correct": 0,
        "incorrect": 0,
        "total": len(quiz_questions),
        "test_time": test_time,
        "end_time_ms": end_time_ms
    }

    return {
        "version": 1,
        "attempt_id": uuid.uuid4().hex,
        "student_id": student_id,
        "student": student,
        "wave": WAVE,
        "start_time": start_time.isoformat(),
        "server_time_ms": server_time_ms,
        "end_time_ms": end_time_ms,
        "questions": quiz_questions,
        "test_time": test_time
    }


def check_answers(student_answers: dict):
    checked_answers = student_answers
    for a in checked_answers["questions"]:
        question_id = a["id"]
        a["correct_answer"] = next(question["answer"] for question in all_questions if question["id"] == question_id)

        if isinstance(a["student_answer"], str) and isinstance(a["correct_answer"], str):
            a["is_correct"] = a["student_answer"].casefold() == a["correct_answer"].casefold()
        elif isinstance(a["student_answer"], list) and isinstance(a["correct_answer"], list):
            a["is_correct"] = set(a["student_answer"]) == set(a["correct_answer"])
        else:
            a["is_correct"] = False

    checked_answers["correct"] = sum([a["is_correct"] for a in checked_answers["questions"]])
    checked_answers["correct_percent"] = round(checked_answers["correct"] * 100 / len(checked_answers["questions"]))
    return checked_answers


@app.post("/save_student_answers")
def send_student_answers(student_answers: str = Body()):
    json_answers = json.loads(student_answers)
    attempt_id = str(json_answers.get("attempt_id") or "").strip()
    if not attempt_id:
        identity = f'{json_answers.get("student_id", "")}|{json_answers.get("start_time", "")}|{json_answers.get("wave", "")}'
        attempt_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        json_answers["attempt_id"] = attempt_id

    with submission_lock:
        existing = next(Path("results").glob(f"*_{attempt_id}_*.json"), None)
        if existing:
            with open(existing, "r", encoding="utf-8") as f:
                content = json.load(f)
            active_attempts.pop(str(json_answers.get("student_id", "")), None)
            return {
                "student": content.get("student", json_answers.get("student", "")),
                "attempt_id": attempt_id,
                "already_saved": True
            }

        active_attempts.pop(str(json_answers.get("student_id", "")), None)
        timestamp_str = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        json_answers["end_time"] = timestamp_str
        safe_student = "".join(
            char if char not in '<>:"/\\|?*' else "_"
            for char in str(json_answers.get("student", "student"))
        )

        path_to_answers = Path("answers") / f"{safe_student}_{json_answers['wave']}_{attempt_id}.json"
        with open(path_to_answers, "w", encoding="utf-8") as f:
            json.dump(json_answers, f, ensure_ascii=False)

        checked = check_answers(json_answers)
        path_to_results = Path("results") / (
            f"{safe_student}_{json_answers['wave']}_{attempt_id}_{checked['correct_percent']}.json"
        )
        with open(path_to_results, "w", encoding="utf-8") as f:
            json.dump(checked, f, ensure_ascii=False)

        with open("gui/summary.txt", "a", encoding="utf-8") as f:
            f.write(json_answers["student"] + "," + str(checked["correct_percent"]) + "," + timestamp_str + "\n")

        return {
            "student": json_answers["student"],
            "attempt_id": attempt_id,
            "already_saved": False
        }


@app.get("/submission_status/{attempt_id}")
def submission_status(attempt_id: str):
    safe_attempt_id = "".join(char for char in attempt_id if char.isalnum() or char in "-_")
    if not safe_attempt_id or safe_attempt_id != attempt_id:
        raise HTTPException(status_code=400, detail="Некорректный идентификатор попытки")
    return {"submitted": next(Path("results").glob(f"*_{safe_attempt_id}_*.json"), None) is not None}


@app.get("/end_quiz")
def end_test(password: str):
    if password == END_TEST_PASSWORD:
        csv_string = "student,percent,start,end\n"
        for file_in_results in Path("results").iterdir():
            if file_in_results.is_file() and file_in_results.suffix == ".json":
                with open(file_in_results, "r", encoding="UTF-8") as f:
                    content = json.load(f)
                    csv_string += f"{content['student']},{content['correct_percent']},{content['start_time']},{content['end_time']}\n"

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        results_path = Path(f"results/results_{timestamp}.csv")
        with open(results_path, "w", encoding='utf-8') as f:
            f.write(csv_string)

        return f"Тестирование завершено. Сводные результаты сохранены в {results_path.resolve()}"
    else:
        return "Неверный пароль"


@app.get("/hostip")
def show_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


app.mount("/pictures", StaticFiles(directory="pictures"), name="pictures")
app.mount("/", StaticFiles(directory="gui", html=True), name="gui")
