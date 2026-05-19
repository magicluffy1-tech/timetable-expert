"""
pages/4_결보강관리.py
결강 등록, 대체 교사 추천, 수업 교환 승인, 결보강 이력
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import get_data, save_session_data, get_all_classes, get_teacher_by_id, get_periods_for_day
from utils.constraints import Assignment
from utils.scheduler import find_substitute_teachers

st.set_page_config(page_title="결보강관리 | 시간표 전문가", page_icon="🔄", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
.page-header {
    background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(247,151,30,0.4);
}
.page-header h2 { color: #1a1a2e; font-size: 1.8rem; font-weight: 900; margin: 0 0 6px 0; }
.page-header p  { color: rgba(0,0,0,0.6); margin: 0; }
.card {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 20px; margin-bottom: 12px;
}
.card-title {
    font-size: 0.95rem; font-weight: 700; color: rgba(255,255,255,0.9);
    border-left: 4px solid #ffd200; padding-left: 10px; margin-bottom: 14px;
}
.recommend-card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
    display: flex; align-items: center; justify-content: space-between;
}
.badge-same { background: rgba(40,167,69,0.25); color: #28a745;
    border: 1px solid rgba(40,167,69,0.4); border-radius: 10px; padding: 2px 10px; font-size: 0.72rem; font-weight: 700; }
.badge-alt  { background: rgba(255,193,7,0.25); color: #ffc107;
    border: 1px solid rgba(255,193,7,0.4); border-radius: 10px; padding: 2px 10px; font-size: 0.72rem; font-weight: 700; }
.stButton > button {
    background: linear-gradient(135deg, #f7971e, #ffd200);
    color: #1a1a2e; border: none; border-radius: 10px; font-weight: 700;
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>🔄 결보강 관리</h2>
    <p>결강 등록, 대체 교사 추천, 수업 교환 승인 및 이력 관리</p>
</div>
""", unsafe_allow_html=True)

data = get_data()
all_classes = get_all_classes(data)
teachers = data.get("teachers", [])
days = data["school_info"].get("days", ["월","화","수","목","금"])
periods_n = data["school_info"].get("periods_per_day", 7)

# 현재 시간표에서 Assignment 재구성 (대체교사 가용성 판단용)
current_assignments: list[Assignment] = []
for cls, cls_tt in data.get("timetable", {}).items():
    for d, day_tt in cls_tt.items():
        for p_str, cell in day_tt.items():
            if cell.get("subject"):
                current_assignments.append(Assignment(
                    class_name=cls, day=d, period=int(p_str),
                    subject=cell["subject"], teacher_id=cell.get("teacher_id",""),
                    special_room=cell.get("special_room"), is_block=cell.get("is_block",False)
                ))

