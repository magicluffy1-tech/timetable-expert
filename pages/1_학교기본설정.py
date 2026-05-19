"""
pages/1_학교기본설정.py
시정표, 학년·반 구성, 교사 등록, 교과 시수, 자유학기제 설정
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import get_data, save_session_data, generate_teacher_id, get_all_classes, get_periods_for_day

st.set_page_config(page_title="학교기본설정 | 시간표 전문가", page_icon="⚙️", layout="wide")

# ── 공통 CSS 주입 ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
.page-header {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(245,87,108,0.35);
}
.page-header h2 { color: white; font-size: 1.8rem; font-weight: 900; margin: 0 0 6px 0; }
.page-header p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.9rem; }
.card {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px;
    padding: 24px; margin-bottom: 16px;
}
.card-title { font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.9);
    border-left: 4px solid #f5576c; padding-left: 10px; margin-bottom: 16px; }
.stButton > button {
    background: linear-gradient(135deg, #f093fb, #f5576c);
    color: white; border: none; border-radius: 10px; font-weight: 600;
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>⚙️ 학교기본설정</h2>
    <p>학교 시정표, 학년·학급 구성, 교사 등록, 교과별 주간 시수, 자유학기제를 설정합니다.</p>
</div>
""", unsafe_allow_html=True)

