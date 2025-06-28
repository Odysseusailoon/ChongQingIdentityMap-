"""
评分引擎
"""
import numpy as np
from typing import Dict, Any, List, Tuple
from collections import Counter
from config.questions import QUESTIONS, ScoringRule

class ScoringEngine:
    def __init__(self, redis_manager):
        self.redis_manager = redis_manager
        
    def calculate_user_scores(self, user_id: str) -> Dict[str, float]:
        """计算用户所有题目的得分"""
        user_answers = self.redis_manager.get_user_answers(user_id)
        scores = {}
        
        for question_id, answer_data in user_answers.items():
            answer = answer_data["answer"]
            question_config = QUESTIONS.get(question_id)
            
            if not question_config or "rule" not in question_config:
                continue
                
            score = self._calculate_question_score(
                question_id, 
                answer, 
                question_config,
                user_id
            )
            scores[question_id] = score
            
        # 保存得分
        self.redis_manager.save_user_score(user_id, scores)
        
        return scores
    
    def _calculate_question_score(self, question_id: str, answer: Any, 
                                 question_config: Dict[str, Any], user_id: str) -> float:
        """根据评分规则计算单题得分"""
        rule = question_config["rule"]
        
        if rule == ScoringRule.STATIC_WEIGHT.value:
            return self._static_weight_score(answer, question_config)
            
        elif rule == ScoringRule.REAL_TIME_RANK.value:
            return self._real_time_rank_score(question_id, answer, question_config)
            
        elif rule == ScoringRule.DISTANCE_SCORE.value:
            return self._distance_score(question_id, answer, question_config)
            
        elif rule == ScoringRule.MAJORITY_VOTE.value:
            return self._majority_vote_score(question_id, answer, question_config)
            
        elif rule == ScoringRule.COUNT_RANK.value:
            return self._count_rank_score(question_id, answer, question_config)
            
        elif rule == ScoringRule.DYNAMIC_YN.value:
            return self._dynamic_yn_score(question_id, answer, question_config)
            
        elif rule == ScoringRule.VOTE_RANK_STATIC.value:
            return self._vote_rank_static_score(question_id, answer, question_config)
            
        return 0
    
    def _static_weight_score(self, answer: str, config: Dict[str, Any]) -> float:
        """静态权重评分"""
        weights = config.get("weights", {})
        return weights.get(answer, 0)
    
    def _real_time_rank_score(self, question_id: str, answer: float, 
                              config: Dict[str, Any]) -> float:
        """实时排名评分"""
        all_answers = self.redis_manager.get_question_answers(question_id)
        values = [float(a["answer"]) for a in all_answers if isinstance(a["answer"], (int, float))]
        
        if not values:
            return config["range"][1]  # 第一个回答者得满分
            
        # 排序并计算排名
        values.sort(reverse=True)
        rank = values.index(float(answer)) + 1 if float(answer) in values else len(values) + 1
        
        # 线性映射到指定范围
        min_score, max_score = config["range"]
        if len(values) == 1:
            return max_score
        
        score = max_score - (rank - 1) * (max_score - min_score) / (len(values) - 1)
        return round(score, 3)
    
    def _distance_score(self, question_id: str, answer: Any, 
                       config: Dict[str, Any]) -> float:
        """距离评分"""
        all_answers = self.redis_manager.get_question_answers(question_id)
        
        if config.get("metric") == "abs_diff_from_avg":
            # 对于身高题，计算与平均值的距离
            values = [float(a["answer"]) for a in all_answers if isinstance(a["answer"], (int, float))]
            if not values:
                return config["range"][1]
                
            avg_value = np.mean(values)
            distances = [abs(v - avg_value) for v in values]
            user_distance = abs(float(answer) - avg_value)
            
        else:
            # 对于文本题（h1, h2），找出最多人的答案作为"中心"
            answers = [a["answer"] for a in all_answers]
            if not answers:
                return config["range"][1]
                
            # 找出众数（最多人的答案）
            counter = Counter(answers)
            most_common = counter.most_common(1)[0][0]
            
            # 简单的距离计算：相同得满分，不同得0分
            # 实际应用中可以使用更复杂的文本相似度算法
            user_distance = 0 if answer == most_common else 1
            distances = [0 if a == most_common else 1 for a in answers]
        
        # 根据距离排名计算得分
        if not distances:
            return config["range"][1]
            
        distances.sort()
        rank = distances.index(user_distance) + 1 if user_distance in distances else len(distances) + 1
        
        min_score, max_score = config["range"]
        if len(distances) == 1:
            return max_score
            
        score = max_score - (rank - 1) * (max_score - min_score) / (len(distances) - 1)
        return round(score, 3)
    
    def _majority_vote_score(self, question_id: str, answer: Any, 
                            config: Dict[str, Any]) -> float:
        """众数投票评分"""
        stats = self.redis_manager.get_question_stats(question_id)
        
        # 统计各选项/组合的票数
        vote_counts = {}
        
        if isinstance(answer, list):
            # 组合题（如火锅调料）
            for key, value in stats.items():
                if key.startswith("combo:"):
                    combo = key.replace("combo:", "")
                    vote_counts[combo] = int(value)
            
            user_combo = ",".join(sorted(answer))
            
        else:
            # 单选题
            for key, value in stats.items():
                if key.startswith("option:"):
                    option = key.replace("option:", "")
                    vote_counts[option] = int(value)
            
            user_combo = answer
        
        if not vote_counts:
            return config["range"][1]
        
        # 按票数排序
        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 找出用户答案的排名
        user_votes = vote_counts.get(user_combo, 0)
        rank = 1
        for combo, votes in sorted_votes:
            if votes > user_votes:
                rank += 1
        
        # 线性映射
        min_score, max_score = config["range"]
        if len(sorted_votes) == 1:
            return max_score
            
        score = max_score - (rank - 1) * (max_score - min_score) / (len(sorted_votes) - 1)
        return round(score, 3)
    
    def _count_rank_score(self, question_id: str, answer: int, 
                         config: Dict[str, Any]) -> float:
        """计数排名评分（与实时排名相同）"""
        return self._real_time_rank_score(question_id, answer, config)
    
    def _dynamic_yn_score(self, question_id: str, answer: str, 
                         config: Dict[str, Any]) -> float:
        """动态Y/N判定评分"""
        stats = self.redis_manager.get_question_stats(question_id)
        
        y_count = int(stats.get("option:Y", 0))
        n_count = int(stats.get("option:N", 0))
        
        if y_count > n_count:
            return 1 if answer == "Y" else -1
        else:
            return 1 if answer == "N" else -1
    
    def _vote_rank_static_score(self, question_id: str, answer: str,
                                 config: Dict[str, Any]) -> float:
        """投票排名（静态分数）评分"""
        all_answers = self.redis_manager.get_question_answers(question_id)
        answers = [a["answer"] for a in all_answers]
        
        if not answers:
            return config["scores"][0] # First voter gets top score
            
        vote_counts = Counter(answers)
        # Sort options by vote count, descending.
        # Options with 0 votes won't be in vote_counts, so we add them.
        sorted_options = sorted(
            config["options"],
            key=lambda option: vote_counts.get(option, 0),
            reverse=True
        )
        
        try:
            rank = sorted_options.index(answer) + 1
        except ValueError:
            return 0 # Should not happen if answer is valid

        # Assign score based on rank
        scores = config.get("scores", [])
        if 1 <= rank <= len(scores):
            return scores[rank - 1]
        return 0

    def calculate_axes_scores(self, user_id: str):
        """计算用户的X, Y轴得分"""
        scores = self.redis_manager.get_user_scores(user_id)
        answers = self.redis_manager.get_user_answers(user_id)

        # X-axis: 实际重庆人
        x_keys = ["a1", "a2", "b1", "c1", "c2", "c3", "e"]
        raw_x = sum(scores.get(k, 0) for k in x_keys)

        b1_answer = answers.get("b1", {}).get("answer")
        if b1_answer == "YY":
            raw_x += scores.get("b2", 0)
        elif b1_answer == "YN":
            raw_x += scores.get("b3", 0) + scores.get("b4", 0)
        elif b1_answer == "NN":
            raw_x += scores.get("b5", 0)
        
        # Y-axis: 精神重庆人
        # Assuming D1%, L%, etc. are all 100%
        y_keys = ["f", "g", "h1", "h2", "h3", "i", "j", "k"] # Base keys for Y-axis
        raw_y = sum(scores.get(k, 0) for k in y_keys)
        
        # Add score based on the game chosen in 'r'
        game_choice = answers.get("r", {}).get("answer")
        if game_choice == "打脏话牌": # Corresponds to question l
            raw_y += scores.get("l", 0)
        elif game_choice == "火锅油碟": # Corresponds to question m
            raw_y += scores.get("m", 0)
        elif game_choice == "打麻将": # Corresponds to question n
            raw_y += scores.get("n", 0)
        elif game_choice == "量身高": # Corresponds to questions o1-o5
            o_keys = ["o1", "o2", "o3", "o4", "o5"]
            raw_y += sum(scores.get(k, 0) for k in o_keys)

        self.redis_manager.save_user_raw_axes(user_id, raw_x, raw_y)
        return raw_x, raw_y

    def get_final_axes_scores(self, user_id: str) -> Tuple[float, float]:
        """获取用户最终的[-100, 100]范围内的坐标"""
        all_axes_scores = self.redis_manager.get_all_user_raw_axes()
        
        user_raw_x, user_raw_y = self.redis_manager.get_user_raw_axes(user_id)

        all_raw_x = [s['x'] for s in all_axes_scores]
        all_raw_y = [s['y'] for s in all_axes_scores]

        def map_to_scale(value, values):
            if len(values) <= 1:
                return 0
            
            median_val = np.median(values)
            min_val = np.min(values)
            max_val = np.max(values)

            if value >= median_val:
                # Avoid division by zero if all values above median are the same
                if max_val == median_val:
                    return 0
                return 100 * (value - median_val) / (max_val - median_val)
            else:
                # Avoid division by zero if all values below median are the same
                if min_val == median_val:
                    return 0
                return -100 * (value - median_val) / (min_val - median_val)

        final_x = map_to_scale(user_raw_x, all_raw_x)
        final_y = map_to_scale(user_raw_y, all_raw_y)
        
        self.redis_manager.save_user_final_axes(user_id, final_x, final_y)
        return final_x, final_y

    def calculate_question_scores(self, question_id: str) -> Dict[str, Any]:
        """计算问题的统计得分"""
        all_answers = self.redis_manager.get_question_answers(question_id)
        
        if not all_answers:
            return {
                "avg_score": 0,
                "total_respondents": 0,
                "distribution": {}
            }
        
        # 获取所有用户的该题得分
        scores = []
        for answer_data in all_answers:
            user_id = answer_data["user_id"]
            user_scores = self.redis_manager.get_user_scores(user_id)
            if question_id in user_scores:
                scores.append(user_scores[question_id])
        
        # 计算统计信息
        score_data = {
            "avg_score": np.mean(scores) if scores else 0,
            "total_respondents": len(all_answers),
            "distribution": dict(Counter(scores))
        }
        
        # 保存统计信息
        self.redis_manager.save_question_score(question_id, score_data)
        
        return score_data
    
    def get_average_axes_scores(self) -> Tuple[float, float]:
        """计算所有用户的平均坐标"""
        all_final_axes = self.redis_manager.get_all_user_final_axes()
        if not all_final_axes:
            return 0, 0
        
        avg_x = np.mean([s['x'] for s in all_final_axes])
        avg_y = np.mean([s['y'] for s in all_final_axes])
        return avg_x, avg_y

    def recalculate_all_scores(self):
        """重新计算所有用户的得分（用于距离评分等需要全局信息的题目）"""
        all_users = self.redis_manager.get_all_users()
        
        # First, recalculate individual question scores for all users
        for user_id in all_users:
            self.calculate_user_scores(user_id)
        
        # Then, calculate raw axes scores for all users
        for user_id in all_users:
            self.calculate_axes_scores(user_id)
            
        # Finally, calculate final scaled axes scores for all users
        for user_id in all_users:
            self.get_final_axes_scores(user_id)

        # 更新问题统计
        for question_id in QUESTIONS.keys():
            if QUESTIONS[question_id].get("rule"):
                self.calculate_question_scores(question_id) 