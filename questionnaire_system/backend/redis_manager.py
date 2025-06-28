"""
Redis数据管理器
"""
import redis
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

class RedisManager:
    def __init__(self, host='localhost', port=6379, db=0, decode_responses=True):
        """初始化Redis连接"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses
        )
        
    def save_user_answer(self, user_id: str, question_id: str, answer: Any) -> bool:
        """保存用户答案"""
        try:
            # 用户答案键：user:answers:{user_id}
            key = f"user:answers:{user_id}"
            
            # 将答案转换为JSON字符串存储
            answer_data = {
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            }
            
            self.redis_client.hset(key, question_id, json.dumps(answer_data))
            
            # 记录该问题的所有回答者
            self.redis_client.sadd(f"question:respondents:{question_id}", user_id)
            
            # 更新问题的答案统计
            self._update_question_stats(question_id, answer)
            
            return True
        except Exception as e:
            print(f"Error saving answer: {e}")
            return False
    
    def get_user_answers(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有答案"""
        key = f"user:answers:{user_id}"
        raw_answers = self.redis_client.hgetall(key)
        
        answers = {}
        for question_id, answer_json in raw_answers.items():
            answer_data = json.loads(answer_json)
            answers[question_id] = answer_data
            
        return answers
    
    def get_question_answers(self, question_id: str) -> List[Dict[str, Any]]:
        """获取某个问题的所有答案"""
        respondents = self.redis_client.smembers(f"question:respondents:{question_id}")
        
        all_answers = []
        for user_id in respondents:
            answer_json = self.redis_client.hget(f"user:answers:{user_id}", question_id)
            if answer_json:
                answer_data = json.loads(answer_json)
                all_answers.append({
                    "user_id": user_id,
                    "answer": answer_data["answer"],
                    "timestamp": answer_data["timestamp"]
                })
                
        return all_answers
    
    def save_user_score(self, user_id: str, scores: Dict[str, float]) -> bool:
        """保存用户得分"""
        try:
            # 保存每题得分
            score_key = f"user:scores:{user_id}"
            for question_id, score in scores.items():
                self.redis_client.hset(score_key, question_id, score)
            
            # 计算并保存总分
            # total_score = sum(scores.values())
            # self.redis_client.hset(score_key, "total", total_score)
            
            # # 更新用户排行榜
            # self.redis_client.zadd("leaderboard:users", {user_id: total_score})
            
            return True
        except Exception as e:
            print(f"Error saving score: {e}")
            return False
    
    def get_user_scores(self, user_id: str) -> Dict[str, float]:
        """获取用户得分"""
        score_key = f"user:scores:{user_id}"
        raw_scores = self.redis_client.hgetall(score_key)
        
        scores = {}
        for question_id, score in raw_scores.items():
            scores[question_id] = float(score)
            
        return scores
    
    def save_question_score(self, question_id: str, score_data: Dict[str, Any]) -> bool:
        """保存问题得分统计"""
        try:
            key = f"question:scores:{question_id}"
            self.redis_client.hset(key, "avg_score", score_data.get("avg_score", 0))
            self.redis_client.hset(key, "total_respondents", score_data.get("total_respondents", 0))
            self.redis_client.hset(key, "score_distribution", json.dumps(score_data.get("distribution", {})))
            
            return True
        except Exception as e:
            print(f"Error saving question score: {e}")
            return False
    
    def get_question_stats(self, question_id: str) -> Dict[str, Any]:
        """获取问题统计信息"""
        stats_key = f"question:stats:{question_id}"
        return self.redis_client.hgetall(stats_key)
    
    def _update_question_stats(self, question_id: str, answer: Any):
        """更新问题统计信息"""
        stats_key = f"question:stats:{question_id}"
        
        # 对于选择题，统计每个选项的数量
        if isinstance(answer, str):
            self.redis_client.hincrby(stats_key, f"option:{answer}", 1)
        
        # 对于数值题，存储所有值用于计算
        elif isinstance(answer, (int, float)):
            values_key = f"question:values:{question_id}"
            self.redis_client.rpush(values_key, answer)
        
        # 对于组合题（如火锅调料），存储组合
        elif isinstance(answer, list):
            combo_key = ",".join(sorted(answer))
            self.redis_client.hincrby(stats_key, f"combo:{combo_key}", 1)
    
    def get_all_users(self) -> List[str]:
        """获取所有用户ID"""
        users = set()
        for key in self.redis_client.scan_iter("user:answers:*"):
            user_id = key.split(":")[-1]
            users.add(user_id)
        return list(users)
    
    def get_leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取排行榜"""
        leaderboard_data = self.redis_client.zrevrange("leaderboard:users", 0, top_n-1, withscores=True)
        
        leaderboard = []
        for rank, (user_id, score) in enumerate(leaderboard_data, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "total_score": score
            })
            
        return leaderboard
    
    def save_user_raw_axes(self, user_id: str, raw_x: float, raw_y: float):
        """保存用户原始轴得分"""
        key = f"user:axes:raw:{user_id}"
        self.redis_client.hset(key, mapping={"x": raw_x, "y": raw_y})

    def get_user_raw_axes(self, user_id: str) -> tuple[float, float]:
        """获取用户原始轴得分"""
        key = f"user:axes:raw:{user_id}"
        data = self.redis_client.hgetall(key)
        return float(data.get("x", 0)), float(data.get("y", 0))

    def get_all_user_raw_axes(self) -> List[Dict[str, float]]:
        """获取所有用户的原始轴得分"""
        all_scores = []
        for key in self.redis_client.scan_iter("user:axes:raw:*"):
            data = self.redis_client.hgetall(key)
            if "x" in data and "y" in data:
                all_scores.append({"x": float(data["x"]), "y": float(data["y"])})
        return all_scores
        
    def save_user_final_axes(self, user_id: str, final_x: float, final_y: float):
        """保存用户最终轴得分"""
        key = f"user:axes:final:{user_id}"
        self.redis_client.hset(key, mapping={"x": final_x, "y": final_y})

    def get_user_final_axes(self, user_id: str) -> tuple[float, float]:
        """获取用户最终轴得分"""
        key = f"user:axes:final:{user_id}"
        data = self.redis_client.hgetall(key)
        return float(data.get("x", 0)), float(data.get("y", 0))

    def get_all_user_final_axes(self) -> List[Dict[str, float]]:
        """获取所有用户的最终轴得分"""
        all_scores = []
        for key in self.redis_client.scan_iter("user:axes:final:*"):
            data = self.redis_client.hgetall(key)
            if "x" in data and "y" in data:
                all_scores.append({"x": float(data["x"]), "y": float(data["y"])})
        return all_scores

    def get_question_respondent_count(self, question_id: str) -> int:
        """获取问题的回答者总数"""
        return self.redis_client.scard(f"question:respondents:{question_id}")

    def clear_all_data(self):
        """清空所有数据（谨慎使用）"""
        self.redis_client.flushdb()
    
    def export_data(self) -> Dict[str, Any]:
        """导出所有数据"""
        data = {
            "users": {},
            "questions": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 导出用户数据
        for user_id in self.get_all_users():
            data["users"][user_id] = {
                "answers": self.get_user_answers(user_id),
                "scores": self.get_user_scores(user_id)
            }
        
        # 导出问题统计
        from config.questions import QUESTIONS
        for question_id in QUESTIONS.keys():
            data["questions"][question_id] = {
                "stats": self.get_question_stats(question_id),
                "answers": self.get_question_answers(question_id)
            }
        
        return data 