data = get_data()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏫 학교 정보", "⏰ 시정표", "👩‍🏫 교사 등록", "📚 교과 시수", "🌟 자유학기제"]
)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: 학교 정보
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="card-title">📌 기본 정보</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        school_name = st.text_input("학교명", value=data["school_info"].get("name", "○○중학교"))
        semester = st.text_input("학기 (예: 2025-1)", value=data["school_info"].get("semester", "2025-1"))
    with col2:
        days_options = ["월", "화", "수", "목", "금"]
        selected_days = st.multiselect(
            "수업 요일",
            days_options,
            default=data["school_info"].get("days", days_options)
        )
        st.markdown("**요일별 교시 수 설정**")
        by_day = data["school_info"].setdefault("periods_per_day_by_day", {"월": 7, "화": 7, "수": 7, "목": 7, "금": 7})
        new_by_day = {}
        cols_day = st.columns(len(selected_days) if selected_days else 1)
        for di, day in enumerate(selected_days):
            with cols_day[di]:
                default_p = by_day.get(day, data["school_info"].get("periods_per_day", 7))
                new_by_day[day] = st.number_input(
                    f"{day}요일", min_value=4, max_value=9, value=int(default_p), key=f"p_day_{day}"
                )

    st.markdown('<div class="card-title" style="margin-top:20px;">🏫 학년·학급 구성</div>', unsafe_allow_html=True)
    for grade in ["1학년", "2학년", "3학년"]:
        cols = st.columns([2, 3])
        with cols[0]:
            n_classes = st.number_input(
                f"{grade} 학급 수",
                min_value=0, max_value=10,
                value=len(data["grades"].get(grade, {}).get("classes", ["1반", "2반", "3반"])),
                key=f"n_classes_{grade}"
            )
        with cols[1]:
            class_list = [f"{i}반" for i in range(1, n_classes + 1)]
            st.text_input(f"{grade} 학급 목록 (자동)", value=", ".join(class_list), disabled=True, key=f"cls_list_{grade}")

    if st.button("✅ 학교 정보 저장", key="save_school_info"):
        data["school_info"]["name"] = school_name
        data["school_info"]["semester"] = semester
        data["school_info"]["days"] = selected_days
        data["school_info"]["periods_per_day_by_day"] = new_by_day
        # 호환용 싱글값은 최대값으로 세팅
        data["school_info"]["periods_per_day"] = max(new_by_day.values()) if new_by_day else 7
        for grade in ["1학년", "2학년", "3학년"]:
            n = st.session_state.get(f"n_classes_{grade}", 3)
            data["grades"][grade] = {"classes": [f"{i}반" for i in range(1, n + 1)]}
        save_session_data()
        st.success("학교 정보가 저장되었습니다!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: 시정표
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="card-title">⏰ 교시별 시작·종료 시간</div>', unsafe_allow_html=True)
    period_times = data["school_info"].get("period_times", {})
    by_day = data["school_info"].get("periods_per_day_by_day", {})
    periods_n = max(by_day.values()) if by_day else data["school_info"].get("periods_per_day", 7)

    new_times = {}
    for p in range(1, periods_n + 1):
        pkey = str(p)
        default_start = period_times.get(pkey, {}).get("start", "08:50")
        default_end   = period_times.get(pkey, {}).get("end", "09:35")
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            st.markdown(f"**{p}교시**")
        with c2:
            start = st.text_input(f"시작", value=default_start, key=f"start_{p}", placeholder="HH:MM")
        with c3:
            end = st.text_input(f"종료", value=default_end, key=f"end_{p}", placeholder="HH:MM")
        new_times[pkey] = {"start": start, "end": end}

    if st.button("✅ 시정표 저장", key="save_timetimes"):
        data["school_info"]["period_times"] = new_times
        save_session_data()
        st.success("시정표가 저장되었습니다!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: 교사 등록
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="card-title">➕ 새 교사 등록</div>', unsafe_allow_html=True)

    DEFAULT_SUBJECTS = [
        "국어", "수학", "영어", "사회", "역사", "과학",
        "체육", "음악", "미술", "기술가정", "도덕",
        "자유학기", "창체", "정보"
    ]

    with st.form("add_teacher_form"):
        c1, c2 = st.columns(2)
        with c1:
            t_name = st.text_input("교사 이름 *")
            t_subjects = st.multiselect("담당 교과 *", DEFAULT_SUBJECTS)
        with c2:
            t_grades = st.multiselect("담당 학년 *", ["1학년", "2학년", "3학년"])
            t_visiting = st.checkbox("순회(겸임) 교사")
        submitted = st.form_submit_button("교사 등록", use_container_width=True)
        if submitted:
            if not t_name or not t_subjects or not t_grades:
                st.error("이름, 담당 교과, 담당 학년은 필수입니다.")
            else:
                new_tid = generate_teacher_id(data)
                data["teachers"].append({
                    "id": new_tid,
                    "name": t_name,
                    "subjects": t_subjects,
                    "grades": t_grades,
                    "is_visiting": t_visiting,
                    "blocked_slots": [],
                    "fixed_slots": [],
                })
                save_session_data()
                st.success(f"✅ {t_name} 선생님이 등록되었습니다. (ID: {new_tid})")
                st.rerun()

    st.markdown('<div class="card-title" style="margin-top:20px;">📋 등록된 교사 목록</div>', unsafe_allow_html=True)
    teachers = data.get("teachers", [])
    if not teachers:
        st.info("등록된 교사가 없습니다. 위 폼에서 교사를 등록해 주세요.")
    else:
        import pandas as pd
        teacher_df = pd.DataFrame([{
            "ID": t["id"],
            "이름": t["name"],
            "담당 교과": ", ".join(t.get("subjects", [])),
            "담당 학년": ", ".join(t.get("grades", [])),
            "순회교사": "✅" if t.get("is_visiting") else "",
        } for t in teachers])
        st.dataframe(teacher_df, use_container_width=True, hide_index=True)

        # 교사 삭제
        with st.expander("교사 삭제"):
            del_options = {f"{t['name']} ({t['id']})": t["id"] for t in teachers}
            del_sel = st.selectbox("삭제할 교사 선택", list(del_options.keys()), key="del_teacher_sel")
            if st.button("🗑️ 선택 교사 삭제", key="del_teacher_btn"):
                tid_to_del = del_options[del_sel]
                data["teachers"] = [t for t in data["teachers"] if t["id"] != tid_to_del]
                save_session_data()
                st.success("삭제되었습니다.")
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4: 교과 시수
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="card-title">📚 학년별 교과 주간 시수 설정</div>', unsafe_allow_html=True)
    st.info("주간 시수는 해당 학년 모든 학급에 동일하게 적용됩니다.")

    ALL_SUBJECTS = [
        "국어", "수학", "영어", "사회", "역사", "과학",
        "체육", "음악", "미술", "기술가정", "도덕", "정보", "창체"
    ]

    grade_tabs = st.tabs(["1학년", "2학년", "3학년"])
    for gi, grade in enumerate(["1학년", "2학년", "3학년"]):
        with grade_tabs[gi]:
            grade_curr = data["curriculum"].get(grade, {})
            new_curr = {}
            cols = st.columns(4)
            for si, subj in enumerate(ALL_SUBJECTS):
                with cols[si % 4]:
                    val = grade_curr.get(subj, 0)
                    new_val = st.number_input(
                        f"{subj}", min_value=0, max_value=10,
                        value=val, key=f"curr_{grade}_{subj}"
                    )
                    new_curr[subj] = new_val

            total = sum(new_curr.values())
            from utils.data_manager import get_periods_for_day
            total_avail = sum(get_periods_for_day(data, d) for d in data["school_info"].get("days", ["월","화","수","목","금"]))
            color = "green" if total <= total_avail else "red"
            st.markdown(f"**총 주간 시수:** :{color}[{total}시간] / 가용 슬롯: {total_avail}시간")

            if st.button(f"✅ {grade} 시수 저장", key=f"save_curr_{grade}"):
                data["curriculum"][grade] = new_curr
                save_session_data()
                st.success(f"{grade} 교과 시수가 저장되었습니다!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 5: 자유학기제
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="card-title">🌟 자유학기(년)제 설정</div>', unsafe_allow_html=True)
    free_sem = data.get("free_semester", {})

    enabled = st.checkbox("자유학기(년)제 운영", value=free_sem.get("enabled", False))
    if enabled:
        col1, col2 = st.columns(2)
        with col1:
            target_grade = st.selectbox(
                "운영 학년",
                ["1학년", "2학년", "3학년"],
                index=["1학년", "2학년", "3학년"].index(free_sem.get("target_grade", "1학년"))
            )
            free_type = st.radio(
                "운영 방식",
                ["자유학기제 (1학기)", "자유학기제 (2학기)", "자유학년제 (1년 전체)"],
                index=0
            )
        with col2:
            programs_raw = st.text_area(
                "주제선택 프로그램 목록 (줄 바꿈으로 구분)",
                value="\n".join(free_sem.get("programs", [])),
                height=150,
                placeholder="예:\n코딩과 미래직업\n생태탐구\n연극과 표현\n스포츠 리그"
            )

        st.markdown("**주간 자유학기 활동 시수 배분**")
        c1, c2, c3 = st.columns(3)
        with c1:
            hrs_theme = st.number_input("주제선택활동 시수/주", 0, 10, free_sem.get("hrs_theme", 4))
        with c2:
            hrs_career = st.number_input("진로탐색활동 시수/주", 0, 10, free_sem.get("hrs_career", 2))
        with c3:
            hrs_arts = st.number_input("예술체육활동 시수/주", 0, 10, free_sem.get("hrs_arts", 2))

        if st.button("✅ 자유학기제 설정 저장", key="save_free_sem"):
            data["free_semester"] = {
                "enabled": True,
                "target_grade": target_grade,
                "free_type": free_type,
                "programs": [p.strip() for p in programs_raw.strip().split("\n") if p.strip()],
                "hrs_theme": hrs_theme,
                "hrs_career": hrs_career,
                "hrs_arts": hrs_arts,
            }
            save_session_data()
            st.success("자유학기제 설정이 저장되었습니다!")
    else:
        if st.button("✅ 저장 (자유학기제 미운영)", key="save_free_sem_off"):
            data["free_semester"] = {"enabled": False}
            save_session_data()
            st.success("설정이 저장되었습니다.")
