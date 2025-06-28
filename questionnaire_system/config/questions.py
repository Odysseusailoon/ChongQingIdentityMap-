"""
问题配置文件
"""
from enum import Enum
from typing import Dict, Any, List, Optional

class QuestionType(Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    TEXT = "text"
    COMBINATION = "combination"

class ScoringRule(Enum):
    STATIC_WEIGHT = "static_weight"
    REAL_TIME_RANK = "real_time_rank"
    DISTANCE_SCORE = "distance_score"
    MAJORITY_VOTE = "majority_vote"
    COUNT_RANK = "count_rank"
    DYNAMIC_YN = "dynamic_yn"
    VOTE_RANK_STATIC = "vote_rank_static"
    CONDITIONAL_RANK = "conditional_rank"
    STATIC_MAPPING = "static_mapping"

QUESTIONS: Dict[str, Dict[str, Any]] = {
    # Unscored
    "q1": {"id": "q1", "label": "称呼", "type": QuestionType.TEXT.value},
    "p": {"id": "p", "label": "MBTI", "type": QuestionType.TEXT.value},
    "q2": {"id": "q2", "label": "性别", "type": QuestionType.SINGLE_CHOICE.value, "options": ["男", "女"]},
    
    # Chapter 1 - Static Weights
    "a1": {"id": "a1", "label": "身份证前三位", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 1, "N": -1}},
    "a2": {"id": "a2", "label": "出生年份", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 1, "N": 0}}, # Assuming Y is >=1997
    "b1": {"id": "b1", "label": "父母是否来自重庆", "type": QuestionType.SINGLE_CHOICE.value, "options": ["YY", "YN", "NN"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"YY": 1, "YN": 0, "NN": -1}},
    "b2": {"id": "b2", "label": "父母是否来自主城九区", "type": QuestionType.SINGLE_CHOICE.value, "options": ["YY", "YN", "NN"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"YY": 1, "YN": 0.5, "NN": 0}},
    "b3": {"id": "b3", "label": "重庆的一方是否来自主城九区", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 1, "N": 0.5}},
    "b4": {"id": "b4", "label": "非重庆的一方是否来自四川", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 0, "N": -0.5}},
    "b5": {"id": "b5", "label": "父母是否都来自四川", "type": QuestionType.SINGLE_CHOICE.value, "options": ["YY", "YN", "NN"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"YY": 0.5, "YN": 0, "NN": -1}},
    "c1": {"id": "c1", "label": "童年是否在重庆", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 1, "N": -1}},
    "c2": {"id": "c2", "label": "常居地是否在重庆", "type": QuestionType.SINGLE_CHOICE.value, "options": ["Y", "N"], "rule": ScoringRule.STATIC_WEIGHT.value, "weights": {"Y": 1, "N": -1}},
    
    # Chapter 1 - Dynamic
    "c3": {"id": "c3", "label": "在重庆待的时长", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 1], "input_type": "months"},
    "e": {"id": "e", "label": "重庆的中心", "type": QuestionType.TEXT.value, "rule": ScoringRule.DISTANCE_SCORE.value, "range": [0, 1]},
    "d": {"id": "d", "label": "维度选择：重庆人身份认同的核心矛盾", "type": QuestionType.SINGLE_CHOICE.value, "options": ["区县", "直辖", "素养"]},

    # Chapter 2
    "f": {"id": "f", "label": "绕口令——出错次数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.CONDITIONAL_RANK.value, "range": [0, 1], "input_type": "positive_integer"},
    "g": {
        "id": "g", "label": "迷宫打卡次数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.STATIC_MAPPING.value,
        "mapping": {0: 0.0, 1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4, 5: 0.5, 6: 0.6, 7: 0.7, 8: 0.8, 9: 0.9, 10: 1.0},
        "input_type": "positive_integer"
    },
    "h1": {"id": "h1", "label": "切蛋糕 - 区县 (得分)", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 1]},
    "h2": {"id": "h2", "label": "切蛋糕 - 直辖 (得分)", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 1]},
    "j": {"id": "j", "label": "夜景图片", "type": QuestionType.SINGLE_CHOICE.value, "options": ["图片1", "图片2", "图片3", "图片4", "图片5", "图片6", "图片7"], "rule": ScoringRule.MAJORITY_VOTE.value, "range": [0, 1]},
    "k": {"id": "k", "label": "山火志愿者对象", "type": QuestionType.SINGLE_CHOICE.value, "options": ["医疗队", "摩托车队", "油锯手队", "不捐钱"], "rule": ScoringRule.MAJORITY_VOTE.value, "range": [0, 1]},
    "l": {"id": "l", "label": "脏话牌 - 使用重庆脏话次数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.CONDITIONAL_RANK.value, "range": [0, 1], "input_type": "positive_integer"},
    "m": {"id": "m", "label": "火锅油碟", "type": QuestionType.COMBINATION.value, "options": [str(i) for i in range(1, 19)], "rule": ScoringRule.MAJORITY_VOTE.value, "range": [0, 1]},
    "n": {"id": "n", "label": "打麻将——胡牌番数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 1], "input_type": "positive_integer"},
    "o1": {"id": "o1", "label": "量身高：身高", "type": QuestionType.NUMBER.value, "rule": ScoringRule.DISTANCE_SCORE.value, "range": [0, 0.2], "input_type": "height_cm", "metric": "abs_diff_from_avg"},
    "o2": {"id": "o2", "label": "量身高：社保年限", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 0.2], "input_type": "years"},
    "o3": {"id": "o3", "label": "量身高：今日在山城巷消费", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 0.2], "input_type": "money"},
    "o4": {"id": "o4", "label": "量身高：2024 年带来的外地游客数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 0.2], "input_type": "count"},
    "o5": {"id": "o5", "label": "量身高：人生迄今带来的重庆户口数", "type": QuestionType.NUMBER.value, "rule": ScoringRule.REAL_TIME_RANK.value, "range": [0, 0.2], "input_type": "count"}
} 