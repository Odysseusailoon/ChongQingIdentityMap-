from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Tuple, List
import numpy as np
import sys
import os
from collections import Counter
import json

# Add project root to path to allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.redis_manager import RedisManager
from backend.scoring_engine import ScoringEngine
from config.questions import QUESTIONS, QuestionType

app = FastAPI(
    title="ChongQing Identity Map API",
    description="API for fetching user scores and question distributions from the ChongQing Identity Map project.",
    version="1.0.0",
)

# --- Pydantic Models ---
class ScoreResponse(BaseModel):
    user_id: str
    final_x: float
    final_y: float
    average_x: float
    average_y: float

class DistributionResponse(BaseModel):
    question_id: str
    label: str
    total_respondents: int
    distribution: Dict[str, Any]

class AllQuestionsResponse(BaseModel):
    questions: Dict[str, str]

# --- Dependencies ---
def get_scoring_engine():
    redis_manager = RedisManager()
    return ScoringEngine(redis_manager)

def get_redis_manager():
    return RedisManager()

# --- API Endpoints ---
@app.get("/score/{user_id}", response_model=ScoreResponse)
def get_user_score(user_id: str):
    """
    Retrieves the final (x, y) coordinates for a given user,
    as well as the average coordinates for all participants.
    """
    try:
        scoring_engine = get_scoring_engine()
        
        # Check if user exists
        if not get_redis_manager().get_user_answers(user_id):
            raise HTTPException(status_code=404, detail="User not found")

        final_x, final_y = scoring_engine.get_final_axes_scores(user_id)
        avg_x, avg_y = scoring_engine.get_average_axes_scores()
        
        return {
            "user_id": user_id,
            "final_x": final_x,
            "final_y": final_y,
            "average_x": avg_x,
            "average_y": avg_y,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/distribution/{question_id}", response_model=DistributionResponse)
def get_question_distribution(question_id: str):
    """
    Retrieves the answer distribution for a given question.
    - For SINGLE_CHOICE and COMBINATION questions, it returns the percentage for each option.
    - For TEXT, NUMBER, and other types, it returns the count for each unique answer.
    """
    redis = get_redis_manager()
    
    if question_id not in QUESTIONS:
        raise HTTPException(status_code=404, detail="Question not found")
        
    question_config = QUESTIONS[question_id]
    all_answers_data = redis.get_question_answers(question_id)
    total_respondents = len(all_answers_data)
    
    # Convert all answers to a hashable type (string) to be used in Counter
    stringified_answers = [json.dumps(a['answer'], sort_keys=True) for a in all_answers_data]
    answers = [a['answer'] for a in all_answers_data]

    distribution = {}
    if total_respondents > 0:
        q_type = question_config.get('type')

        if q_type == QuestionType.SINGLE_CHOICE.value:
            counts = Counter(answers)
            options = question_config.get('options', [])
            for option in options:
                count = counts.get(option, 0)
                percentage = (count / total_respondents) * 100
                distribution[option] = f"{percentage:.2f}%"
        
        elif q_type == QuestionType.COMBINATION.value:
            # For combinations, we treat each unique combination as an option
            # Answers are lists, so we sort them to ensure consistent representation
            flat_list = [",".join(sorted(ans)) for ans in answers if isinstance(ans, list)]
            counts = Counter(flat_list)
            for combo, count in counts.items():
                percentage = (count / total_respondents) * 100
                distribution[combo] = f"{percentage:.2f}%"

        else: # For TEXT, NUMBER, etc.
            # Use the stringified list for counting to handle potential unhashable types
            counts = Counter(stringified_answers)
            # Create a user-friendly distribution dict
            for stringified_answer, count in counts.items():
                # Convert the string back to its original Python object for the response key
                original_answer = json.loads(stringified_answer)
                # Ensure the key is a string for the Pydantic model
                distribution[str(original_answer)] = count

    return {
        "question_id": question_id,
        "label": question_config['label'],
        "total_respondents": total_respondents,
        "distribution": distribution,
    }

@app.get("/questions", response_model=AllQuestionsResponse)
def get_all_questions():
    """
    Retrieves a list of all available question IDs and their labels.
    """
    return {"questions": {qid: qconfig['label'] for qid, qconfig in QUESTIONS.items()}}

@app.get("/")
def read_root():
    return {"message": "Welcome to the ChongQing Identity Map API. Visit /docs for documentation."} 