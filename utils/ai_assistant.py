"""
ai_assistant.py
Gemini API를 이용한 시간표 진단 및 조언
"""
import google.generativeai as genai
import streamlit as st
import json
from .constraints import Assignment

def get_api_key(data: dict):
    # 세션 또는 data 딕셔너리에서 API 키를 가져옵니다.
    if "gemini_api_key" in st.session_state and st.session_state.gemini_api_key:
        return st.session_state.gemini_api_key
    return data.get("api_key", "")

def diagnose_timetable(data: dict, assignments: list[Assignment], stats: dict) -> str:
    """
    생성된 시간표 초안을 바탕으로 프롬프트를 구성하여 Gemini에게 평가를 요청합니다.
    """
    api_key = get_api_key(data)
    if not api_key:
        return "⚠️ Google Gemini API 키가 설정되어 있지 않습니다. 설정 메뉴에서 API 키를 입력해주세요."
    
    try:
        genai.configure(api_key=api_key)
        # 안전하고 호환성이 높은 모델 사용
        model = genai.GenerativeModel('gemini-pro')
        
        # 시간표 기초 통계 텍스트 구성
        filled_count = stats.get('total_assigned', len(assignments))
        score = stats.get('quality', {}).get('score', 0)
        detail = stats.get('quality', {}).get('detail', "")
        
        prompt = f"""
당신은 중학교 시간표 편성 전문가 AI입니다.
아래는 이번에 새롭게 짜여진 시간표의 기본 정보와 품질 지표입니다.

[시간표 기초 지표]
- 전체 배정된 수업 수: {filled_count}개
- 종합 품질 점수(알고리즘 산출): {score} / 100
- 세부 내용: {detail}

[요청 사항]
위의 정보와 시간표 편성의 일반적인 제약 조건(예: 한 교사가 하루에 특정 반에 여러 번 들어가는지, 수업이 오후에 너무 몰려있는지 등)을 바탕으로, 선생님들을 위해 다음의 리포트를 작성해 주세요.
1. 이 시간표의 긍정적인 점 (장점)
2. 품질 점수 향상을 위해 개선이 필요한 점이나 잠재적 갈등(병목 현상) 요소
3. 개선을 위한 구체적인 대안 1~2가지 (예: "음악 수업을 오전에 배치하면 덜 피로할 것입니다.")

친절하고 전문적인 어조로 답변해 주며, 마크다운 형식으로 보기 좋게 정리해 주세요.
"""
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"⚠️ API 요청 중 오류가 발생했습니다: {str(e)}"
