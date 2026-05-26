"""
pages/7_학기시수점검.py
특정 기준일을 기준으로 교과별 이수 시수 vs 기준 시수 비교 및 과부족 예측 페이지

주요 기능:
  - 학기 시작/종료일, 기준일 설정
  - 공휴일·행사·요일변경 예외 일정 등록
  - 현재 시간표 기반으로 완료/잔여/예상 시수 자동 산출
  - 과부족 시수를 학급별·교과별로 색상 표로 시각화
"""
import streamlit as st
import pandas as pd
import sys, os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import (
    get_data, save_session_data, get_all_classes,
    get_subject_color, SUBJECT_COLORS,
)

# ─── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="학기시수점검 | 시간표 전문가", page_icon="📊", layout="wide")

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
.page-header p  { color: rgba(0,0,0,0.65); margin: 0; font-size: 0.9rem; }
.section-title {
    font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.95);
    border-left: 4px solid #ffd200; padding-left: 10px; margin: 20px 0 12px 0;
}
.stat-card {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px; padding: 16px 20px; text-align: center; margin-bottom: 8px;
}
.stat-card .label { font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-bottom: 4px; }
.stat-card .value { font-size: 1.6rem; font-weight: 900; color: #ffd200; }
.stat-card .sub   { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
.calendar-badge {
    display: inline-block; border-radius: 6px; padding: 2px 8px;
    font-size: 0.72rem; font-weight: 700; margin: 2px;
}
.badge-holiday { background: rgba(239,68,68,0.25); color: #fca5a5; border: 1px solid rgba(239,68,68,0.4); }
.badge-event   { background: rgba(59,130,246,0.25); color: #93c5fd; border: 1px solid rgba(59,130,246,0.4); }
.badge-change  { background: rgba(168,85,247,0.25); color: #d8b4fe; border: 1px solid rgba(168,85,247,0.4); }
table.hours-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
table.hours-table th {
    background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.85);
    padding: 8px 10px; border: 1px solid rgba(255,255,255,0.12); text-align: center;
}
table.hours-table td {
    padding: 6px 10px; border: 1px solid rgba(255,255,255,0.08);
    text-align: center; color: rgba(255,255,255,0.9);
}
.cell-shortage { background: rgba(239,68,68,0.18); font-weight: 700; color: #fca5a5; }
.cell-surplus  { background: rgba(59,130,246,0.18); font-weight: 700; color: #93c5fd; }
.cell-ok       { background: rgba(34,197,94,0.12); color: #86efac; }
.stButton > button {
    background: linear-gradient(135deg, #f7971e, #ffd200);
    color: #1a1a2e; border: none; border-radius: 10px; font-weight: 700;
    font-family: 'Noto Sans KR', sans-serif;
}
.stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📊 학기 시수 점검</h2>
    <p>기준일 기준으로 교과별 이수 시수 · 잔여 예상 시수 · 과부족 시수를 자동 산출하여 학기말 결강/보강 계획을 지원합니다.</p>
</div>
""", unsafe_allow_html=True)

data = get_data()
timetable = data.get("timetable", {})
curriculum = data.get("curriculum", {})
school_info = data.get("school_info", {})
days_order = school_info.get("days", ["월", "화", "수", "목", "금"])
DAY_MAP = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# ──────────────────────────────────────────────────────────────────────
# 학사 일정 데이터 초기화 (session_state 기반으로 영구 보존)
# ──────────────────────────────────────────────────────────────────────
if "academic_calendar" not in st.session_state:
    saved_cal = data.get("academic_calendar", {})
    st.session_state.academic_calendar = {
        "start_date": saved_cal.get("start_date", "2025-03-02"),
        "end_date":   saved_cal.get("end_date",   "2025-07-18"),
        "std_weeks":  saved_cal.get("std_weeks",  17),
        "exceptions": saved_cal.get("exceptions", []),
    }

cal = st.session_state.academic_calendar

# ─── Tabs ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⚙️ 학사 일정 설정", "📅 요일별 수업 현황", "📋 교과별 시수 리포트"])

# ══════════════════════════════════════════════════════════════════════
# TAB 1: 학사 일정 설정
# ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">📆 학기 기본 일정</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        new_start = st.date_input(
            "학기 시작일",
            value=date.fromisoformat(cal["start_date"]),
            key="cal_start",
        )
    with c2:
        new_end = st.date_input(
            "학기 종료일",
            value=date.fromisoformat(cal["end_date"]),
            key="cal_end",
        )
    with c3:
        ref_date = st.date_input(
            "📌 기준일 (오늘 또는 진단 날짜)",
            value=date.today(),
            key="cal_ref",
        )
    with c4:
        new_weeks = st.number_input(
            "학기 기준 주수",
            min_value=1, max_value=52,
            value=cal["std_weeks"],
            step=1,
            help="교육과정상 이 학기의 기준 수업 주수 (보통 17주)",
        )

    # ─── 예외 일정 관리 ────────────────────────────────────────────────
    st.markdown('<div class="section-title">🗓️ 예외 일정 등록 (공휴일 · 행사 · 요일변경)</div>', unsafe_allow_html=True)
    st.caption(
        "수업이 없는 날(공휴일·재량휴업·행사)이나 "
        "요일 시간표를 다른 요일로 운영하는 날(예: 목요일에 금요일 시간표 운영)을 추가하세요."
    )

    # 🇰🇷 법정 공휴일 자동 불러오기
    if st.button("🇰🇷 우리나라 법정 공휴일 자동 불러오기 (학기 기간 반영)", key="load_kr_holidays", use_container_width=True):
        try:
            import holidays
            start_yr = new_start.year
            end_yr = new_end.year
            years = list(range(start_yr, end_yr + 1))
            kr_holidays = holidays.KR(years=years)
            
            added_count = 0
            existing_dates = {exc["date"] for exc in cal["exceptions"]}
            
            temp_exceptions = cal["exceptions"].copy()
            
            for h_date, h_name in sorted(kr_holidays.items()):
                if new_start <= h_date <= new_end:
                    date_str = h_date.isoformat()
                    if date_str not in existing_dates:
                        temp_exceptions.append({
                            "date": date_str,
                            "type": "holiday",
                            "memo": h_name,
                            "replace_with": "",
                        })
                        added_count += 1
            
            if added_count > 0:
                st.session_state.academic_calendar["exceptions"] = temp_exceptions
                st.success(f"✅ 총 {added_count}개의 법정 공휴일을 추가했습니다! 아래 '💾 학사 일정 저장' 버튼을 누르면 최종 저장됩니다.")
                st.rerun()
            else:
                st.info("ℹ️ 학기 기간 내에 새로 추가할 법정 공휴일이 없거나 이미 모두 등록되어 있습니다.")
        except Exception as e:
            st.error(f"❌ 공휴일을 불러오는 중 오류가 발생했습니다: {e}")

    exc_cols = st.columns([2, 2, 2, 2, 1])
    exc_cols[0].markdown("**날짜**")
    exc_cols[1].markdown("**유형**")
    exc_cols[2].markdown("**메모**")
    exc_cols[3].markdown("**대체 요일** (요일변경 시)")
    exc_cols[4].markdown("")

    exceptions = cal["exceptions"].copy()

    # 기존 예외 목록 표시
    to_delete = []
    for i, exc in enumerate(exceptions):
        ec1, ec2, ec3, ec4, ec5 = st.columns([2, 2, 2, 2, 1])
        exc_date = ec1.date_input(
            f"날짜_{i}", value=date.fromisoformat(exc["date"]),
            key=f"exc_date_{i}", label_visibility="collapsed",
        )
        exc_type = ec2.selectbox(
            f"유형_{i}",
            ["holiday", "event", "change"],
            index=["holiday", "event", "change"].index(exc.get("type", "holiday")),
            format_func=lambda x: {"holiday": "🔴 수업없음(공휴일/행사)", "event": "🔵 행사(수업단축)", "change": "🟣 요일변경"}[x],
            key=f"exc_type_{i}", label_visibility="collapsed",
        )
        exc_memo = ec3.text_input(
            f"메모_{i}", value=exc.get("memo", ""),
            key=f"exc_memo_{i}", label_visibility="collapsed",
        )
        exc_replace = ec4.selectbox(
            f"대체요일_{i}",
            ["(없음)", "월", "화", "수", "목", "금"],
            index=(["(없음)", "월", "화", "수", "목", "금"].index(exc.get("replace_with", "(없음)"))
                   if exc.get("replace_with", "(없음)") in ["(없음)", "월", "화", "수", "목", "금"] else 0),
            key=f"exc_replace_{i}", label_visibility="collapsed",
        )
        if ec5.button("🗑", key=f"del_exc_{i}"):
            to_delete.append(i)
        else:
            exceptions[i] = {
                "date": exc_date.isoformat(),
                "type": exc_type,
                "memo": exc_memo,
                "replace_with": exc_replace if exc_replace != "(없음)" else "",
            }

    for idx in sorted(to_delete, reverse=True):
        exceptions.pop(idx)

    if st.button("➕ 예외 일정 추가", key="add_exc"):
        exceptions.append({
            "date": date.today().isoformat(),
            "type": "holiday",
            "memo": "",
            "replace_with": "",
        })
        st.rerun()

    # ─── 저장 버튼 ────────────────────────────────────────────────────
    if st.button("💾 학사 일정 저장", key="save_cal", use_container_width=True):
        st.session_state.academic_calendar = {
            "start_date": new_start.isoformat(),
            "end_date":   new_end.isoformat(),
            "std_weeks":  int(new_weeks),
            "exceptions": exceptions,
        }
        data["academic_calendar"] = st.session_state.academic_calendar
        save_session_data()
        st.success("✅ 학사 일정이 저장되었습니다!")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# 핵심 계산 함수
# ══════════════════════════════════════════════════════════════════════
def _build_day_counts(start: date, end: date, ref: date, exceptions: list) -> tuple[dict, dict]:
    """
    start~end 사이에서 각 요일이 몇 번 수업일로 존재하는지 계산.
    ref 이전 → past_counts, ref 이후 → future_counts (ref 당일은 past에 포함)

    예외 처리:
      - holiday/event: 해당일을 수업일에서 제외
      - change: 해당일을 본래 요일 대신 replace_with 요일로 카운트
    """
    # 예외 딕셔너리 구성 {date_str: exc_info}
    exc_map = {exc["date"]: exc for exc in exceptions}

    past_counts   = {d: 0 for d in ["월", "화", "수", "목", "금"]}
    future_counts = {d: 0 for d in ["월", "화", "수", "목", "금"]}

    cur = start
    day_names = ["월", "화", "수", "목", "금", "토", "일"]

    while cur <= end:
        d_str = cur.isoformat()
        weekday = cur.weekday()  # 0=월
        natural_day = day_names[weekday] if weekday < 7 else None

        if d_str in exc_map:
            exc = exc_map[d_str]
            if exc["type"] in ("holiday", "event"):
                # 수업 없음 → 카운트하지 않음
                cur += timedelta(days=1)
                continue
            elif exc["type"] == "change" and exc.get("replace_with"):
                # 요일 변경: 해당 날을 replace_with 요일로 카운트
                effective_day = exc["replace_with"]
            else:
                effective_day = natural_day
        else:
            effective_day = natural_day

        if effective_day in past_counts:  # 평일만 카운트
            if cur <= ref:
                past_counts[effective_day] += 1
            else:
                future_counts[effective_day] += 1

        cur += timedelta(days=1)

    return past_counts, future_counts


def _compute_subject_hours(
    timetable: dict,
    class_name: str,
    days_order: list,
    past_counts: dict,
    future_counts: dict,
    curriculum: dict,
) -> dict:
    """
    특정 학급의 교과별 (완료 예상 시수, 잔여 예상 시수) 계산.
    반환: {subject: {"done": int, "remaining": int, "total": int}}
    """
    cls_tt = timetable.get(class_name, {})
    result = {}

    # 학급의 학년에 해당하는 교육과정 과목들로 초기화하여 누락 방지 (평균 계산 오류 수정)
    grade_key = class_name.split()[0] if class_name else ""
    grade_curr = curriculum.get(grade_key, {})
    for subj in grade_curr:
        result[subj] = {"done": 0, "remaining": 0, "total": 0}

    for day in days_order:
        day_tt = cls_tt.get(day, {})
        for period_str, cell in day_tt.items():
            subj = cell.get("subject", "")
            if not subj:
                continue
            if subj not in result:
                result[subj] = {"done": 0, "remaining": 0, "total": 0}
            result[subj]["done"]      += past_counts.get(day, 0)
            result[subj]["remaining"] += future_counts.get(day, 0)

    for subj in result:
        result[subj]["total"] = result[subj]["done"] + result[subj]["remaining"]

    return result


# ══════════════════════════════════════════════════════════════════════
# TAB 2: 요일별 수업 현황
# ══════════════════════════════════════════════════════════════════════
with tab2:
    cal_now = st.session_state.academic_calendar
    try:
        s_date = date.fromisoformat(cal_now["start_date"])
        e_date = date.fromisoformat(cal_now["end_date"])
        r_date = st.session_state.get("cal_ref", date.today())
        if isinstance(r_date, date):
            pass
        else:
            r_date = date.today()
    except Exception:
        s_date = date(2025, 3, 2)
        e_date = date(2025, 7, 18)
        r_date = date.today()

    # ref date 가져오기 (tab1의 date_input에서 고름)
    r_date = st.session_state.get("cal_ref", date.today())

    past_counts, future_counts = _build_day_counts(
        s_date, e_date, r_date, cal_now["exceptions"]
    )

    st.markdown('<div class="section-title">📊 요일별 수업 일수 현황</div>', unsafe_allow_html=True)
    st.caption(f"기준일: **{r_date}** | 학기: {s_date} ~ {e_date}")

    summary_cols = st.columns(5)
    for i, day in enumerate(["월", "화", "수", "목", "금"]):
        p = past_counts.get(day, 0)
        f = future_counts.get(day, 0)
        summary_cols[i].markdown(f"""
        <div class="stat-card">
            <div class="label">{day}요일</div>
            <div class="value">{p + f}회</div>
            <div class="sub">완료 {p}회 / 잔여 {f}회</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">🗓️ 등록된 예외 일정</div>', unsafe_allow_html=True)
    if not cal_now["exceptions"]:
        st.info("등록된 예외 일정이 없습니다. '학사 일정 설정' 탭에서 공휴일/행사일을 추가하세요.")
    else:
        type_map = {
            "holiday": ("🔴 수업없음", "badge-holiday"),
            "event":   ("🔵 행사(단축)", "badge-event"),
            "change":  ("🟣 요일변경", "badge-change"),
        }
        exc_sorted = sorted(cal_now["exceptions"], key=lambda x: x["date"])
        badge_html = ""
        for exc in exc_sorted:
            label, cls_ = type_map.get(exc["type"], ("?", ""))
            memo = exc.get("memo", "")
            repl = f" → {exc['replace_with']}요일 운영" if exc.get("replace_with") else ""
            badge_html += f'<span class="calendar-badge {cls_}">{exc["date"]} {label} {memo}{repl}</span> '
        st.markdown(badge_html, unsafe_allow_html=True)

    # 학기 전체 통계
    total_past   = sum(past_counts.values())
    total_future = sum(future_counts.values())
    st.markdown(f"""
    <div style="margin-top:16px; padding: 16px; background: rgba(255,210,0,0.08);
         border: 1px solid rgba(255,210,0,0.3); border-radius: 12px; color: rgba(255,255,255,0.85);">
    📌 <strong>학기 전체:</strong>
    총 수업일(교시) 기준 — 완료 <strong style="color:#ffd200">{total_past}</strong>일차 ·
    잔여 <strong style="color:#93c5fd">{total_future}</strong>일차 ·
    합계 <strong>{total_past + total_future}</strong>일차
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 3: 교과별 시수 리포트 (핵심)
# ══════════════════════════════════════════════════════════════════════
with tab3:
    cal_now = st.session_state.academic_calendar
    try:
        s_date = date.fromisoformat(cal_now["start_date"])
        e_date = date.fromisoformat(cal_now["end_date"])
    except Exception:
        s_date = date(2025, 3, 2)
        e_date = date(2025, 7, 18)

    r_date = st.session_state.get("cal_ref", date.today())
    std_weeks = cal_now.get("std_weeks", 17)

    past_counts, future_counts = _build_day_counts(
        s_date, e_date, r_date, cal_now["exceptions"]
    )

    st.markdown('<div class="section-title">⚙️ 보기 옵션</div>', unsafe_allow_html=True)
    opt_col1, opt_col2, opt_col3 = st.columns([2, 2, 2])

    all_classes = get_all_classes(data)
    grades_list = list(data.get("grades", {}).keys())

    view_mode = opt_col1.radio(
        "보기 단위",
        ["학급별", "학년별(전체 평균)"],
        horizontal=True,
        key="hrs_view_mode",
    )
    if view_mode == "학급별":
        selected_class = opt_col2.selectbox(
            "학급 선택", all_classes, key="hrs_class_sel"
        )
        target_classes = [selected_class]
        grade_key = selected_class.split()[0] if selected_class else grades_list[0]
    else:
        selected_grade = opt_col2.selectbox(
            "학년 선택", grades_list, key="hrs_grade_sel"
        )
        grade_classes = [
            f"{selected_grade} {c}"
            for c in data.get("grades", {}).get(selected_grade, {}).get("classes", [])
        ]
        target_classes = grade_classes
        grade_key = selected_grade

    grade_curr = curriculum.get(grade_key, {})
    std_weeks_used = opt_col3.number_input(
        "계산에 쓸 기준 주수 (덮어쓰기)",
        value=std_weeks, min_value=1, max_value=52, step=1,
        key="hrs_stdweeks",
        help="학사 일정 설정의 기준 주수를 여기서 임시로 바꿔볼 수 있습니다.",
    )

    if not target_classes:
        st.warning("시간표 데이터가 없습니다. 먼저 [시간표편성] 탭에서 자동 편성을 실행해 주세요.")
        st.stop()

    st.markdown(f"""
    <div style="margin-bottom:12px; font-size: 0.85rem; color: rgba(255,255,255,0.6);">
    📌 기준일: <strong style="color:#ffd200">{r_date}</strong> |
    학기: {s_date} ~ {e_date} |
    기준 주수: {std_weeks_used}주
    </div>
    """, unsafe_allow_html=True)

    # ─── 집계 ──────────────────────────────────────────────────────────
    # 각 교과별로 모든 target_classes 의 값을 평균(또는 대표값)
    agg: dict[str, dict] = {}

    for cls in target_classes:
        cls_hours = _compute_subject_hours(
            timetable, cls, days_order, past_counts, future_counts, curriculum
        )
        for subj, hrs in cls_hours.items():
            if subj not in agg:
                agg[subj] = {"done_list": [], "remaining_list": [], "total_list": []}
            agg[subj]["done_list"].append(hrs["done"])
            agg[subj]["remaining_list"].append(hrs["remaining"])
            agg[subj]["total_list"].append(hrs["total"])

    # 교육과정의 모든 과목을 반드시 표시 (실제 시간표에 없더라도)
    for subj in grade_curr:
        if subj not in agg:
            agg[subj] = {"done_list": [0], "remaining_list": [0], "total_list": [0]}

    # ─── 표 데이터 구성 ────────────────────────────────────────────────
    rows = []
    for subj, d in sorted(agg.items(), key=lambda x: -grade_curr.get(x[0], 0)):
        weekly_hrs = grade_curr.get(subj, 0)
        std_total  = weekly_hrs * std_weeks_used  # 기준 총 시수

        done_avg   = round(sum(d["done_list"]) / len(d["done_list"]), 1) if d["done_list"] else 0
        rem_avg    = round(sum(d["remaining_list"]) / len(d["remaining_list"]), 1) if d["remaining_list"] else 0
        total_avg  = done_avg + rem_avg
        shortage   = round(total_avg - std_total, 1)

        rows.append({
            "subject": subj,
            "weekly": weekly_hrs,
            "std_total": std_total,
            "done": done_avg,
            "remaining": rem_avg,
            "expected_total": total_avg,
            "shortage": shortage,
        })

    # ─── HTML 테이블 렌더링 ────────────────────────────────────────────
    st.markdown('<div class="section-title">📋 교과별 시수 현황표</div>', unsafe_allow_html=True)

    label_suffix = f" ({view_mode})" if view_mode == "학년별(전체 평균)" else ""
    
    # Markdown의 들여쓰기 코드블록 파싱 오작동을 완벽히 차단하기 위해 모든 들여쓰기를 제거한 리스트로 구성하여 조인합니다.
    html_lines = []
    html_lines.append('<table class="hours-table">')
    html_lines.append('<thead>')
    html_lines.append('<tr>')
    html_lines.append('<th>교과</th>')
    html_lines.append('<th>주당시수</th>')
    html_lines.append(f'<th>기준시수<br>({std_weeks_used}주)</th>')
    html_lines.append('<th>✅ 완료시수<br>(기준일까지)</th>')
    html_lines.append('<th>⏳ 잔여예상시수<br>(기준일 이후)</th>')
    html_lines.append('<th>📊 최종예상시수</th>')
    html_lines.append(f'<th>🔺 과부족 시수{label_suffix}</th>')
    html_lines.append('</tr>')
    html_lines.append('</thead>')
    html_lines.append('<tbody>')

    for row in rows:
        sh = row["shortage"]
        if sh < -0.4:
            cell_cls = "cell-shortage"
            sh_str = f"▼ {abs(sh):.1f}h 부족"
        elif sh > 0.4:
            cell_cls = "cell-surplus"
            sh_str = f"▲ {sh:.1f}h 초과"
        else:
            cell_cls = "cell-ok"
            sh_str = "✔ 충족"

        subj_color = SUBJECT_COLORS.get(row["subject"], "#cccccc")
        html_lines.append('<tr>')
        html_lines.append(f'<td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{subj_color};margin-right:6px;"></span>{row["subject"]}</td>')
        html_lines.append(f'<td>{row["weekly"]}h/주</td>')
        html_lines.append(f'<td><strong>{row["std_total"]}h</strong></td>')
        html_lines.append(f'<td>{row["done"]:.1f}h</td>')
        html_lines.append(f'<td>{row["remaining"]:.1f}h</td>')
        html_lines.append(f'<td><strong>{row["expected_total"]:.1f}h</strong></td>')
        html_lines.append(f'<td class="{cell_cls}"><strong>{sh_str}</strong></td>')
        html_lines.append('</tr>')

    html_lines.append('</tbody>')
    html_lines.append('</table>')

    html = "".join(html_lines)
    st.markdown(html, unsafe_allow_html=True)

    # ─── 요약 배너 ────────────────────────────────────────────────────
    shortage_subjs  = [(r["subject"], r["shortage"]) for r in rows if r["shortage"] < -0.4]
    surplus_subjs   = [(r["subject"], r["shortage"]) for r in rows if r["shortage"] > 0.4]

    st.markdown("---")
    sum_col1, sum_col2 = st.columns(2)
    with sum_col1:
        if shortage_subjs:
            st.error(
                f"**⚠️ 시수 부족 교과 ({len(shortage_subjs)}개)**\n\n"
                + "\n".join([f"- **{s}**: {abs(h):.1f}h 부족" for s, h in shortage_subjs])
            )
        else:
            st.success("✅ 시수 부족 교과가 없습니다.")

    with sum_col2:
        if surplus_subjs:
            st.info(
                f"**💡 시수 초과 교과 ({len(surplus_subjs)}개)**\n\n"
                + "\n".join([f"- **{s}**: {h:.1f}h 초과" for s, h in surplus_subjs])
            )
        else:
            st.info("💡 시수 초과 교과가 없습니다.")

    # ─── Excel 다운로드 ───────────────────────────────────────────────
    st.markdown('<div class="section-title">📥 결과 다운로드</div>', unsafe_allow_html=True)

    df_export = pd.DataFrame([{
        "교과":         r["subject"],
        "주당시수(h)":  r["weekly"],
        f"기준시수({std_weeks_used}주)": r["std_total"],
        "완료시수(h)":  r["done"],
        "잔여예상시수(h)": r["remaining"],
        "최종예상시수(h)": r["expected_total"],
        "과부족(h)":    r["shortage"],
        "판정":         "부족" if r["shortage"] < -0.4 else ("초과" if r["shortage"] > 0.4 else "충족"),
    } for r in rows])

    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="학기시수점검")
    buf.seek(0)

    st.download_button(
        label="📥 Excel로 내려받기",
        data=buf,
        file_name=f"시수점검_{grade_key}_{r_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.caption(
        "※ 완료·잔여 시수는 현재 시간표가 변경 없이 그대로 운영된다는 가정 하에 산출됩니다. "
        "결강·보강이 확정된 경우 [결보강관리] 탭에서 반영 후 다시 조회하세요."
    )
