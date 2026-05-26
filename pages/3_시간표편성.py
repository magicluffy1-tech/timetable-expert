"""
pages/3_시간표편성.py
AI 자동편성 + 품질 지표 + 학급별 시간표 그리드 + 수동 보정
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import (
    get_data, save_session_data, get_all_classes,
    get_subject_color, get_teacher_by_id, SUBJECT_COLORS,
    get_periods_for_day
)
from utils.constraints import validate_timetable, calculate_quality_score
from utils.scheduler import (
    generate_timetable, generate_multiple_drafts,
    assignments_to_timetable_dict, get_teacher_timetable
)

st.set_page_config(page_title="시간표편성 | 시간표 전문가", page_icon="🤖", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
.page-header {
    background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(161,140,209,0.4);
}
.page-header h2 { color: white; font-size: 1.8rem; font-weight: 900; margin: 0 0 6px 0; }
.page-header p  { color: rgba(255,255,255,0.8); margin: 0; }

/* 시간표 그리드 */
.tt-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.tt-table th {
    background: rgba(161,140,209,0.3); color: white; font-size: 0.82rem;
    font-weight: 700; padding: 8px 4px; border: 1px solid rgba(255,255,255,0.15); text-align: center;
}
.tt-table td {
    border: 1px solid rgba(255,255,255,0.1); padding: 5px 4px;
    text-align: center; font-size: 0.8rem; min-width: 70px;
    vertical-align: middle; height: 44px;
}
.tt-cell {
    border-radius: 6px; padding: 4px 6px; font-weight: 600;
    font-size: 0.78rem; line-height: 1.3; color: #1a1a2e;
}
.tt-period-col {
    background: rgba(161,140,209,0.15); color: rgba(255,255,255,0.7);
    font-weight: 700; font-size: 0.78rem;
}
.tt-teacher-name { font-size: 0.68rem; color: rgba(0,0,0,0.55); font-weight: 400; }

/* 품질 게이지 */
.quality-bar-wrap { background: rgba(255,255,255,0.1); border-radius: 20px; height: 12px; margin-top: 4px; }
.quality-bar-fill { border-radius: 20px; height: 12px; transition: width 0.5s; }

/* 카드 */
.card {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 20px;
}
.card-title {
    font-size: 0.95rem; font-weight: 700; color: rgba(255,255,255,0.9);
    border-left: 4px solid #a18cd1; padding-left: 10px; margin-bottom: 14px;
}
.stButton > button {
    background: linear-gradient(135deg, #a18cd1, #fbc2eb);
    color: #1a1a2e; border: none; border-radius: 10px; font-weight: 700;
    font-family: 'Noto Sans KR', sans-serif;
}
.draft-card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px; padding: 16px; text-align: center; cursor: pointer;
    transition: all 0.2s;
}
.draft-card:hover { background: rgba(161,140,209,0.15); border-color: #a18cd1; }
.draft-score { font-size: 2rem; font-weight: 900; color: #fbc2eb; }
.draft-label { color: rgba(255,255,255,0.6); font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>🤖 시간표 자동 편성</h2>
    <p>AI 기반 자동 편성 및 품질 지표를 확인하고 수동 보정을 할 수 있습니다.</p>
</div>
""", unsafe_allow_html=True)

data = get_data()
all_classes = get_all_classes(data)
days = data["school_info"].get("days", ["월","화","수","목","금"])
periods_n = data["school_info"].get("periods_per_day", 7)
teachers = data.get("teachers", [])

# ── 데이터 검증 ───────────────────────────────────────────────────────────────
if not all_classes:
    st.warning("학급 정보가 없습니다. 학교기본설정에서 학급을 먼저 구성하세요.")
    st.stop()