tab1, tab2, tab3 = st.tabs(["📝 결강 등록 & 보강 배정", "🔀 수업 교환 신청", "📋 결보강 이력"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: 결강 등록 & 보강 배정
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="card-title">📝 결강 정보 입력</div>', unsafe_allow_html=True)

    with st.form("absence_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            abs_date = st.date_input("결강 날짜", value=date.today())
            abs_class = st.selectbox("결강 학급", all_classes if all_classes else ["(학급 없음)"])
        with c2:
            abs_day = st.selectbox("요일", days)
            abs_period = st.number_input("교시", 1, periods_n, 1)
        with c3:
            abs_teacher_opts = {f"{t['name']} ({t['id']})": t for t in teachers}
            abs_t_label = st.selectbox("결강 교사", list(abs_teacher_opts.keys()) if teachers else ["(교사 없음)"])
            abs_reason = st.selectbox("결강 사유", ["출장", "병가", "연수", "공가", "기타"])

        submitted = st.form_submit_button("결강 등록 및 대체교사 추천", use_container_width=True)

    if submitted and teachers and all_classes:
        max_p = get_periods_for_day(data, abs_day)
        if abs_period > max_p:
            st.error(f"⛔ {abs_day}요일은 최대 {max_p}교시까지만 운영됩니다. 교시를 확인해 주세요.")
        else:
            abs_teacher_obj = abs_teacher_opts[abs_t_label]
            abs_tid = abs_teacher_obj["id"]

            # 해당 셀의 과목 파악
            cell = data.get("timetable", {}).get(abs_class, {}).get(abs_day, {}).get(str(abs_period), {})
            abs_subj = cell.get("subject", "")
            grade = abs_class.split()[0]

        # 결강 정보 세션에 임시 저장
        st.session_state["pending_absence"] = {
            "date": abs_date.isoformat(),
            "day": abs_day,
            "period": int(abs_period),
            "class_name": abs_class,
            "subject": abs_subj,
            "grade": grade,
            "absent_teacher_id": abs_tid,
            "absent_teacher_name": abs_teacher_obj.get("name", ""),
            "reason": abs_reason,
            "status": "pending",
        }
        st.session_state["substitute_candidates"] = find_substitute_teachers(
            data, abs_tid, abs_day, int(abs_period), abs_subj, grade, current_assignments
        )

    # 대체 교사 추천 결과 표시
    if "pending_absence" in st.session_state and "substitute_candidates" in st.session_state:
        absence = st.session_state["pending_absence"]
        candidates = st.session_state["substitute_candidates"]

        st.markdown("---")
        st.markdown(f"""
        **📌 결강 정보**  
        {absence['class_name']} / {absence['day']} {absence['period']}교시 / 
        **{absence['subject'] or '(과목 미편성)'}** / 
        결강교사: **{absence['absent_teacher_name']}** / 사유: {absence['reason']}
        """)

        st.markdown('<div class="card-title">🤖 대체 교사 추천 목록</div>', unsafe_allow_html=True)

        if not candidates:
            st.warning("해당 시간에 배정 가능한 교사가 없습니다.")
        else:
            for i, cand in enumerate(candidates[:5]):  # 상위 5명
                badge = (
                    '<span class="badge-same">✅ 동일 교과</span>'
                    if cand["same_subject"]
                    else '<span class="badge-alt">🔄 타 교과</span>'
                )
                subjs_str = ", ".join(cand["subjects"][:3])

                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.markdown(f"""
                    <div class="recommend-card">
                        <div>
                            <strong style="color:white;">{cand['name']}</strong>
                            &nbsp;{badge}&nbsp;
                            <span style="color:rgba(255,255,255,0.5);font-size:0.8rem;">({subjs_str})</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_btn:
                    if st.button(f"배정", key=f"assign_sub_{i}", use_container_width=True):
                        new_sub = dict(absence)
                        new_sub["sub_teacher_id"] = cand["id"]
                        new_sub["sub_teacher_name"] = cand["name"]
                        new_sub["status"] = "done"
                        new_sub["id"] = f"SUB{len(data.get('substitutions',[]))+1:04d}"
                        new_sub["created_at"] = datetime.now().isoformat()
                        data.setdefault("substitutions", []).append(new_sub)
                        save_session_data()
                        del st.session_state["pending_absence"]
                        del st.session_state["substitute_candidates"]
                        st.success(f"✅ {cand['name']} 선생님이 보강 교사로 배정되었습니다!")
                        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: 수업 교환 신청
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="card-title">🔀 교사 간 수업 교환 신청</div>', unsafe_allow_html=True)
    st.info("두 교사의 서로 다른 수업 시간을 교환합니다. 충돌 여부를 자동으로 검증합니다.")

    with st.form("swap_form"):
        st.markdown("**교사 A의 수업**")
        cA1, cA2, cA3, cA4 = st.columns(4)
        t_options_list = [f"{t['name']} ({t['id']})" for t in teachers]
        with cA1: swap_t_a = st.selectbox("교사 A", t_options_list, key="swap_ta")
        with cA2: swap_day_a = st.selectbox("요일 A", days, key="swap_da")
        with cA3: swap_period_a = st.number_input("교시 A", 1, periods_n, 1, key="swap_pa")
        with cA4: swap_class_a = st.selectbox("학급 A", all_classes if all_classes else ["없음"], key="swap_ca")

        st.markdown("**교사 B의 수업**")
        cB1, cB2, cB3, cB4 = st.columns(4)
        with cB1: swap_t_b = st.selectbox("교사 B", t_options_list, key="swap_tb")
        with cB2: swap_day_b = st.selectbox("요일 B", days, key="swap_db")
        with cB3: swap_period_b = st.number_input("교시 B", 1, periods_n, 1, key="swap_pb")
        with cB4: swap_class_b = st.selectbox("학급 B", all_classes if all_classes else ["없음"], key="swap_cb")

        swap_submitted = st.form_submit_button("교환 검증 및 신청", use_container_width=True)

    if swap_submitted:
        ta_id = {f"{t['name']} ({t['id']})": t["id"] for t in teachers}.get(swap_t_a, "")
        tb_id = {f"{t['name']} ({t['id']})": t["id"] for t in teachers}.get(swap_t_b, "")

        max_pa = get_periods_for_day(data, swap_day_a)
        max_pb = get_periods_for_day(data, swap_day_b)

        if swap_period_a > max_pa:
            st.error(f"⛔ {swap_day_a}요일은 최대 {max_pa}교시까지만 운영됩니다. 교시 A를 확인해 주세요.")
        elif swap_period_b > max_pb:
            st.error(f"⛔ {swap_day_b}요일은 최대 {max_pb}교시까지만 운영됩니다. 교시 B를 확인해 주세요.")
        else:
            # 간단한 충돌 검사
            conflicts = []
            # 교사 A가 교사 B의 시간에 다른 반 수업이 있는지
            for a in current_assignments:
                if a.teacher_id == ta_id and a.day == swap_day_b and a.period == int(swap_period_b) and a.class_name != swap_class_a:
                    conflicts.append(f"{swap_t_a.split('(')[0]}는 {swap_day_b}{swap_period_b}교시에 {a.class_name} 수업이 있습니다.")
                if a.teacher_id == tb_id and a.day == swap_day_a and a.period == int(swap_period_a) and a.class_name != swap_class_b:
                    conflicts.append(f"{swap_t_b.split('(')[0]}는 {swap_day_a}{swap_period_a}교시에 {a.class_name} 수업이 있습니다.")

            if conflicts:
                for c in conflicts:
                    st.error(f"⛔ {c}")
            else:
                st.success("✅ 충돌 없음! 교환이 가능합니다.")
            if st.button("✅ 교환 확정", key="confirm_swap"):
                # 실제 시간표 교환
                tt = data.get("timetable", {})
                cell_a = tt.get(swap_class_a, {}).get(swap_day_a, {}).get(str(swap_period_a), {}).copy()
                cell_b = tt.get(swap_class_b, {}).get(swap_day_b, {}).get(str(swap_period_b), {}).copy()

                from utils.data_manager import set_timetable_cell
                set_timetable_cell(data, swap_class_a, swap_day_a, int(swap_period_a), cell_b)
                set_timetable_cell(data, swap_class_b, swap_day_b, int(swap_period_b), cell_a)

                # 교환 이력
                swap_record = {
                    "id": f"SWAP{len(data.get('substitutions',[]))+1:04d}",
                    "type": "swap",
                    "date": date.today().isoformat(),
                    "teacher_a": swap_t_a, "class_a": swap_class_a,
                    "day_a": swap_day_a, "period_a": int(swap_period_a),
                    "teacher_b": swap_t_b, "class_b": swap_class_b,
                    "day_b": swap_day_b, "period_b": int(swap_period_b),
                    "status": "done",
                    "created_at": datetime.now().isoformat(),
                }
                data.setdefault("substitutions", []).append(swap_record)
                save_session_data()
                st.success("교환이 확정·저장되었습니다!")
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: 결보강 이력
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="card-title">📋 결보강 전체 이력</div>', unsafe_allow_html=True)

    substitutions = data.get("substitutions", [])
    if not substitutions:
        st.info("결보강 이력이 없습니다.")
    else:
        # 날짜 필터
        filter_date = st.date_input("날짜 필터 (비워두면 전체)", value=None, key="sub_date_filter")

        rows = []
        for s in reversed(substitutions):
            if filter_date and s.get("date") != filter_date.isoformat():
                continue
            stype = "수업교환" if s.get("type") == "swap" else "결보강"
            rows.append({
                "날짜": s.get("date",""),
                "유형": stype,
                "학급": s.get("class_name", f"{s.get('class_a','')}↔{s.get('class_b','')}"),
                "교시": f"{s.get('period','')}교시" if s.get("period") else f"{s.get('day_a','')}{s.get('period_a','')}교시",
                "결강/교환 교사": s.get("absent_teacher_name", s.get("teacher_a","")),
                "보강/상대 교사": s.get("sub_teacher_name", s.get("teacher_b","")),
                "사유": s.get("reason",""),
                "상태": "✅ 완료" if s.get("status") == "done" else "⏳ 대기",
            })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("해당 날짜의 이력이 없습니다.")

        if st.button("🗑️ 전체 이력 삭제", key="clear_subs"):
            data["substitutions"] = []
            save_session_data()
            st.rerun()
