from fastapi import FastAPI
import json
import random
from pathlib import Path

app = FastAPI()

# student_answers_example = {
#   "version": 1,
#   "student": "asd",
#   "attempt": 0,
#   "questions": [
#     {
#       "id": 4,
#       "question": "Сколько винтов у теодолита?",
#       "student_answer": 100
#     }
#   ]
# }

# open files once and use variables after
with open("questions.json", "r", encoding="UTF-8") as f:
    content = json.load(f)
    all_questions = content["questions"]
    topics = ["теодолит"]
    topics_questions = [q for q in all_questions if q.get("topic") in topics]
    remove_keys = ["author", "answer", "topic"]
    quiz_questions = [{key: value for key, value in q.items() if key not in remove_keys} for q in topics_questions]

with open("students.json", "r", encoding="UTF-8") as f:
    content = json.load(f)
    students = content["students"]

# create folders if they don't exist
Path("answers").mkdir(parents=True, exist_ok=True)
Path("results").mkdir(parents=True, exist_ok=True)

def check_answers(student_answers: dict):
    checked_answers = student_answers
    for a in checked_answers["questions"]:
        question_id = a["id"]
        a["correct_answer"] = next(question["answer"] for question in topics_questions if question["id"] == question_id)
        a["is_correct"] = a["student_answer"] == a["correct_answer"]

    checked_answers["correct"] = sum([a["is_correct"] for a in checked_answers["questions"]])
    checked_answers["correct_percent"] = round(checked_answers["correct"] * 100 / len(checked_answers["questions"]))
    return checked_answers

@app.get("/students")
def show_students():
    return students

@app.get("/give_quiz")
def give_quiz(student_id, student: str):
    """Give json-like quiz

    Args:
        student_id (int): indentificator of a student
        student (str): student name

    Returns:
        obj: json-like quiz
    """
    quiz_length = 1
    questions_for_student = random.sample(quiz_questions, len(quiz_questions))[:quiz_length]  # random order and only first n questions
    return {
        "version": 1,
        "student_id": student_id,
        "student": student,
        "attempt": 0, # TODO how to count attempts?
        "questions": questions_for_student
    }

@app.get("/get_student_answers")
def get_answers(student_answers: str):
    """Save answers as-is and checked answers

    Args:
        student_answers (str): json-like string with student's answers

    Returns:
        str: student name
    """
    json_answers = json.loads(student_answers)
    print(json_answers)
    path_to_answers = f'answers/{json_answers["student"]}_{json_answers["attempt"]}.json'
    with open(path_to_answers, 'w', encoding='utf-8') as f:
        json.dump(json_answers, f, ensure_ascii=False)

    path_to_results = f'results/{json_answers["student"]}_{json_answers["attempt"]}.json'
    with open(path_to_results, 'w', encoding='utf-8') as f:
        json.dump(check_answers(json_answers), f, ensure_ascii=False)  # TODO move checking to background?
    return json_answers["student"]