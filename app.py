"""
app.py — 중학교 시간표 전문가 통합 솔루션 메인 대시보드
"""
import streamlit as st
from datetime import date, datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.data_manager import get_data, save_session_data, get_all_classes, SUBJECT_COLORS, get_periods_for_day

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="중학교 시간표 전문가",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 전역 CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 배경 그라디언트 */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

/* 메인 헤더 */
.hero-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 40px 48px;
    margin-bottom: 32px;
    box-shadow: 0 20px 60px rgba(102,126,234,0.4);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.hero-header h1 {
    font-size: 2.6rem;
    font-weight: 900;
    color: white;
    margin: 0 0 8px 0;
    line-height: 1.2;
}
.hero-header p {
    color: rgba(255,255,255,0.85);
    font-size: 1.05rem;
    margin: 0;
}
.hero-badge {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    color: white;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 16px;
    letter-spacing: 1px;
}

/* 상태 카드 */
.stat-card {
    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
}
.stat-icon { font-size: 2.4rem; margin-bottom: 8px; }
.stat-value {
    font-size: 2.2rem;
    font-weight: 900;
    color: white;
    line-height: 1;
}
.stat-label {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.6);
    margin-top: 6px;
    font-weight: 500;
    letter-spacing: 0.5px;
}

/* 섹션 헤더 */
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
    border-left: 4px solid #667eea;
    padding-left: 12px;
    margin: 32px 0 16px 0;
}

/* 메뉴 카드 */
.menu-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 22px 20px;
    transition: all 0.25s;
    cursor: pointer;
    height: 100%;
}
.menu-card:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(102,126,234,0.6);
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(102,126,234,0.25);
}
.menu-card .menu-icon { font-size: 2rem; margin-bottom: 10px; }
.menu-card .menu-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: white;
    margin-bottom: 6px;
}
.menu-card .menu-desc {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.55);
    line-height: 1.5;
}

