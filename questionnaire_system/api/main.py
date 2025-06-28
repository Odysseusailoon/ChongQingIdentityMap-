from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Tuple, List
import numpy as np
import sys
import os

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
    distribution: Dict[str, str]

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
    The distribution is returned as a dictionary where keys are the
    answer options and values are their percentage representation.
    """
    redis = get_redis_manager()
    
    if question_id not in QUESTIONS:
        raise HTTPException(status_code=404, detail="Question not found")
        
    question_config = QUESTIONS[question_id]
    stats = redis.get_question_stats(question_id)
    total_respondents = redis.get_question_respondent_count(question_id)

    distribution = {}
    if total_respondents > 0:
        if question_config['type'] in [QuestionType.SINGLE_CHOICE.value, QuestionType.COMBINATION.value]:
            vote_counts = {}
            prefix = "option:" if question_config['type'] == QuestionType.SINGLE_CHOICE.value else "combo:"
            
            options = question_config.get('options', [])
            if question_config['type'] == QuestionType.COMBINATION.value:
                # For combination, we discover options from stats
                options = [k.replace(prefix, "") for k in stats if k.startswith(prefix)]

            for option in options:
                count = int(stats.get(f"{prefix}{option}", 0))
                vote_counts[option] = count

            for option, count in vote_counts.items():
                percentage = (count / total_respondents) * 100
                distribution[option] = f"{percentage:.2f}%"
        else:
            distribution["error"] = "Distribution for this question type is not supported via this endpoint."
    
    return {
        "question_id": question_id,
        "label": question_config['label'],
        "total_respondents": total_respondents,
        "distribution": distribution,
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the ChongQing Identity Map API. Visit /docs for documentation."} 