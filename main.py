from fastapi import FastAPI
import json
import random

app = FastAPI()

with open("questions.json", "r", encoding="UTF-8") as f:
    content = json.load(f)
    questions_with_answers = content["questions"]
    remove_keys = ["author", "answer", "topic"]
    questions_without_answers = [{key: value for key, value in q.items() if key not in remove_keys} for q in questions_with_answers]

@app.get("/")
def give_quiz(student: str):
    quiz_questions = random.sample(questions_without_answers, len(questions_without_answers))  # questions selection would be more complicated
    return {
        "version": 1,
        "student": student,
        "attempt": 0, # TODO how to count attempts?
        "questions": quiz_questions
    }