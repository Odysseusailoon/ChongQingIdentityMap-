"""
问卷系统主应用
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from backend.redis_manager import RedisManager
from backend.scoring_engine import ScoringEngine
from config.questions import QUESTIONS, QuestionType, ScoringRule
import json
from datetime import datetime

# 初始化
@st.cache_resource
def init_redis():
    return RedisManager()

@st.cache_resource
def init_scoring_engine():
    redis_manager = init_redis()
    return ScoringEngine(redis_manager)

# 页面配置
st.set_page_config(
    page_title="重庆特色问答系统",
    page_icon="🌶️",
    layout="wide"
)

# 初始化session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'current_answers' not in st.session_state:
    st.session_state.current_answers = {}

# 侧边栏
with st.sidebar:
    st.title("🌶️ 重庆特色问答系统")
    
    # 用户登录
    st.header("用户登录")
    user_id = st.text_input("请输入用户ID", key="user_id_input")
    
    if st.button("进入系统"):
        if user_id:
            st.session_state.user_id = user_id
            st.success(f"欢迎 {user_id}!")
        else:
            st.error("请输入用户ID")
    
    # 功能选择
    if st.session_state.user_id:
        st.divider()
        page = st.radio(
            "选择功能",
            ["答题", "查看成绩", "排行榜", "问题统计", "管理工具"]
        )
    else:
        page = None

# 主页面
if not st.session_state.user_id:
    st.title("欢迎使用重庆特色问答系统")
    st.info("请在左侧输入用户ID登录")
else:
    redis_manager = init_redis()
    scoring_engine = init_scoring_engine()
    
    if page == "答题":
        st.title("答题页面")
        st.write(f"当前用户: {st.session_state.user_id}")
        
        # 获取用户已答题目
        user_answers = redis_manager.get_user_answers(st.session_state.user_id)
        
        # 定义章节问题
        chapter1_keys = ["q1", "q2", "p", "a1", "a2", "b1", "b2", "b3", "b4", "b5", "d", "c1", "c2", "c3", "e"]
        chapter2_keys = [k for k in QUESTIONS.keys() if k not in chapter1_keys]

        chapter1_questions = {k: QUESTIONS[k] for k in chapter1_keys if k in QUESTIONS}
        chapter2_questions = {k: QUESTIONS[k] for k in chapter2_keys if k in QUESTIONS}

        # 创建选项卡
        tab1, tab2 = st.tabs(["Chapter 1", "Chapter 2"])

        with st.form("questionnaire_form"):
            answers = {}

            with tab1:
                st.header("Chapter 1")
                for question_id, question in chapter1_questions.items():
                    st.subheader(f"{question_id}. {question['label']}")
                    existing_answer = user_answers.get(question_id, {}).get("answer")
                    
                    if question.get('type') == QuestionType.SINGLE_CHOICE.value:
                        custom_labels = {
                            "b1": {"都是重庆人": "YY", "一方是重庆人": "YN", "都不是重庆人": "NN"},
                            "b2": {"都来自主城九区": "YY", "一方来自主城九区": "YN", "都不来自主城九区": "NN"},
                            "b5": {"都来自四川": "YY", "一方来自四川": "YN", "都不来自四川": "NN"},
                        }
                        yn_map = {"是": "Y", "否": "N"}
                        
                        label_map = None
                        if question_id in custom_labels:
                            label_map = custom_labels[question_id]
                        elif question['options'] == ["Y", "N"]:
                            label_map = yn_map

                        if label_map:
                            display_options = list(label_map.keys())
                            display_answer = None
                            if existing_answer:
                                for k, v in label_map.items():
                                    if v == existing_answer:
                                        display_answer = k
                                        break
                            
                            index = display_options.index(display_answer) if display_answer in display_options else 0
                            
                            selected_label = st.radio(
                                "请选择",
                                display_options,
                                key=f"q_{question_id}",
                                index=index
                            )
                            answer = label_map[selected_label]
                        else:
                            answer = st.radio(
                                "请选择",
                                question['options'],
                                key=f"q_{question_id}",
                                index=question['options'].index(existing_answer) if existing_answer in question['options'] else 0
                            )
                        answers[question_id] = answer

                    elif question.get('type') == QuestionType.TEXT.value:
                        answer = st.text_input("请输入答案", value=existing_answer if existing_answer else "", key=f"q_{question_id}")
                        answers[question_id] = answer
                    elif question.get('type') == QuestionType.NUMBER.value:
                        input_type = question.get('input_type', 'number')
                        if input_type == 'months':
                            answer = st.number_input(
                                "请输入月数", min_value=0, step=1,
                                value=int(existing_answer) if existing_answer else 0, key=f"q_{question_id}"
                            )
                        else:
                            answer = st.number_input("请输入数字", value=int(existing_answer) if existing_answer else 0, key=f"q_{question_id}")
                        answers[question_id] = answer

            with tab2:
                st.header("Chapter 2")

                chapter2_explanations = {
                    "f": "请如实回答您在绕口令挑战中是否出错了。",
                    "g": "请输入您在迷宫环节成功打卡的次数。您的表现将与他人实时排名。",
                    "h1": "这是一个关于地理感知的测试。请大致输入您认为的重庆'老区县'范围。",
                    "h2": "这是一个关于地理感知的测试。请大致输入您认为的重庆'直辖'后新增的区域。",
                    "h3": "请选择您认为最'重庆'的选项。您的选择将与大多数人进行比较。",
                    "i": "考验您对重庆本土文化（方言、地名等）的了解程度，请输入您能想到的相关词汇数量。",
                    "j": "请选出您最喜欢的重庆夜景图片。这是一个投票，选择多数派的选项会得分。",
                    "k": "在关于2022年重庆山火的公共讨论中，您认为'山火文'主要指向哪个群体？",
                    "l": "在之前的互动中，您是否使用了重庆方言或特色口头禅？",
                    "m": "请选择您吃火锅时必加的油碟调料。我们将根据所有人的选择，形成一个'标准油碟'并据此评分。",
                    "n": "请输入您在本轮麻将游戏中胡牌的番数。番数越高，排名越高。",
                    "o1": "您的身高将与所有参与者的平均身高进行比较。",
                    "o2": "您在重庆缴纳社保的年限。",
                    "o3": "您今日在山城巷的总消费金额（元）。",
                    "o4": "在2024年，您为重庆带来了多少外地游客？",
                    "o5": "迄今为止，您为重庆'贡献'了几个新户口（例如子女、配偶等）？"
                }

                for question_id, question in chapter2_questions.items():
                    st.subheader(f"{question_id}. {question['label']}")
                    if question_id in chapter2_explanations:
                        st.caption(chapter2_explanations[question_id])

                    existing_answer = user_answers.get(question_id, {}).get("answer")

                    if question['type'] == QuestionType.SINGLE_CHOICE.value:
                        
                        custom_labels = None
                        if question_id == 'f':
                            custom_labels = {"出错了": "Y", "没出错": "N"}
                        elif question_id == 'l':
                            custom_labels = {"使用了": "Y", "没有使用": "N"}

                        if custom_labels:
                            display_options = list(custom_labels.keys())
                            display_answer = None
                            if existing_answer:
                                for k, v in custom_labels.items():
                                    if v == existing_answer:
                                        display_answer = k
                                        break
                            
                            index = display_options.index(display_answer) if display_answer in display_options else 0
                            
                            selected_label = st.radio(
                                "请选择",
                                display_options,
                                key=f"q_{question_id}",
                                index=index
                            )
                            answer = custom_labels[selected_label]
                        else:
                            answer = st.radio(
                                "请选择",
                                question['options'],
                                key=f"q_{question_id}",
                                index=question['options'].index(existing_answer) if existing_answer in question['options'] else 0
                            )
                        answers[question_id] = answer
                    elif question['type'] == QuestionType.NUMBER.value:
                        input_type = question.get('input_type', 'number')
                        
                        if input_type == 'positive_integer':
                            answer = st.number_input(
                                "请输入正整数", min_value=0, step=1,
                                value=int(existing_answer) if existing_answer else 0, key=f"q_{question_id}"
                            )
                        elif input_type == 'height_cm':
                            answer = st.number_input(
                                "请输入身高(cm)", min_value=50.0, max_value=250.0, step=0.1,
                                value=float(existing_answer) if existing_answer else 170.0, key=f"q_{question_id}"
                            )
                        elif input_type == 'years':
                            answer = st.number_input(
                                "请输入年限", min_value=0.0, step=0.5,
                                value=float(existing_answer) if existing_answer else 0.0, key=f"q_{question_id}"
                            )
                        elif input_type == 'money':
                            answer = st.number_input(
                                "请输入金额(元)", min_value=0.0, step=1.0,
                                value=float(existing_answer) if existing_answer else 0.0, key=f"q_{question_id}"
                            )
                        else: # count
                            answer = st.number_input(
                                "请输入数量", min_value=0, step=1,
                                value=int(existing_answer) if existing_answer else 0, key=f"q_{question_id}"
                            )
                        answers[question_id] = answer
                    elif question['type'] == QuestionType.TEXT.value:
                        answer = st.text_input(
                            "请输入答案", value=existing_answer if existing_answer else "", key=f"q_{question_id}"
                        )
                        answers[question_id] = answer
                    elif question['type'] == QuestionType.COMBINATION.value:
                        selected = st.multiselect(
                            "请选择调料组合", question['options'],
                            default=existing_answer if isinstance(existing_answer, list) else [], key=f"q_{question_id}"
                        )
                        answers[question_id] = selected
                    
                    st.divider()

            # 提交按钮
            submitted = st.form_submit_button("提交所有答案", type="primary")

            if submitted:
                # 保存答案
                success_count = 0
                for q_id, answer in answers.items():
                    if redis_manager.save_user_answer(st.session_state.user_id, q_id, answer):
                        success_count += 1
                
                if success_count == len(answers):
                    st.success("答案提交成功！")
                    
                    # 计算得分
                    scores = scoring_engine.calculate_user_scores(st.session_state.user_id)
                    
                    # 定义需要全局重算的评分规则
                    recalculation_rules = {
                        ScoringRule.REAL_TIME_RANK.value,
                        ScoringRule.DISTANCE_SCORE.value,
                        ScoringRule.MAJORITY_VOTE.value,
                        ScoringRule.COUNT_RANK.value,
                        ScoringRule.DYNAMIC_YN.value
                    }

                    # 对于需要重算的题目，重新计算所有人的分数
                    needs_recalculation = any(
                        QUESTIONS.get(q_id, {}).get("rule") in recalculation_rules 
                        for q_id in answers
                    )

                    if needs_recalculation:
                        with st.spinner("正在重新计算所有用户得分..."):
                            scoring_engine.recalculate_all_scores()
                    
                    st.balloons()
                else:
                    st.error("部分答案保存失败，请重试")
    
    elif page == "查看成绩":
        st.title("我的坐标")

        final_x, final_y = scoring_engine.get_final_axes_scores(st.session_state.user_id)
        avg_x, avg_y = scoring_engine.get_average_axes_scores()
        
        st.markdown("---")
        
        # 显示信息页
        st.header("信息页")
        user_info = redis_manager.get_user_answers(st.session_state.user_id)
        st.write(f"**称呼 (q1):** {user_info.get('q1', {}).get('answer', 'N/A')}")
        st.write(f"**性别 (q2):** {user_info.get('q2', {}).get('answer', 'N/A')}")
        st.write(f"**MBTI (p):** {user_info.get('p', {}).get('answer', 'N/A')}")
        
        st.markdown("---")
        
        # 显示坐标轴图
        st.header("坐标轴")

        fig = go.Figure()

        # 添加用户点
        fig.add_trace(go.Scatter(
            x=[final_x],
            y=[final_y],
            mode='markers+text',
            marker=dict(color='red', size=15, symbol='star'),
            text=[st.session_state.user_id],
            textposition="top center",
            name="我的位置"
        ))

        # 添加平均分点
        fig.add_trace(go.Scatter(
            x=[avg_x],
            y=[avg_y],
            mode='markers+text',
            marker=dict(color='blue', size=12, symbol='circle'),
            text=["大众平均分"],
            textposition="bottom center",
            name="大众平均分"
        ))

        # 设置坐标轴
        fig.update_layout(
            xaxis=dict(
                title_text="x: 客观维度, 实际重庆人",
                range=[-110, 110],
                zeroline=True, zerolinewidth=2, zerolinecolor='black'
            ),
            yaxis=dict(
                title_text="y: 主观维度, 精神重庆人",
                range=[-110, 110],
                zeroline=True, zerolinewidth=2, zerolinecolor='black'
            ),
            width=800,
            height=800,
            showlegend=False,
            title="'重庆人'身份坐标"
        )
        
        # 添加象限标签
        annotations = [
            dict(x=50, y=50, text="实际重庆人 & 精神重庆人", showarrow=False, font=dict(size=14)),
            dict(x=-50, y=50, text="非实际重庆人 & 精神重庆人", showarrow=False, font=dict(size=14)),
            dict(x=-50, y=-50, text="非实际重庆人 & 非精神重庆人", showarrow=False, font=dict(size=14)),
            dict(x=50, y=-50, text="实际重庆人 & 非精神重庆人", showarrow=False, font=dict(size=14))
        ]
        fig.update_layout(annotations=annotations)

        st.plotly_chart(fig, use_container_width=True)
    
    elif page == "排行榜":
        st.title("用户排行榜")
        st.info("排行榜功能已在新版计分系统中禁用。")
    
    elif page == "问题统计":
        st.title("问题统计")
        
        selected_question_id = st.selectbox(
            "请选择要查看的题目",
            options=list(QUESTIONS.keys()),
            format_func=lambda q_id: f"{q_id}: {QUESTIONS[q_id]['label']}"
        )
        
        if selected_question_id:
            st.markdown("---")
            
            question_config = QUESTIONS[selected_question_id]
            stats = redis_manager.get_question_stats(selected_question_id)
            total_respondents = redis_manager.get_question_respondent_count(selected_question_id)
            
            st.subheader(f"“{question_config['label']}”答案分布")

            if total_respondents == 0:
                st.info("该题目暂无回答记录")
            else:
                if question_config['type'] in [QuestionType.SINGLE_CHOICE.value, QuestionType.COMBINATION.value]:
                    
                    vote_counts = {}
                    if question_config['type'] == QuestionType.SINGLE_CHOICE.value:
                        for option in question_config['options']:
                            count = int(stats.get(f"option:{option}", 0))
                            vote_counts[option] = count
                    else: # Combination
                        for key, value in stats.items():
                            if key.startswith("combo:"):
                                combo = key.replace("combo:", "")
                                vote_counts[combo] = int(value)
                    
                    if not vote_counts:
                        st.info("该题目暂无回答记录")
                    else:
                        # 计算百分比
                        percentages = {option: (count / total_respondents) * 100 for option, count in vote_counts.items()}
                        
                        df = pd.DataFrame({
                            "选项": vote_counts.keys(),
                            "票数": vote_counts.values(),
                            "百分比(%)": [round(p, 2) for p in percentages.values()]
                        })
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # 绘制图表
                        chart_df = pd.DataFrame(percentages.values(), index=percentages.keys(), columns=['百分比'])
                        st.bar_chart(chart_df)

                else:
                    st.info("该题型暂不支持分布统计。")
    
    elif page == "管理工具":
        st.title("管理工具")
        st.warning("⚠️ 以下操作请谨慎使用")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("导出所有数据", type="secondary"):
                data = redis_manager.export_data()
                
                # 提供下载
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载数据",
                    data=json_str,
                    file_name=f"questionnaire_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("重算所有得分", type="secondary"):
                with st.spinner("正在重新计算..."):
                    scoring_engine.recalculate_all_scores()
                st.success("重算完成！")
        
        with col3:
            if st.button("清空所有数据", type="secondary"):
                if st.checkbox("我确认要清空所有数据"):
                    redis_manager.clear_all_data()
                    st.success("数据已清空！")
                    st.experimental_rerun()

# 添加一些样式
st.markdown("""
<style>
    .stRadio > label {
        font-weight: bold;
    }
    .stNumberInput > label {
        font-weight: bold;
    }
    .stTextInput > label {
        font-weight: bold;
    }
    .stMultiSelect > label {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True) 