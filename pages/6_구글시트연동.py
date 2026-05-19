"""
pages/6_구글시트연동.py
구글 시트 온라인 취합 및 기초 데이터 동기화 페이지
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_manager import get_data, save_session_data, sync_all_from_google_sheet

st.set_page_config(page_title="구글시트연동 | 시간표 전문가", page_icon="🟢", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
.page-header {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 28px;
    box-shadow: 0 12px 40px rgba(56,239,125,0.35);
}
.page-header h2 { color: white; font-size: 1.8rem; font-weight: 900; margin: 0 0 6px 0; }
.page-header p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.9rem; }
.card {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px;
    padding: 24px; margin-bottom: 16px;
}
.card-title { font-size: 1rem; font-weight: 700; color: rgba(255,255,255,0.9);
    border-left: 4px solid #38ef7d; padding-left: 10px; margin-bottom: 16px; }
.stButton > button {
    background: linear-gradient(135deg, #11998e, #38ef7d);
    color: #0f0c29; border: none; border-radius: 10px; font-weight: 700;
    font-family: 'Noto Sans KR', sans-serif;
}
.guide-box {
    background: rgba(255,255,255,0.04);
    border: 1px dashed rgba(255,255,255,0.2);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
    color: rgba(255,255,255,0.8);
    font-size: 0.85rem;
    line-height: 1.6;
}
.guide-box strong { color: #38ef7d; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>🟢 구글 시트 온라인 동기화</h2>
    <p>공유된 구글 스프레드시트 링크를 통해 교사별 배정금지 시간, 교과 시수, 블록타임을 간편하게 일괄 동기화합니다.</p>
</div>
""", unsafe_allow_html=True)

data = get_data()

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown('<div class="card-title">🔗 구글 시트 링크 연동 및 동기화</div>', unsafe_allow_html=True)
    
    current_url = data.get("google_sheet_url", "")
    sheet_url = st.text_input(
        "구글 스프레드시트 URL 입력", 
        value=current_url, 
        placeholder="https://docs.google.com/spreadsheets/d/.../edit?usp=sharing",
        help="시트의 링크 공유 설정을 '링크가 있는 모든 사용자에게 공개 (뷰어)'로 설정한 뒤 URL을 입력하세요."
    )
    
    if st.button("🔄 구글 시트 데이터 가져오기", use_container_width=True):
        if not sheet_url:
            st.error("구글 스프레드시트 URL을 입력해 주세요.")
        else:
            with st.spinner("⏳ 구글 시트에서 탭별로 데이터를 내려받아 정밀 분석 및 동기화하는 중..."):
                # URL 저장
                data["google_sheet_url"] = sheet_url
                save_session_data()
                
                success, logs = sync_all_from_google_sheet(data, sheet_url)
                
                if success:
                    st.success("🎉 구글 시트 동기화 작업이 완료되었습니다!")
                    # 로그 요약 표시
                    st.markdown("### 📋 동기화 처리 상세 로그")
                    for log in logs:
                        st.markdown(log)
                    
                    st.info("💡 동기화된 기초 데이터는 [학교기본설정] 및 [교사조건입력] 페이지에서 확인 및 수정할 수 있습니다.")
                else:
                    st.error("❌ 동기화 도중 오류가 발생했습니다.")
                    for log in logs:
                        st.markdown(log)

with col2:
    st.markdown('<div class="card-title">📖 구글 시트 템플릿 작성 가이드</div>', unsafe_allow_html=True)
    st.markdown("""
    구글 시트를 이용해 선생님들의 시간표 제약 조건을 온라인으로 간편하게 취합하세요!  
    시트 내에 아래의 **4개 탭**을 정확한 이름으로 만들어야 합니다:
    """)
    
    with st.expander("📚 1. [교과시수] 탭 설정"):
        st.markdown("""
        <div class="guide-box">
            학년별 각 과목당 주간 시수 기준표를 등록합니다.<br>
            - <strong>필수 열:</strong> 학년, 과목, 주간시수<br><br>
            <strong>작성 예시:</strong><br>
            | 학년 | 과목 | 주간시수 |<br>
            | 1학년 | 국어 | 4 |<br>
            | 1학년 | 수학 | 4 |<br>
            | 2학년 | 과학 | 3 |
        </div>
        """, unsafe_allow_html=True)

    with st.expander("👩‍🏫 2. [교사기초자료] 탭 설정"):
        st.markdown("""
        <div class="guide-box">
            교사 목록과 각 교사의 담당 학년, 교과, 배정 금지 시간을 지정합니다.<br>
            - <strong>필수 열:</strong> 교사명, 담당교과, 담당학년, 순회교사여부, 배정금지요일교시<br>
            - <strong>담당교과:</strong> 여러 개일 경우 콤마(,)로 구분 (예: 수학, 정보)<br>
            - <strong>담당학년:</strong> 여러 개일 경우 콤마(,)로 구분 (예: 1학년, 2학년)<br>
            - <strong>순회교사여부:</strong> O 또는 X<br>
            - <strong>배정금지요일교시:</strong> 콤마로 구분하여 입력 (예: 월1, 화5, 금7)<br><br>
            <strong>작성 예시:</strong><br>
            | 교사명 | 담당교과 | 담당학년 | 순회교사여부 | 배정금지요일교시 |<br>
            | 홍길동 | 수학 | 1학년,2학년 | X | 월1, 월2 |<br>
            | 김순회 | 영어 | 3학년 | O | 수3, 수4 |
        </div>
        """, unsafe_allow_html=True)

    with st.expander("⏱ 3. [블록타임] 탭 설정"):
        st.markdown("""
        <div class="guide-box">
            연속으로 묶어서 진행해야 하는 교과를 설정합니다. (과학실험, 미술 등)<br>
            - <strong>필수 열:</strong> 학급, 과목, 연속교시<br><br>
            <strong>작성 예시:</strong><br>
            | 학급 | 과목 | 연속교시 |<br>
            | 1학년 1반 | 과학 | 2 |<br>
            | 1학년 2반 | 미술 | 2 |
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🔒 4. [순회교사고정] 탭 설정"):
        st.markdown("""
        <div class="guide-box">
            순회교사의 타교 근무 시간 등 특정 고정 시간대를 강제 배정합니다.<br>
            - <strong>필수 열:</strong> 교사명, 요일, 교시, 학급, 과목<br>
            - 타교 출강 등 빈 시간으로 비워야 하는 칸은 학급 열에 <strong>(타교)</strong> 라고 적어줍니다.<br><br>
            <strong>작성 예시:</strong><br>
            | 교사명 | 요일 | 교시 | 학급 | 과목 |<br>
            | 김순회 | 월 | 1 | (타교) | 영어 |<br>
            | 김순회 | 월 | 2 | (타교) | 영어 |
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("""
    💡 <strong>중요 설정:</strong> 구글 스프레드시트 우측 상단 <strong>[공유]</strong> 버튼을 누르고 일반 액세스를 <strong>'링크가 있는 모든 사용자'</strong> 및 <strong>'뷰어'</strong>로 설정해야 프로그램이 해당 데이터를 읽어올 수 있습니다.
    """, unsafe_allow_html=True)
