from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware  # CORS
from fastapi.staticfiles import StaticFiles
import json
import random
from pathlib import Path
from datetime import datetime 

from settings import WAVE, END_TEST_PASSWORD, QUIZ_LENGTH, QUESTIONS_FILE, STUDENTS_FILE

app = FastAPI()

origins = [ # CORS
    "*",
]

app.add_middleware(  # CORS
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# open files once and use variables after
with open(QUESTIONS_FILE, "r", encoding="UTF-8") as f:
    content = json.load(f)
    # TODO reassign questions id since mistakes are possible and checking is based on id
    all_questions = content["questions"]
    # if you want to use topics 1) filter all questions with topics 2) use topic questions to construct quiz_questions (when removing service keys from all_questions dict)
    # topics = ["теодолит"]  # move topics to VARIABLES
    # topics_questions = [q for q in all_questions if q.get("topic") in topics]
    typed_questions = [dict(q, **{"is_multiple": True}) if type(q["answer"]) is list else dict(q, **{"is_multiple": False}) for q in all_questions]
    print(typed_questions)
    remove_keys = ["author", "answer", "topic"]
    quiz_questions = [{key: value for key, value in q.items() if key not in remove_keys} for q in typed_questions]  # all_questions can be replaced with topic_questions

with open(STUDENTS_FILE, "r", encoding="UTF-8") as f:
    content = json.load(f)
    students = content["students"]

# create folders if they don't exist
Path("answers").mkdir(parents=True, exist_ok=True)
Path("results").mkdir(parents=True, exist_ok=True)

def check_answers(student_answers: dict):
    checked_answers = student_answers
    for a in checked_answers["questions"]:
        question_id = a["id"]
        a["correct_answer"] = next(question["answer"] for question in all_questions if question["id"] == question_id)  # all_questions can be replaced with topic_questions
        if type(a["student_answer"]) is str and type(a["correct_answer"]) is str:
            a["is_correct"] = a["student_answer"].casefold() == a["correct_answer"].casefold()
        elif type(a["student_answer"]) is list and type(a["correct_answer"]) is list:
            a["is_correct"] = set(a["student_answer"]) == set(a["correct_answer"])
        else:
            print("Unmatched types! Can't compare.")
            a["is_correct"] = False

    checked_answers["correct"] = sum([a["is_correct"] for a in checked_answers["questions"]])
    checked_answers["correct_percent"] = round(checked_answers["correct"] * 100 / len(checked_answers["questions"]))
    return checked_answers


@app.get("/students")
def show_students():
    return students

@app.get("/get_quiz")
def get_quiz(student_id, student: str):
    """Get json-like quiz

    Args:
        student_id (int): indentificator of a student
        student (str): student name

    Returns:
        obj: json-like quiz
    """
    quiz_length = QUIZ_LENGTH
    questions_for_student = random.sample(quiz_questions, len(quiz_questions))[:quiz_length]  # random order and only first n questions
    return {
        "version": 1,
        "student_id": student_id,
        "student": student,
        "wave": WAVE,  # волна сдачи теста
        "start_time": datetime.now().strftime("%Y-%m-%dT%H-%M-%S"),
        "questions": questions_for_student
    }

@app.post("/save_student_answers")
def send_student_answers(student_answers: str = Body()):
    """Save answers as-is and check answers

    Args:
        student_answers (str): json-like string with student's answers

    Returns:
        str: student name
    """
    json_answers = json.loads(student_answers)
    timestamp_str = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    json_answers["end_time"] = timestamp_str
    path_to_answers = f'answers/{json_answers["student"]}_{json_answers["wave"]}_{timestamp_str}.json'
    with open(path_to_answers, 'w', encoding='utf-8') as f:
        json.dump(json_answers, f, ensure_ascii=False)

    path_to_results = f'results/{json_answers["student"]}_{json_answers["wave"]}_{timestamp_str}.json'
    with open(path_to_results, 'w', encoding='utf-8') as f:
        json.dump(check_answers(json_answers), f, ensure_ascii=False)  # TODO move checking to background?
    return json_answers["student"]

@app.get("/end_quiz")
def end_test(password: str):
    """End test and save results to csv

    Args:
        password (str): password to end test
    """
    if password == END_TEST_PASSWORD:
        csv_string = "student,percent,start,end\n"
        for file_in_results in Path("results").iterdir():
            if file_in_results.is_file() and file_in_results.suffix == ".json":
                # print(file_in_results)
                with open(file_in_results, "r", encoding="UTF-8") as f:
                    content = json.load(f)
                    csv_string += f"{content['student']},{content['correct_percent']},{content['start_time']},{content['end_time']}\n"
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        results_path = Path(f"results/results_{timestamp}.csv")
        with open(results_path, "w", encoding='utf-8') as f:
            f.write(csv_string)
        return(f"Тестирование завершено. Сводные результаты сохранены в {results_path.resolve()}")
    else:
        return("Неверный пароль")

app.mount("/pictures", StaticFiles(directory="pictures"), name="pictures")
app.mount("/", StaticFiles(directory="gui", html = True), name="gui")  # must be after all since root route will fill all empty routes


    