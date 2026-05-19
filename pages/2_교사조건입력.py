"""
pages/2_교사조건입력.py
교사별 배정금지시간, 특별실 요청, 블록타임, 순회교사 고정 시간 설정
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import get_data, save_session_data, get_periods_for_day

st.set_page_config(page_title="교사조건입력 | 시간표 전문가", page_icon="👩‍🏫", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
.page-header {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(79,172,254,0.35);
}
.page-header h2 { color: white; font-size: 1.8rem; font-weight: 900; margin: 0 0 6px 0; }
.page-header p  { color: rgba(255,255,255,0.8); margin: 0; }
.card {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 24px; margin-bottom: 16px;
}
.card-title {
    font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.9);
    border-left: 4px solid #4facfe; padding-left: 10px; margin-bottom: 16px;
}
.slot-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.slot-btn {
    padding: 5px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
    border: 2px solid rgba(255,255,255,0.2); color: white; background: rgba(255,255,255,0.08);
    transition: all 0.15s;
}
.slot-btn.blocked { background: rgba(220,53,69,0.4); border-color: #dc3545; }
.slot-btn.fixed   { background: rgba(40,167,69,0.4); border-color: #28a745; }
.stButton > button {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: #0f0c29; border: none; border-radius: 10px; font-weight: 700;
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>👩‍🏫 교사 조건 입력</h2>
    <p>배정 금지 시간, 특별실 사용 요청, 블록타임, 순회교사 고정 시간을 설정합니다.</p>
</div>
""", unsafe_allow_html=True)

data = get_data()
teachers = data.get("teachers", [])

if not teachers:
    st.warning("등록된 교사가 없습니다. [학교기본설정] 페이지에서 먼저 교사를 등록해 주세요.")
    st.stop()

days = data["school_info"].get("days", ["월","화","수","목","금"])
periods_n = data["school_info"].get("periods_per_day", 7)