if not teachers:
    st.warning("등록된 교사가 없습니다. 학교기본설정에서 교사를 먼저 등록하세요.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["🤖 자동 편성", "📊 시간표 보기", "✏️ 수동 보정"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: 자동 편성
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown('<div class="card-title">⚙️ 편성 옵션</div>', unsafe_allow_html=True)
        n_drafts = st.slider("생성할 초안 수", 1, 5, 3)
        st.markdown("**균형화 옵션**")
        opt_max_daily = st.checkbox("하루 동일 과목 최대 2시간 제한", value=True)
        opt_spread_1st = st.checkbox("1·5교시 기피과목 분산", value=True)

        st.markdown("---")
        st.markdown('<div class="card-title">📋 현재 편성 현황</div>', unsafe_allow_html=True)
        timetable = data.get("timetable", {})
        filled = sum(
            1
            for cls in all_classes
            for d in days
            for p in range(1, get_periods_for_day(data, d) + 1)
            if timetable.get(cls, {}).get(d, {}).get(str(p), {}).get("subject", "")
        )
        total = sum(get_periods_for_day(data, d) for d in days) * len(all_classes)
        pct = int(filled / total * 100) if total else 0
        color = "#28a745" if pct >= 90 else ("#ffc107" if pct >= 50 else "#dc3545")
        st.markdown(f"편성률: **<span style='color:{color};'>{pct}%</span>** ({filled}/{total})", unsafe_allow_html=True)

        bar_color = "#28a745" if pct >= 90 else ("#ffc107" if pct >= 50 else "#dc3545")
        st.markdown(f"""
        <div class="quality-bar-wrap">
            <div class="quality-bar-fill" style="width:{pct}%;background:{bar_color};"></div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card-title">🚀 자동 편성 실행</div>', unsafe_allow_html=True)
        st.markdown("""
        자동 편성 알고리즘이 다음 제약조건을 자동으로 처리합니다:
        - ✅ 교사 중복 배정 0%
        - ✅ 특별실 동시 사용 방지
        - ✅ 순회교사 고정 시간 우선 반영
        - ✅ 블록타임(연속 수업) 자동 배정
        - ✅ 주간 교과 시수 충족
        """)

        if st.button("🚀 시간표 자동 편성 시작", use_container_width=True, type="primary"):
            if not data.get("curriculum"):
                st.error("교과 시수가 설정되지 않았습니다. 학교기본설정에서 먼저 설정하세요.")
            else:
                with st.spinner(f"⏳ {n_drafts}개의 시간표 초안을 생성 중입니다..."):
                    drafts = generate_multiple_drafts(data, n=n_drafts)
                    st.session_state["drafts"] = drafts
                    st.session_state["selected_draft"] = 0

                st.success(f"✅ {n_drafts}개의 초안이 생성되었습니다! 아래에서 선택하세요.")

        # 초안 선택 UI
        if "drafts" in st.session_state:
            drafts = st.session_state["drafts"]
            st.markdown("---")
            st.markdown("**📋 초안 선택** — 품질 점수가 높을수록 균형 잡힌 시간표입니다.")

            draft_cols = st.columns(len(drafts))
            for i, (score, assignments, stats) in enumerate(drafts):
                with draft_cols[i]:
                    q = stats["quality"]
                    is_selected = st.session_state.get("selected_draft") == i
                    border = "border: 2px solid #fbc2eb;" if is_selected else ""
                    st.markdown(f"""
                    <div class="draft-card" style="{border}">
                        <div class="draft-score">{score}</div>
                        <div class="draft-label">초안 {i+1}</div>
                        <div style="font-size:0.75rem;color:rgba(255,255,255,0.5);margin-top:6px;">
                            배정 과목: {stats['total_assigned']}개<br>
                            균형도: {q['balance_score']}<br>
                            아침 적합도: {q['morning_score']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"선택 {'✅' if is_selected else ''}", key=f"select_draft_{i}", use_container_width=True):
                        st.session_state["selected_draft"] = i

            # 선택된 초안 적용
            sel_idx = st.session_state.get("selected_draft", 0)
            _, sel_assignments, sel_stats = drafts[sel_idx]

            st.markdown("---")
            col_q1, col_q2, col_q3 = st.columns(3)
            q = sel_stats["quality"]
            with col_q1:
                st.metric("🏆 종합 품질 점수", f"{q['score']} / 100")
            with col_q2:
                st.metric("⚖️ 과목 균형도", f"{q['balance_score']} / 100")
            with col_q3:
                st.metric("🌅 시간 배치 적합도", f"{q['morning_score']} / 100")

            if q.get("detail"):
                st.markdown(f"<span style='color:rgba(255,255,255,0.55);font-size:0.8rem;'>{q['detail']}</span>", unsafe_allow_html=True)

            # 제약조건 검증
            errors = validate_timetable(data, sel_assignments)
            if errors:
                with st.expander(f"⚠️ 제약 위반 {len(errors)}건 (클릭하여 확인)"):
                    for e in errors:
                        st.markdown(e)
            else:
                st.success("✅ 모든 제약조건을 충족합니다!")

            st.markdown("---")
            if st.button("✨ AI 시간표 진단 및 조언 받기", use_container_width=True):
                from utils.ai_assistant import diagnose_timetable
                with st.spinner("Gemini AI가 시간표를 꼼꼼히 분석하고 있습니다... (약 10~20초 소요)"):
                    report = diagnose_timetable(data, sel_assignments, sel_stats)
                st.markdown("### 🤖 AI 진단 리포트")
                st.info(report)

            if st.button("✅ 선택한 초안을 시간표로 확정", use_container_width=True):
                data["timetable"] = assignments_to_timetable_dict(sel_assignments, data)
                save_session_data()
                st.success("시간표가 확정·저장되었습니다! '시간표 보기' 탭에서 확인하세요.")
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: 시간표 보기
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    view_type = st.radio("보기 유형", ["학급별 시간표", "교사별 시간표"], horizontal=True)

    if view_type == "학급별 시간표":
        sel_class = st.selectbox("학급 선택", all_classes, key="view_class_sel")
        tt = data.get("timetable", {})
        class_tt = tt.get(sel_class, {})

        # 시간표 HTML 렌더링
        html = f"""
        <table class="tt-table">
        <thead><tr>
            <th style="width:55px;">교시</th>
        """
        for d in days:
            html += f"<th>{d}</th>"
        html += "</tr></thead><tbody>"

        period_times = data["school_info"].get("period_times", {})
        max_periods = max(get_periods_for_day(data, d) for d in days) if days else 7
        for p in range(1, max_periods + 1):
            pt = period_times.get(str(p), {})
            time_str = f"<br><span style='font-size:0.65rem;color:rgba(255,255,255,0.4);'>{pt.get('start','')}</span>"
            html += f"<tr><td class='tt-period-col'>{p}교시{time_str}</td>"
            for d in days:
                periods_for_day = get_periods_for_day(data, d)
                if p > periods_for_day:
                    html += "<td><span style='color:rgba(255,255,255,0.15);font-size:0.75rem;'>-</span></td>"
                    continue
                cell = class_tt.get(d, {}).get(str(p), {})
                subj = cell.get("subject", "")
                tid = cell.get("teacher_id", "")
                teacher = get_teacher_by_id(data, tid)
                t_name = teacher.get("name", "") if teacher else ""

                color = get_subject_color(subj)
                is_block = cell.get("is_block", False)
                block_indicator = " 🔗" if is_block else ""

                if subj:
                    html += f"""
                    <td>
                        <div class="tt-cell" style="background:{color};">
                            {subj}{block_indicator}
                            <div class="tt-teacher-name">{t_name}</div>
                        </div>
                    </td>"""
                else:
                    html += "<td></td>"
            html += "</tr>"

        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

        # 과목별 배색 범례
        st.markdown("---")
        st.markdown("**과목 색상 범례**")
        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-top:6px;'>"
        for subj, color in SUBJECT_COLORS.items():
            if subj:
                legend_html += f"""
                <div style='background:{color};border-radius:6px;padding:4px 10px;
                    font-size:0.75rem;font-weight:600;color:#1a1a2e;'>{subj}</div>"""
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

    else:  # 교사별 시간표
        teacher_options = {f"{t['name']} ({t['id']})": t["id"] for t in teachers}
        sel_t_label = st.selectbox("교사 선택", list(teacher_options.keys()), key="view_teacher_sel")
        sel_tid = teacher_options[sel_t_label]

        # 현재 확정 시간표에서 Assignment 재구성
        assignments = []
        from utils.constraints import Assignment
        for cls, cls_tt in data.get("timetable", {}).items():
            for d, day_tt in cls_tt.items():
                for p_str, cell in day_tt.items():
                    if cell.get("subject"):
                        assignments.append(Assignment(
                            class_name=cls, day=d, period=int(p_str),
                            subject=cell["subject"], teacher_id=cell.get("teacher_id",""),
                            special_room=cell.get("special_room"), is_block=cell.get("is_block",False)
                        ))

        teacher_tt = get_teacher_timetable(assignments, sel_tid, data)

        html = "<table class='tt-table'><thead><tr><th>교시</th>"
        for d in days:
            html += f"<th>{d}</th>"
        html += "</tr></thead><tbody>"

        max_periods = max(get_periods_for_day(data, d) for d in days) if days else 7
        for p in range(1, max_periods + 1):
            html += f"<tr><td class='tt-period-col'>{p}교시</td>"
            for d in days:
                periods_for_day = get_periods_for_day(data, d)
                if p > periods_for_day:
                    html += "<td><span style='color:rgba(255,255,255,0.15);font-size:0.75rem;'>-</span></td>"
                    continue
                cell = teacher_tt.get(d, {}).get(p)
                if cell:
                    color = get_subject_color(cell["subject"])
                    html += f"""
                    <td>
                        <div class="tt-cell" style="background:{color};">
                            {cell['subject']}
                            <div class="tt-teacher-name">{cell['class_name']}</div>
                        </div>
                    </td>"""
                else:
                    html += "<td><span style='color:rgba(255,255,255,0.2);font-size:0.75rem;'>공강</span></td>"
            html += "</tr>"

        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

        # 담당 시간 수 요약
        t_assignments = [a for a in assignments if a.teacher_id == sel_tid]
        st.markdown(f"**주간 담당 시간: {len(t_assignments)}시간**")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: 수동 보정
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="card-title">✏️ 시간표 수동 보정</div>', unsafe_allow_html=True)
    st.info("확정된 시간표에서 특정 셀을 직접 수정할 수 있습니다. 저장 전에 충돌 여부가 자동으로 표시됩니다.")

    tt = data.get("timetable", {})
    if not any(tt.get(cls) for cls in all_classes):
        st.warning("편성된 시간표가 없습니다. 자동 편성 탭에서 먼저 시간표를 생성하세요.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            edit_class = st.selectbox("학급", all_classes, key="edit_class")
        with col2:
            edit_day = st.selectbox("요일", days, key="edit_day")
        with col3:
            periods_for_edit_day = get_periods_for_day(data, edit_day)
            edit_period = st.number_input("교시", 1, periods_for_edit_day, 1, key="edit_period")

        current_cell = tt.get(edit_class, {}).get(edit_day, {}).get(str(edit_period), {})
        current_subj = current_cell.get("subject", "")
        current_tid = current_cell.get("teacher_id", "")

        st.markdown(f"**현재 셀:** {edit_class} / {edit_day} / {edit_period}교시")
        if current_subj:
            t = get_teacher_by_id(data, current_tid)
            st.markdown(f"현재 배정: **{current_subj}** ({t.get('name','') if t else '교사 미배정'})")
        else:
            st.markdown("현재 배정: 없음")

        st.markdown("---")
        ALL_SUBJECTS = ["(비우기)","국어","수학","영어","사회","역사","과학","체육","음악","미술","기술가정","도덕","자유학기","창체","자습","정보"]
        new_subj = st.selectbox("새 과목", ALL_SUBJECTS, index=ALL_SUBJECTS.index(current_subj) if current_subj in ALL_SUBJECTS else 0, key="edit_subj")

        teacher_for_subj = [t for t in teachers if new_subj in t.get("subjects", [])] if new_subj != "(비우기)" else []
        t_options = {f"{t['name']} ({t['id']})": t["id"] for t in teacher_for_subj}
        t_options_list = ["(교사 미배정)"] + list(t_options.keys())
        new_t_label = st.selectbox("담당 교사", t_options_list, key="edit_teacher")
        new_tid = t_options.get(new_t_label, "") if new_t_label != "(교사 미배정)" else ""

        # 충돌 검사
        if new_tid and new_subj != "(비우기)":
            conflict = False
            for cls2, cls_tt in tt.items():
                if cls2 == edit_class:
                    continue
                cell2 = cls_tt.get(edit_day, {}).get(str(edit_period), {})
                if cell2.get("teacher_id") == new_tid:
                    st.error(f"⛔ 충돌! {new_t_label.split('(')[0].strip()} 선생님은 해당 시간에 {cls2}에 배정되어 있습니다.")
                    conflict = True
                    break
            if not conflict:
                st.success("✅ 충돌 없음")

        edit_mode = st.radio("수정 방식 선택", ["단순 강제 수정", "스마트 재배정 (연쇄 이동)"], horizontal=True)

        if edit_mode == "단순 강제 수정":
            st.caption("선택한 셀만 강제로 변경합니다. 충돌이 발생해도 무시하고 덮어씁니다.")
            if st.button("💾 단순 수정 저장", key="save_manual_edit"):
                from utils.data_manager import set_timetable_cell
                if new_subj == "(비우기)":
                    set_timetable_cell(data, edit_class, edit_day, edit_period, {"subject": "", "teacher_id": "", "special_room": "", "is_block": False})
                else:
                    set_timetable_cell(data, edit_class, edit_day, edit_period, {
                        "subject": new_subj,
                        "teacher_id": new_tid,
                        "special_room": current_cell.get("special_room", ""),
                        "is_block": current_cell.get("is_block", False),
                    })
                save_session_data()
                st.success("수정 사항이 저장되었습니다!")
                st.rerun()
        else:
            st.caption(
                "선택한 과목을 이 시간에 배정하고, 충돌이 발생하면 **기존 수업을 빈 슬롯으로 국소적으로 이동**합니다. "
                "다른 학급이나 교사의 시간표는 건드리지 않아 '나비효과'를 방지합니다."
            )
            if st.button("🚀 스마트 재배정 실행", key="save_smart_edit", type="primary"):
                if new_subj == "(비우기)":
                    st.error("스마트 재배정은 빈칸(비우기)으로는 실행할 수 없습니다.")
                elif not new_tid:
                    st.error("담당 교사가 배정되지 않아 스마트 재배정을 실행할 수 없습니다.")
                else:
                    with st.spinner("Local Swap 알고리즘으로 최소 범위 재조정 중..."):
                        from utils.local_swap import local_swap_reschedule
                        timetable = data.get("timetable", {})
                        ok, msg, new_tt = local_swap_reschedule(
                            timetable=timetable,
                            data=data,
                            class_name=edit_class,
                            target_day=edit_day,
                            target_period=edit_period,
                            new_subject=new_subj,
                            new_teacher_id=new_tid,
                        )
                    if ok:
                        data["timetable"] = new_tt
                        save_session_data()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

