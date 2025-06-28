# ChongQing Identity Map (重庆身份坐标)

一个基于Streamlit和Redis的"重庆人"身份象限实验系统，通过三大章节问卷与实时数据可视化，探索"重庆人"身份的多维度与多样性。

## 项目简介

本项目是一个剧场实验式的互动问卷系统，旨在通过一系列与重庆相关的身份、文化、地理、生活习惯等问题，结合实时数据分析与可视化，将每一位参与者的"重庆人"身份映射到二维坐标系上。

- **三大章节**：
  - **Chapter 1**：基础身份信息与成长背景
  - **Chapter 2**：文化、地理、生活习惯等多维度问题
  - **Chapter 3**：为观众选择最能代表重庆的游戏
- **身份坐标**：
  - **x轴：实际重庆人**（客观维度）
  - **y轴：精神重庆人**（主观维度）
  - 每位用户的答案经过多维度加权与排名，最终投射到[-100, 100]的二维象限坐标系中
- **可视化**：
  - 交互式象限图，直观展示每位参与者在"重庆人"身份坐标系中的位置
  - 四象限标签：实际重庆人&精神重庆人、实际重庆人&非精神重庆人、非实际重庆人&精神重庆人、非实际重庆人&非精神重庆人

## 快速开始

### 1. 安装Redis

```bash
# macOS
brew install redis

# Ubuntu/Debian
sudo apt-get install redis-server

# 启动Redis
redis-server
```

### 2. 安装Python依赖

```bash
cd questionnaire_system
pip install -r requirements.txt
```

### 3. 启动应用

```bash
# 方式1：使用启动脚本
./run.sh

# 方式2：手动启动
streamlit run app.py
```

应用将在 http://localhost:8501 启动

## 系统架构

```
questionnaire_system/
├── app.py                 # Streamlit主应用
├── backend/
│   ├── redis_manager.py   # Redis数据管理
│   └── scoring_engine.py  # 评分引擎
├── config/
│   └── questions.py       # 问题配置
└── requirements.txt       # 依赖包
```

## 评分规则说明

1. **静态权重**：固定分值，如Y=+1, N=-1
2. **实时排名**：根据数值大小排名，线性映射到分数区间
3. **距离评分**：计算与"中心"（众数或平均值）的距离
4. **众数投票**：选择最多人选的选项得高分
5. **动态Y/N**：根据当前Y/N比例动态决定正负分

## 使用说明

1. 输入用户ID登录系统
2. 在答题页面回答所有问题
3. 提交后自动计算得分
4. 可查看个人成绩、排行榜和问题统计

## 数据存储

所有数据存储在Redis中，包括：
- 用户答案：`user:answers:{user_id}`
- 用户得分：`user:scores:{user_id}`
- 问题统计：`question:stats:{question_id}`
- 排行榜：`leaderboard:users`

## 注意事项

- 距离评分题目在有新用户提交后会触发所有用户重新计算
- 管理工具中的"清空数据"操作不可恢复，请谨慎使用
- 建议定期导出数据备份

## 主要功能

- 三大章节问卷，涵盖身份、文化、地理、生活等多维度
- 实时身份坐标象限可视化
- 用户信息页（昵称、性别、MBTI等）
- 问题统计分析与数据导出
- 提供API接口获取用户得分与问题统计

## 评分与可视化说明

- 每道题目根据不同规则（静态权重、实时排名、众数投票等）计分
- x轴与y轴分别聚合相关题目得分，结合全体用户分布，映射到[-100, 100]区间
- 用户在象限图中的位置实时更新，反映其"重庆人"身份的多维度特征

## API文档

本项目提供以下API接口，方便进行数据集成与二次开发。API服务运行在 `http://localhost:8000`。

### 1. 获取用户得分

- **Endpoint**: `/score/{user_id}`
- **Method**: `GET`
- **Description**: 获取指定用户的最终坐标得分，以及所有参与者的平均分。
- **Example**:
  ```bash
  curl http://localhost:8000/score/test_user
  ```
- **Success Response (200)**:
  ```json
  {
    "user_id": "test_user",
    "final_x": 85.3,
    "final_y": -20.1,
    "average_x": 45.7,
    "average_y": 10.2
  }
  ```
- **Error Response (404)**:
  ```json
  {
    "detail": "User not found"
  }
  ```

### 2. 获取问题答案分布

- **Endpoint**: `/distribution/{question_id}`
- **Method**: `GET`
- **Description**: 获取指定问题的答案分布百分比。
- **Example**:
  ```bash
  curl http://localhost:8000/distribution/f
  ```
- **Success Response (200)**:
  ```json
  {
    "question_id": "f",
    "label": "绕口令——是否出错",
    "total_respondents": 50,
    "distribution": {
      "Y": "30.00%",
      "N": "70.00%"
    }
  }
  ```
- **Error Response (404)**:
  ```json
  {
    "detail": "Question not found"
  }
  ```

访问 `http://localhost:8000/docs` 可查看完整的交互式API文档（由Swagger UI提供）。

## 致谢

本项目灵感来源于剧场实验《伍零零》，感谢所有参与者与支持者！

---

如有建议或合作意向，欢迎联系项目维护者。 