tab1, tab2, tab3, tab4 = st.tabs(["🚫 배정금지 / 필수배정", "🏫 특별실 배정", "⏱ 블록타임", "🔒 순회교사 고정시간"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: 배정금지 / 필수배정 시간
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="card-title">🚫 교사별 배정 금지 및 필수 배정 시간 설정</div>', unsafe_allow_html=True)
    st.info("각 교사별로 수업을 절대 배정하면 안 되는 '금지 시간(🔴)'과, 수업을 반드시 배치해야 하는 '필수 배정 시간(🟢)'을 마우스 클릭으로 간편하게 조율하세요.")

    teacher_options = {f"{t['name']} ({t['id']})": t["id"] for t in teachers}
    sel_teacher_label = st.selectbox("교사 선택", list(teacher_options.keys()), key="blocked_teacher_sel")
    sel_tid = teacher_options[sel_teacher_label]
    teacher_obj = next((t for t in teachers if t["id"] == sel_tid), None)

    if teacher_obj:
        # 배정 금지 슬롯 집합
        blocked_set = {
            (s["day"], int(s["period"]))
            for s in teacher_obj.setdefault("blocked_slots", [])
        }
        # 필수 배정 슬롯 집합
        required_set = {
            (s["day"], int(s["period"]))
            for s in teacher_obj.setdefault("required_slots", [])
        }

        st.markdown("**시간표 클릭으로 배정 조건 설정 (⚪ 가능 ➡️ 🔴 금지 ➡️ 🟢 필수 ➡️ ⚪ 가능 순환)**")

        # 시간표 그리드 표시
        header_cols = st.columns([1] + [2] * len(days))
        header_cols[0].markdown("**교시**")
        for i, d in enumerate(days):
            header_cols[i + 1].markdown(f"**{d}요일**")

        new_blocked = set(blocked_set)
        new_required = set(required_set)
        max_periods = max(get_periods_for_day(data, d) for d in days) if days else 7

        for p in range(1, max_periods + 1):
            row_cols = st.columns([1] + [2] * len(days))
            row_cols[0].markdown(f"**{p}교시**")
            for i, d in enumerate(days):
                periods_for_day = get_periods_for_day(data, d)
                if p > periods_for_day:
                    row_cols[i + 1].markdown("<div style='text-align:center;color:rgba(255,255,255,0.15);font-size:0.8rem;padding-top:4px;'>-</div>", unsafe_allow_html=True)
                    continue

                is_blocked = (d, p) in blocked_set
                is_required = (d, p) in required_set

                if is_blocked:
                    btn_label = "🔴 금지"
                    btn_type = "primary"
                elif is_required:
                    btn_label = "🟢 필수"
                    btn_type = "primary"
                else:
                    btn_label = "⚪ 가능"
                    btn_type = "secondary"

                if row_cols[i + 1].button(
                    btn_label,
                    key=f"blocked_{sel_tid}_{d}_{p}",
                    use_container_width=True,
                    type=btn_type
                ):
                    # 순환 로직
                    if (d, p) not in blocked_set and (d, p) not in required_set:
                        # ⚪ 가능 -> 🔴 금지
                        new_blocked.add((d, p))
                    elif (d, p) in blocked_set:
                        # 🔴 금지 -> 🟢 필수
                        new_blocked.discard((d, p))
                        new_required.add((d, p))
                    else:
                        # 🟢 필수 -> ⚪ 가능
                        new_required.discard((d, p))

                    teacher_obj["blocked_slots"] = [
                        {"day": day, "period": period}
                        for (day, period) in new_blocked
                    ]
                    teacher_obj["required_slots"] = [
                        {"day": day, "period": period}
                        for (day, period) in new_required
                    ]
                    save_session_data()
                    st.rerun()

        st.markdown(f"**현재 설정 요약:** 🔴 배정 금지 시간 {len(teacher_obj['blocked_slots'])}개 / 🟢 필수 배정 시간 {len(teacher_obj['required_slots'])}개")
        
        c1, c2 = st.columns(2)
        with c1:
            if teacher_obj.get("blocked_slots"):
                slots_text = ", ".join([
                    f"{s['day']}{s['period']}교시"
                    for s in sorted(teacher_obj["blocked_slots"], key=lambda x: (x["day"], x["period"]))
                ])
                st.markdown(f"**🔴 배정 금지:** <span style='color:#ff6b6b;'>{slots_text}</span>", unsafe_allow_html=True)
        with c2:
            if teacher_obj.get("required_slots"):
                slots_text = ", ".join([
                    f"{s['day']}{s['period']}교시"
                    for s in sorted(teacher_obj["required_slots"], key=lambda x: (x["day"], x["period"]))
                ])
                st.markdown(f"**🟢 필수 배정:** <span style='color:#4ecd7a;'>{slots_text}</span>", unsafe_allow_html=True)

        if st.button("🔄 조건 전체 초기화 (배정금지/필수배정 모두)", key=f"clear_blocked_{sel_tid}", use_container_width=True):
            teacher_obj["blocked_slots"] = []
            teacher_obj["required_slots"] = []
            save_session_data()
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: 특별실 배정
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="card-title">🏫 특별실 사용 요청 설정</div>', unsafe_allow_html=True)
    st.info("특별실은 자동 편성 시 중복 배정을 방지합니다. 특별실이 필요한 과목을 교과별로 연결하세요.")

    special_rooms = data.get("special_rooms", [])

    # 특별실 목록 표시 및 과목 연결
    st.markdown("**등록된 특별실 및 연결 과목**")
    for sr in special_rooms:
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            st.markdown(f"🏫 **{sr['name']}**")
        with c2:
            all_subjs = ["국어","수학","영어","사회","역사","과학","체육","음악","미술","기술가정","도덕","정보","자유학기"]
            linked = st.multiselect(
                "연결 과목",
                all_subjs,
                default=sr.get("subjects", []),
                key=f"sr_subjects_{sr['id']}"
            )
        with c3:
            if st.button("저장", key=f"save_sr_{sr['id']}"):
                sr["subjects"] = linked
                save_session_data()
                st.success("저장!")

    # 새 특별실 추가
    st.markdown("---")
    st.markdown("**새 특별실 추가**")
    with st.form("add_room_form"):
        new_room_name = st.text_input("특별실 이름 (예: 과학실2, 시청각실)")
        new_room_subjs = st.multiselect("연결 과목", all_subjs)
        if st.form_submit_button("특별실 추가"):
            if new_room_name:
                new_id = f"SR{len(special_rooms)+1:03d}"
                data["special_rooms"].append({
                    "id": new_id,
                    "name": new_room_name,
                    "subjects": new_room_subjs,
                })
                save_session_data()
                st.success(f"'{new_room_name}' 특별실이 추가되었습니다.")
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: 블록타임
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="card-title">⏱ 블록타임(연속 수업) 설정</div>', unsafe_allow_html=True)
    st.info("2교시 이상 연속으로 진행되어야 하는 수업을 설정합니다. (과학실험, 미술, 자유학기 주제선택 등)")

    block_times = data.get("block_times", [])

    # 현재 블록타임 목록
    if block_times:
        import pandas as pd
        bt_df = pd.DataFrame(block_times)
        bt_df.columns = ["학급", "과목", "연속교시수"]
        st.dataframe(bt_df, use_container_width=True, hide_index=True)
    else:
        st.info("설정된 블록타임이 없습니다.")

    st.markdown("**블록타임 추가**")
    from utils.data_manager import get_all_classes
    all_classes = get_all_classes(data)
    if not all_classes:
        st.warning("학급이 없습니다. 학교기본설정에서 학급을 먼저 구성하세요.")
    else:
        with st.form("add_blocktime_form"):
            bt_cols = st.columns(3)
            with bt_cols[0]:
                bt_class = st.selectbox("학급", all_classes)
            with bt_cols[1]:
                bt_subj = st.selectbox("과목", ["과학","미술","기술가정","자유학기","체육","음악","정보"])
            with bt_cols[2]:
                bt_n = st.number_input("연속 교시 수", min_value=2, max_value=4, value=2)
            if st.form_submit_button("블록타임 추가"):
                # 중복 제거
                exists = any(
                    bt["class_name"] == bt_class and bt["subject"] == bt_subj
                    for bt in block_times
                )
                if exists:
                    st.warning("이미 동일한 블록타임이 설정되어 있습니다.")
                else:
                    data["block_times"].append({
                        "class_name": bt_class,
                        "subject": bt_subj,
                        "n_consecutive": bt_n,
                    })
                    save_session_data()
                    st.success("블록타임이 추가되었습니다!")
                    st.rerun()

    # 블록타임 삭제
    if block_times:
        st.markdown("**블록타임 삭제**")
        bt_options = [f"{bt['class_name']} | {bt['subject']} ({bt['n_consecutive']}연속)" for bt in block_times]
        bt_del = st.selectbox("삭제할 블록타임", bt_options, key="del_bt_sel")
        if st.button("🗑️ 삭제", key="del_bt_btn"):
            idx = bt_options.index(bt_del)
            data["block_times"].pop(idx)
            save_session_data()
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4: 순회교사 고정 시간
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="card-title">🔒 순회(겸임) 교사 고정 시간 설정</div>', unsafe_allow_html=True)
    st.info("순회교사의 타교 근무 시간을 고정하면, 자동 편성 시 해당 시간에 수업이 배정되지 않습니다.")

    visiting_teachers = [t for t in teachers if t.get("is_visiting")]
    if not visiting_teachers:
        st.warning("등록된 순회교사가 없습니다. 학교기본설정에서 '순회교사' 체크 후 교사를 등록하세요.")
    else:
        vt_options = {f"{t['name']} ({t['id']})": t["id"] for t in visiting_teachers}
        sel_vt_label = st.selectbox("순회교사 선택", list(vt_options.keys()), key="vt_sel")
        sel_vt_id = vt_options[sel_vt_label]
        vt_obj = next((t for t in teachers if t["id"] == sel_vt_id), None)

        if vt_obj:
            fixed_slots = vt_obj.get("fixed_slots", [])

            st.markdown("**고정 시간 추가 (타교 근무)**")
            with st.form("add_fixed_slot"):
                all_classes_with_other = ["(타교 수업)"] + get_all_classes(data)
                fc1, fc2, fc3, fc4 = st.columns(4)
                with fc1:
                    fs_day = st.selectbox("요일", days)
                with fc2:
                    fs_period = st.number_input("교시", min_value=1, max_value=periods_n, value=1)
                with fc3:
                    fs_class = st.selectbox("학급", all_classes_with_other)
                with fc4:
                    fs_subj = st.text_input("과목", placeholder="예: 수학")
                if st.form_submit_button("고정 시간 추가"):
                    max_p_for_day = get_periods_for_day(data, fs_day)
                    if fs_period > max_p_for_day:
                        st.error(f"⛔ {fs_day}요일은 최대 {max_p_for_day}교시까지만 운영됩니다.")
                    else:
                        fixed_slots.append({
                            "day": fs_day,
                            "period": int(fs_period),
                            "class_name": fs_class if fs_class != "(타교 수업)" else "",
                            "subject": fs_subj,
                            "is_other_school": fs_class == "(타교 수업)",
                        })
                        vt_obj["fixed_slots"] = fixed_slots
                        # 타교 수업 시간은 배정금지에도 추가
                        if fs_class == "(타교 수업)":
                            blocked = vt_obj.get("blocked_slots", [])
                            blocked.append({"day": fs_day, "period": int(fs_period)})
                            vt_obj["blocked_slots"] = blocked
                        save_session_data()
                        st.success("고정 시간이 추가되었습니다!")
                        st.rerun()

            if fixed_slots:
                import pandas as pd
                fs_df = pd.DataFrame([{
                    "요일": fs["day"],
                    "교시": f"{fs['period']}교시",
                    "학급": fs.get("class_name") or "(타교)",
                    "과목": fs.get("subject", ""),
                    "구분": "🔒 타교 근무" if fs.get("is_other_school") else "📌 고정 배정",
                } for fs in fixed_slots])
                st.dataframe(fs_df, use_container_width=True, hide_index=True)

                if st.button("🔄 고정 시간 전체 초기화", key=f"clear_fixed_{sel_vt_id}"):
                    vt_obj["fixed_slots"] = []
                    save_session_data()
                    st.rerun()