/* 결보강 뱃지 */
.sub-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
}
.sub-pending { background: rgba(255,193,7,0.2); color: #ffc107; border: 1px solid rgba(255,193,7,0.4); }
.sub-done    { background: rgba(40,167,69,0.2);  color: #28a745; border: 1px solid rgba(40,167,69,0.4); }

/* 사이드바 */
.sidebar-title {
    font-size: 1.3rem;
    font-weight: 900;
    color: white;
    margin-bottom: 4px;
}
section[data-testid="stSidebar"] {
    background: rgba(15,12,41,0.85) !important;
    border-right: 1px solid rgba(255,255,255,0.1);
}

/* Streamlit 기본 요소 오버라이드 */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-family: 'Noto Sans KR', sans-serif;
    transition: opacity 0.2s, transform 0.15s;
}
.stButton > button:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.alert-info {
    background: rgba(102,126,234,0.15);
    border: 1px solid rgba(102,126,234,0.4);
    border-radius: 10px;
    padding: 14px 18px;
    color: rgba(255,255,255,0.9);
    font-size: 0.9rem;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)


# ── 데이터 로드 ───────────────────────────────────────────────────────────────
data = get_data()
school = data["school_info"]
today = date.today()
today_str = today.strftime("%Y년 %m월 %d일")
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-title">📅 시간표 전문가</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin-bottom:24px;">
        중학교 맞춤형 통합 솔루션
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**{school.get('name','○○중학교')}**")
    st.markdown(f"`{school.get('semester','2025-1')}학기`")
    st.markdown("---")

    st.markdown("### 🗂 메뉴")
    st.page_link("app.py",                         label="🏠 대시보드",       help="메인 현황판")
    st.page_link("pages/6_구글시트연동.py",         label="🟢 구글시트연동",   help="온라인 공동 취합 및 동기화")
    st.page_link("pages/1_학교기본설정.py",         label="⚙️ 학교기본설정",   help="시정표·교사·교과 설정")
    st.page_link("pages/2_교사조건입력.py",         label="👩‍🏫 교사조건입력",   help="배정금지·블록타임·특별실")
    st.page_link("pages/3_시간표편성.py",           label="🤖 시간표편성",     help="AI 자동편성 및 수동보정")
    st.page_link("pages/4_결보강관리.py",           label="🔄 결보강관리",     help="결강·보강·교환 처리")
    st.page_link("pages/5_시간표출력.py",           label="🖨️ 시간표출력",     help="학급·교사별 출력 및 엑셀")

    st.markdown("---")
    st.markdown("### 🤖 AI 어시스턴트 설정")
    api_key = st.text_input("Gemini API Key", value=st.session_state.get("gemini_api_key", data.get("api_key", "")), type="password", help="시간표 AI 진단 기능을 사용하려면 Google Gemini API 키를 입력하세요.")
    if st.button("🔑 API 키 저장", use_container_width=True):
        st.session_state.gemini_api_key = api_key
        data["api_key"] = api_key
        save_session_data()
        st.success("API 키 저장 완료!")

    st.markdown("---")
    if st.button("💾 데이터 저장", use_container_width=True):
        if save_session_data():
            st.success("저장 완료!")
        else:
            st.error("저장 실패")

# ── 히어로 헤더 ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-header">
    <div class="hero-badge">🏫 MIDDLE SCHOOL SCHEDULER PRO</div>
    <h1>📅 시간표 전문가</h1>
    <p>중학교 맞춤형 통합 시간표 편성 솔루션 &nbsp;|&nbsp; {today_str}({weekday_kr}) &nbsp;|&nbsp; {school.get('name','○○중학교')} {school.get('semester','2025-1')}학기</p>
</div>
""", unsafe_allow_html=True)

# ── 현황 통계 카드 ────────────────────────────────────────────────────────────
teachers = data.get("teachers", [])
all_classes = get_all_classes(data)
timetable = data.get("timetable", {})

# 시간표 편성 완료율 계산
days = school.get("days", ["월","화","수","목","금"])
total_slots = sum(get_periods_for_day(data, d) for d in days) * len(all_classes)
filled_slots = sum(
    1
    for cls in all_classes
    for d in days
    for p in range(1, get_periods_for_day(data, d) + 1)
    if timetable.get(cls, {}).get(d, {}).get(str(p), {}).get("subject", "")
)
completion_pct = int(filled_slots / total_slots * 100) if total_slots else 0

# 오늘 결보강 현황
today_subs = [
    s for s in data.get("substitutions", [])
    if s.get("date") == today.isoformat()
]
pending_subs = [s for s in today_subs if s.get("status") == "pending"]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">👩‍🏫</div>
        <div class="stat-value">{len(teachers)}</div>
        <div class="stat-label">등록 교사</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">🏫</div>
        <div class="stat-value">{len(all_classes)}</div>
        <div class="stat-label">전체 학급</div>
    </div>""", unsafe_allow_html=True)
with c3:
    color = "#28a745" if completion_pct >= 90 else ("#ffc107" if completion_pct >= 50 else "#dc3545")
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value" style="color:{color};">{completion_pct}%</div>
        <div class="stat-label">시간표 편성률</div>
    </div>""", unsafe_allow_html=True)
with c4:
    alert_color = "#dc3545" if pending_subs else "#28a745"
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">🔄</div>
        <div class="stat-value" style="color:{alert_color};">{len(pending_subs)}</div>
        <div class="stat-label">오늘 미처리 결보강</div>
    </div>""", unsafe_allow_html=True)

# ── 빠른 접근 메뉴 ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">⚡ 빠른 메뉴</div>', unsafe_allow_html=True)

