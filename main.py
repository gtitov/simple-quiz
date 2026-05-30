from fastapi import FastAPI, Body, UploadFile
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
            "test_time": 15
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
    all_questions = questions_json["questions"]
    typed_questions = [dict(q, **{"is_multiple": isinstance(q["answer"], list)}) for q in all_questions]

with open(STUDENTS_FILE, "r", encoding="UTF-8") as f:
    students_json = json.load(f)
    students = students_json["students"]

Path("answers").mkdir(parents=True, exist_ok=True)
Path("results").mkdir(parents=True, exist_ok=True)


@app.get("/get_config")
def get_config(password: str):
    if password != END_TEST_PASSWORD:
        return {"error": "Неверный пароль"}
    return config


@app.get("/get_topics")
def get_topics(password: str):
    if password != END_TEST_PASSWORD:
        return []
    return sorted(set(q["topic"] for q in all_questions if q.get("topic")))


@app.get("/students")
def show_students():
    return students


@app.post("/set_config")
async def set_config(password: str, data: dict = Body()):
    if password != END_TEST_PASSWORD:
        return "Неверный пароль"

    config["quiz_length"] = int(data.get("quiz_length", QUIZ_LENGTH))
    topics = data.get("topics")
    config["topics"] = topics if topics else None
    config["test_time"] = int(data.get("test_time", 15))
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
    if config["topics"]:
        selected_questions = [q for q in typed_questions if q.get("topic") in config["topics"]]
    else:
        selected_questions = typed_questions

    questions_for_student = random.sample(
        selected_questions,
        min(config["quiz_length"], len(selected_questions))
    )

    remove_keys = ["author", "answer"]
    quiz_questions = [{key: value for key, value in q.items() if key not in remove_keys} for q in questions_for_student]

    return {
        "version": 1,
        "student_id": student_id,
        "student": student,
        "wave": WAVE,
        "start_time": datetime.now().isoformat(),
        "questions": quiz_questions,
        "test_time": load_config().get("test_time", 15)
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
    timestamp_str = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    json_answers["end_time"] = timestamp_str

    path_to_answers = f'answers/{json_answers["student"]}_{json_answers["wave"]}_{timestamp_str}.json'
    with open(path_to_answers, 'w', encoding='utf-8') as f:
        json.dump(json_answers, f, ensure_ascii=False)

    checked = check_answers(json_answers)
    path_to_results = f'results/{json_answers["student"]}_{json_answers["wave"]}_{timestamp_str}_{checked["correct_percent"]}.json'
    path_to_summary = 'gui/summary.txt'
    with open(path_to_results, 'w', encoding='utf-8') as f:
        json.dump(checked, f, ensure_ascii=False)

    with open(path_to_summary, 'a', encoding='utf-8') as f:
        f.write(json_answers["student"] + ',' + str(checked["correct_percent"]) + ',' + timestamp_str + '\n')

    return json_answers["student"]


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