menus = [
    ("🟢", "구글시트연동", "공유 시트를 통해 기초자료, 교과시수, 블록타임을 간편하게 일괄 동기화", "pages/6_구글시트연동.py"),
    ("⚙️", "학교기본설정", "시정표, 학년·반 구성, 교사 등록, 교과 시수, 자유학기제 설정", "pages/1_학교기본설정.py"),
    ("👩‍🏫", "교사조건입력", "배정 금지 시간, 특별실 요청, 블록타임, 순회교사 고정 시간", "pages/2_교사조건입력.py"),
    ("🤖", "시간표 자동편성", "AI 기반 자동 편성 + 드래그앤드롭 수동 보정 + 품질 지표", "pages/3_시간표편성.py"),
    ("🖨️", "시간표 출력", "학급별·교사별 시간표 출력 및 엑셀·HTML 내보내기", "pages/5_시간표출력.py"),
]

cols = st.columns(5)
for i, (icon, title, desc, link) in enumerate(menus):
    with cols[i]:
        st.markdown(f"""
        <div class="menu-card">
            <div class="menu-icon">{icon}</div>
            <div class="menu-title">{title}</div>
            <div class="menu-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        st.page_link(link, label=f"→ 바로가기", use_container_width=True)

# ── 오늘의 결보강 현황 ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🔄 오늘의 결보강 현황</div>', unsafe_allow_html=True)

if not today_subs:
    st.markdown(f"""
    <div class="alert-info">
        ✅ {today_str}({weekday_kr}) — 결보강 신청 없음. 정상 수업입니다.
    </div>
    """, unsafe_allow_html=True)
else:
    sub_df_rows = []
    for s in today_subs:
        status_badge = (
            '<span class="sub-badge sub-pending">처리 대기</span>'
            if s.get("status") == "pending"
            else '<span class="sub-badge sub-done">처리 완료</span>'
        )
        sub_df_rows.append({
            "학급": s.get("class_name", ""),
            "교시": f"{s.get('period','')}교시",
            "과목": s.get("subject", ""),
            "결강 교사": s.get("absent_teacher_name", ""),
            "대체 교사": s.get("sub_teacher_name", "-"),
            "상태": s.get("status", ""),
        })
    import pandas as pd
    st.dataframe(pd.DataFrame(sub_df_rows), use_container_width=True, hide_index=True)

# ── 학교 정보 요약 ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 학교 정보 요약</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**학급 구성**")
    grades_info = []
    for grade, ginfo in data.get("grades", {}).items():
        classes = ginfo.get("classes", [])
        grades_info.append({"학년": grade, "학급 수": len(classes), "학급 목록": ", ".join(classes)})
    if grades_info:
        import pandas as pd
        st.dataframe(pd.DataFrame(grades_info), use_container_width=True, hide_index=True)

with col_b:
    st.markdown("**교과별 주간 시수 (1학년 기준)**")
    curr_1 = data.get("curriculum", {}).get("1학년", {})
    if curr_1:
        import pandas as pd
        curr_df = pd.DataFrame([
            {"과목": subj, "주간 시수": hrs, "색상": SUBJECT_COLORS.get(subj, "#BDC3C7")}
            for subj, hrs in curr_1.items() if hrs > 0
        ])
        st.dataframe(
            curr_df[["과목", "주간 시수"]],
            use_container_width=True,
            hide_index=True,
        )

# ── 자유학기제 현황 ────────────────────────────────────────────────────────────
free_sem = data.get("free_semester", {})
if free_sem.get("enabled"):
    st.markdown('<div class="section-header">🌟 자유학기제 운영 현황</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="alert-info">
        🌟 <strong>자유학기제 운영 중</strong> — 대상: <strong>{free_sem.get('target_grade','')}</strong><br>
        프로그램: {', '.join(free_sem.get('programs', [])) or '(미설정)'}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:rgba(255,255,255,0.3);font-size:0.75rem;'>"
    "중학교 시간표 전문가 통합 솔루션 | Powered by Streamlit"
    "</div>",
    unsafe_allow_html=True
)
