"""
data_manager.py
학교 데이터를 JSON 파일로 저장하고 불러오는 유틸리티 모듈
"""
import json
import os
from datetime import date, datetime
from pathlib import Path
import streamlit as st

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_FILE = DATA_DIR / "school_data.json"

DEFAULT_DATA = {
    "school_info": {
        "name": "○○중학교",
        "semester": "2025-1",
        "periods_per_day": 7,
        "days": ["월", "화", "수", "목", "금"],
        "periods_per_day_by_day": {"월": 7, "화": 7, "수": 7, "목": 7, "금": 7},
        "period_times": {
            "1": {"start": "08:50", "end": "09:35"},
            "2": {"start": "09:45", "end": "10:30"},
            "3": {"start": "10:40", "end": "11:25"},
            "4": {"start": "11:35", "end": "12:20"},
            "5": {"start": "13:10", "end": "13:55"},
            "6": {"start": "14:05", "end": "14:50"},
            "7": {"start": "15:00", "end": "15:45"},
        }
    },
    "grades": {
        "1학년": {"classes": ["1반", "2반", "3반"]},
        "2학년": {"classes": ["1반", "2반", "3반"]},
        "3학년": {"classes": ["1반", "2반", "3반"]},
    },
    "teachers": [],
    "curriculum": {
        "1학년": {
            "국어": 4, "수학": 4, "영어": 3, "사회": 3,
            "역사": 2, "과학": 3, "체육": 3, "음악": 1,
            "미술": 1, "기술가정": 2, "도덕": 1
        },
        "2학년": {
            "국어": 4, "수학": 4, "영어": 3, "사회": 3,
            "역사": 2, "과학": 3, "체육": 3, "음악": 1,
            "미술": 1, "기술가정": 2, "도덕": 1
        },
        "3학년": {
            "국어": 4, "수학": 4, "영어": 3, "사회": 3,
            "역사": 2, "과학": 3, "체육": 3, "음악": 1,
            "미술": 1, "기술가정": 2, "도덕": 1
        },
    },
    "special_rooms": [
        {"id": "SR001", "name": "과학실", "subjects": ["과학"]},
        {"id": "SR002", "name": "기술실", "subjects": ["기술가정"]},
        {"id": "SR003", "name": "음악실", "subjects": ["음악"]},
        {"id": "SR004", "name": "미술실", "subjects": ["미술"]},
        {"id": "SR005", "name": "체육관", "subjects": ["체육"]},
        {"id": "SR006", "name": "영어실", "subjects": ["영어"]},
    ],
    "block_times": [],
    "free_semester": {
        "enabled": False,
        "target_grade": "1학년",
        "programs": []
    },
    "timetable": {},
    "substitutions": [],
    "fixed_subject_slots": [],
}

SUBJECT_COLORS = {
    "국어": "#FF6B6B",
    "수학": "#4ECDC4",
    "영어": "#45B7D1",
    "사회": "#96CEB4",
    "역사": "#FFEAA7",
    "과학": "#DDA0DD",
    "체육": "#98D8C8",
    "음악": "#F7DC6F",
    "미술": "#F0B27A",
    "기술가정": "#82E0AA",
    "도덕": "#AED6F1",
    "자유학기": "#F1948A",
    "창체": "#BB8FCE",
    "자습": "#BDC3C7",
    "": "#ECF0F1",
}


def ensure_data_dir():
    """데이터 디렉토리가 없으면 생성"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> dict:
    """학교 데이터를 JSON 파일에서 불러옴. 없으면 기본값 반환."""
    ensure_data_dir()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 기본값에 없는 신규 키 병합
            merged = _deep_merge(DEFAULT_DATA, data)
            
            # 교사 학년 데이터 보정 (예: ["1", "2", "3"] -> ["1학년", "2학년", "3학년"])
            teachers = merged.get("teachers", [])
            for t in teachers:
                norm_grades = []
                for g in t.get("grades", []):
                    g_str = str(g).strip()
                    if g_str in ["1", "2", "3"]:
                        norm_grades.append(f"{g_str}학년")
                    else:
                        norm_grades.append(g_str)
                t["grades"] = norm_grades

            # 교사 매핑 생성 (학년, 과목 -> 교사 ID)
            t_map = {}
            for t in teachers:
                for grade in t.get("grades", []):
                    for subj in t.get("subjects", []):
                        t_map[(grade, subj)] = t["id"]

            # 기존 시간표의 빈 teacher_id 자동으로 채우기
            timetable = merged.get("timetable", {})
            for class_name, cls_tt in timetable.items():
                grade_part = class_name.split()[0] if class_name else ""
                for day, day_tt in cls_tt.items():
                    for period_str, cell in day_tt.items():
                        if isinstance(cell, dict) and cell.get("subject"):
                            if not cell.get("teacher_id"):
                                key = (grade_part, cell["subject"])
                                if key in t_map:
                                    cell["teacher_id"] = t_map[key]

            return merged
        except (json.JSONDecodeError, IOError):
            return dict(DEFAULT_DATA)
    return dict(DEFAULT_DATA)


def save_data(data: dict) -> bool:
    """학교 데이터를 JSON 파일로 저장"""
    ensure_data_dir()
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        st.error(f"저장 실패: {e}")
        return False


def _deep_merge(base: dict, override: dict) -> dict:
    """기본값에 저장된 값을 덮어씌우는 딥 머지"""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def get_data() -> dict:
    """세션 상태에서 데이터를 가져오거나, 없으면 파일에서 로드"""
    if "school_data" not in st.session_state:
        st.session_state.school_data = load_data()
    else:
        # 이미 세션 상태가 초기화되어 있는 경우라도, 기존 데이터를 보정/치유합니다.
        data = st.session_state.school_data
        teachers = data.get("teachers", [])
        
        # 1) 학년 형식 정규화 (1 -> 1학년)
        for t in teachers:
            norm_grades = []
            for g in t.get("grades", []):
                g_str = str(g).strip()
                if g_str in ["1", "2", "3"]:
                    norm_grades.append(f"{g_str}학년")
                else:
                    norm_grades.append(g_str)
            t["grades"] = norm_grades

        # 2) 교사 매핑 및 기존 시간표 빈 teacher_id 채우기
        t_map = {}
        for t in teachers:
            for grade in t.get("grades", []):
                for subj in t.get("subjects", []):
                    t_map[(grade, subj)] = t["id"]

        timetable = data.get("timetable", {})
        for class_name, cls_tt in timetable.items():
            grade_part = class_name.split()[0] if class_name else ""
            for day, day_tt in cls_tt.items():
                for period_str, cell in day_tt.items():
                    if isinstance(cell, dict) and cell.get("subject"):
                        if not cell.get("teacher_id"):
                            key = (grade_part, cell["subject"])
                            if key in t_map:
                                cell["teacher_id"] = t_map[key]
    return st.session_state.school_data


def save_session_data() -> bool:
    """세션 상태의 데이터를 파일로 저장"""
    if "school_data" in st.session_state:
        return save_data(st.session_state.school_data)
    return False


def get_all_classes(data: dict) -> list:
    """모든 학급 목록 반환 (예: ['1학년 1반', '1학년 2반', ...])"""
    classes = []
    for grade, info in data.get("grades", {}).items():
        for cls in info.get("classes", []):
            classes.append(f"{grade} {cls}")
    return classes


def get_periods_for_day(data: dict, day: str) -> int:
    """요일별 최대 교시 수 반환"""
    school_info = data.get("school_info", {})
    by_day = school_info.get("periods_per_day_by_day", {})
    if not by_day:
        return school_info.get("periods_per_day", 7)
    return int(by_day.get(day, school_info.get("periods_per_day", 7)))


def get_teacher_by_id(data: dict, teacher_id: str) -> dict | None:
    """ID로 교사 정보 조회"""
    for t in data.get("teachers", []):
        if t.get("id") == teacher_id:
            return t
    return None


def get_teachers_for_subject_grade(data: dict, subject: str, grade: str) -> list:
    """특정 교과/학년 담당 교사 목록 반환"""
    result = []
    for t in data.get("teachers", []):
        if subject in t.get("subjects", []) and grade in t.get("grades", []):
            result.append(t)
    return result


def get_subject_color(subject: str) -> str:
    """과목명에 따른 색상 반환"""
    return SUBJECT_COLORS.get(subject, "#BDC3C7")


def add_substitution(data: dict, sub: dict):
    """결보강 기록 추가"""
    if "substitutions" not in data:
        data["substitutions"] = []
    sub["id"] = f"SUB{len(data['substitutions'])+1:04d}"
    sub["created_at"] = datetime.now().isoformat()
    data["substitutions"].append(sub)


def generate_teacher_id(data: dict) -> str:
    """새 교사 ID 생성"""
    existing = [t.get("id", "") for t in data.get("teachers", [])]
    i = len(existing) + 1
    while f"T{i:03d}" in existing:
        i += 1
    return f"T{i:03d}"


def get_timetable_cell(data: dict, class_name: str, day: str, period: int) -> dict:
    """특정 학급/요일/교시의 시간표 셀 반환"""
    return (
        data.get("timetable", {})
        .get(class_name, {})
        .get(day, {})
        .get(str(period), {"subject": "", "teacher_id": ""})
    )


def set_timetable_cell(data: dict, class_name: str, day: str, period: int, cell: dict):
    """특정 학급/요일/교시의 시간표 셀 설정"""
    tt = data.setdefault("timetable", {})
    cls_tt = tt.setdefault(class_name, {})
    day_tt = cls_tt.setdefault(day, {})
    day_tt[str(period)] = cell


# ──────────────────────────────────────────────────────────────────────────────
# 구글 시트 연동 기능 추가
# ──────────────────────────────────────────────────────────────────────────────
import re
import urllib.parse
import urllib.request
import pandas as pd
import io

def extract_google_sheet_id(url: str) -> str | None:
    """구글 시트 URL에서 Document ID 추출"""
    match = re.search(r"/d/([^/]+)", url)
    return match.group(1) if match else None


def fetch_google_sheet_tab(doc_id: str, tab_name: str) -> pd.DataFrame:
    """구글 시트의 특정 탭 데이터를 CSV 형태로 패치하여 DataFrame으로 변환"""
    encoded_tab = urllib.parse.quote(tab_name)
    export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={encoded_tab}"
    
    try:
        req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            csv_data = response.read()
            
        try:
            decoded_csv = csv_data.decode('utf-8')
        except UnicodeDecodeError:
            decoded_csv = csv_data.decode('cp949')
            
        df = pd.read_csv(io.StringIO(decoded_csv))
        # 열 이름 정리
        df.columns = df.columns.str.strip().str.replace('\n', '', regex=False).str.replace('\r', '', regex=False)
        return df
    except Exception as e:
        raise Exception(f"'{tab_name}' 탭을 가져오지 못했습니다: {e}")


def sync_all_from_google_sheet(data: dict, url: str) -> tuple[bool, list[str]]:
    """구글 시트 URL을 파싱하여 전체 기초 데이터를 동기화"""
    doc_id = extract_google_sheet_id(url)
    if not doc_id:
        return False, ["올바른 구글 시트 URL이 아닙니다."]
        
    logs = []
    
    # 1. 교과시수 동기화
    try:
        df_curr = fetch_google_sheet_tab(doc_id, "교과시수")
        required_cols = ["학년", "과목", "주간시수"]
        if all(col in df_curr.columns for col in required_cols):
            # curriculum 데이터 구성
            new_curr = {"1학년": {}, "2학년": {}, "3학년": {}}
            for _, row in df_curr.iterrows():
                grade = str(row["학년"]).strip()
                subj = str(row["과목"]).strip()
                try:
                    hrs = int(row["주간시수"])
                except ValueError:
                    hrs = 0
                
                if grade in new_curr:
                    new_curr[grade][subj] = hrs
            data["curriculum"] = new_curr
            logs.append("✅ [교과시수] 탭 동기화 완료")
        else:
            logs.append("⚠️ [교과시수] 필수 열(학년, 과목, 주간시수)이 없어 건너뜁니다.")
    except Exception as e:
        logs.append(f"❌ [교과시수] 동기화 실패: {e}")

    # 2. 교사 기정 데이터 & 배정 금지/필수 동기화
    try:
        df_teachers = fetch_google_sheet_tab(doc_id, "교사기초자료")
        required_cols = ["교사명", "담당교과", "담당학년", "순회교사여부"]
        if all(col in df_teachers.columns for col in required_cols):
            teachers_by_name = {}
            for _, row in df_teachers.iterrows():
                t_name = str(row["교사명"]).strip()
                if not t_name or t_name == "nan":
                    continue
                
                t_subjs = [s.strip() for s in str(row["담당교과"]).split(",") if s.strip()]
                raw_grades = [g.strip() for g in str(row["담당학년"]).split(",") if g.strip()]
                t_grades = []
                for g in raw_grades:
                    if g in ["1", "2", "3"]:
                        t_grades.append(f"{g}학년")
                    else:
                        t_grades.append(g)
                is_visiting = str(row["순회교사여부"]).strip().upper() in ["O", "YES", "TRUE", "예"]
                
                # 배정 금지 요일교시 파싱 (예: "월1, 월2, 화5")
                blocked_slots = []
                blocked_raw = str(row.get("배정금지요일교시", ""))
                if blocked_raw and blocked_raw != "nan":
                    slots_list = [s.strip() for s in blocked_raw.split(",") if s.strip()]
                    for slot_str in slots_list:
                        match = re.match(r"([월화수목금])([1-9])", slot_str)
                        if match:
                            blocked_slots.append({
                                "day": match.group(1),
                                "period": int(match.group(2))
                            })
                
                # 필수 배정 요일교시 파싱 (예: "월3, 목4")
                required_slots = []
                required_raw = str(row.get("필수배정요일교시", ""))
                if required_raw and required_raw != "nan":
                    slots_list = [s.strip() for s in required_raw.split(",") if s.strip()]
                    for slot_str in slots_list:
                        match = re.match(r"([월화수목금])([1-9])", slot_str)
                        if match:
                            req_subj = t_subjs[0] if t_subjs else ""
                            required_slots.append({
                                "day": match.group(1),
                                "period": int(match.group(2)),
                                "subject": req_subj
                            })
                
                if t_name in teachers_by_name:
                    # 동일한 이름의 교사는 교과/학년/조건 병합 (선생님 중복배정 방지)
                    existing = teachers_by_name[t_name]
                    existing.setdefault("subject_grades", {})
                    for s in t_subjs:
                        if s not in existing["subjects"]:
                            existing["subjects"].append(s)
                        existing["subject_grades"].setdefault(s, [])
                        for g in t_grades:
                            if g not in existing["subject_grades"][s]:
                                existing["subject_grades"][s].append(g)
                    for g in t_grades:
                        if g not in existing["grades"]:
                            existing["grades"].append(g)
                    if is_visiting:
                        existing["is_visiting"] = True
                    for slot in blocked_slots:
                        if slot not in existing["blocked_slots"]:
                            existing["blocked_slots"].append(slot)
                    for slot in required_slots:
                        if slot not in existing["required_slots"]:
                            existing["required_slots"].append(slot)
                else:
                    subject_grades = {}
                    for s in t_subjs:
                        subject_grades[s] = list(t_grades)
                    teachers_by_name[t_name] = {
                        "name": t_name,
                        "subjects": t_subjs,
                        "grades": t_grades,
                        "subject_grades": subject_grades,
                        "is_visiting": is_visiting,
                        "blocked_slots": blocked_slots,
                        "required_slots": required_slots,
                        "fixed_slots": []
                    }
            
            new_teachers = []
            for idx, (t_name, t_info) in enumerate(teachers_by_name.items()):
                t_info["id"] = f"T{idx+1:03d}"
                new_teachers.append(t_info)
                
            data["teachers"] = new_teachers
            logs.append(f"✅ [교사기초자료] 동기화 완료 (교사명 기준 병합 처리, 총 {len(new_teachers)}명 등록)")
        else:
            logs.append("⚠️ [교사기초자료] 필수 열(교사명, 담당교과, 담당학년, 순회교사여부)이 없어 건너뜁니다.")
    except Exception as e:
        logs.append(f"❌ [교사기초자료] 동기화 실패: {e}")

    # 3. 블록타임 동기화
    try:
        df_blocks = fetch_google_sheet_tab(doc_id, "블록타임")
        required_cols = ["학급", "과목", "연속교시"]
        if all(col in df_blocks.columns for col in required_cols):
            new_blocks = []
            for _, row in df_blocks.iterrows():
                cname = str(row["학급"]).strip()
                subj = str(row["과목"]).strip()
                try:
                    n_consec = int(row["연속교시"])
                except ValueError:
                    n_consec = 2
                
                if cname and subj and cname != "nan" and subj != "nan":
                    new_blocks.append({
                        "class_name": cname,
                        "subject": subj,
                        "n_consecutive": n_consec
                    })
            data["block_times"] = new_blocks
            logs.append(f"✅ [블록타임] 동기화 완료 (설정 {len(new_blocks)}건)")
        else:
            logs.append("⚠️ [블록타임] 필수 열(학급, 과목, 연속교시)이 없어 건너뜁니다.")
    except Exception as e:
        logs.append(f"❌ [블록타임] 동기화 실패: {e}")

    # 4. 순회교사 고정시간 동기화
    try:
        df_fixed = fetch_google_sheet_tab(doc_id, "순회교사고정")
        required_cols = ["교사명", "요일", "교시", "학급", "과목"]
        if all(col in df_fixed.columns for col in required_cols):
            fixed_count = 0
            for _, row in df_fixed.iterrows():
                t_name = str(row["교사명"]).strip()
                day = str(row["요일"]).strip()
                try:
                    period = int(row["교시"])
                except ValueError:
                    continue
                cname = str(row["학급"]).strip()
                subj = str(row["과목"]).strip()
                
                if t_name == "nan" or not t_name:
                    continue
                
                # 교사 찾기
                teacher_obj = next((t for t in data["teachers"] if t["name"] == t_name), None)
                if teacher_obj:
                    is_other = cname == "(타교)" or cname == "타교" or not cname or cname == "nan"
                    slot_info = {
                        "day": day,
                        "period": period,
                        "class_name": "" if is_other else cname,
                        "subject": subj if subj != "nan" else "",
                        "is_other_school": is_other
                    }
                    teacher_obj.setdefault("fixed_slots", []).append(slot_info)
                    
                    # 타교인 경우 배정금지 목록에도 자동 추가
                    if is_other:
                        teacher_obj.setdefault("blocked_slots", []).append({
                            "day": day,
                            "period": period
                        })
                    fixed_count += 1
            logs.append(f"✅ [순회교사고정] 동기화 완료 (고정 {fixed_count}건 설정)")
        else:
            logs.append("⚠️ [순회교사고정] 필수 열(교사명, 요일, 교시, 학급, 과목)이 없어 건너뜁니다.")
    except Exception as e:
        logs.append(f"❌ [순회교사고정] 동기화 실패: {e}")

    # 5. 시간고정배정 동기화
    try:
        df_fixed_subj = fetch_google_sheet_tab(doc_id, "시간고정배정")
        required_cols = ["학급명", "요일", "교시", "과목명"]
        if all(col in df_fixed_subj.columns for col in required_cols):
            new_fixed_subj = []
            for _, row in df_fixed_subj.iterrows():
                class_raw = str(row["학급명"]).strip()
                day = str(row["요일"]).strip()
                try:
                    period = int(row["교시"])
                except ValueError:
                    continue
                subj = str(row["과목명"]).strip()
                
                if class_raw == "nan" or not class_raw or subj == "nan" or not subj:
                    continue
                
                # 만약 class_raw가 "1학년"처럼 학년으로만 되어 있다면, 그 학년의 모든 학급으로 동적 확장!
                matched_classes = []
                if class_raw in ["1학년", "2학년", "3학년", "1", "2", "3"]:
                    grade_key = f"{class_raw}학년" if class_raw in ["1", "2", "3"] else class_raw
                    classes_in_grade = data.get("grades", {}).get(grade_key, {}).get("classes", [])
                    for cls in classes_in_grade:
                        matched_classes.append(f"{grade_key} {cls}")
                else:
                    norm_class = class_raw
                    match = re.match(r"([123])\s*학년?\s*([1-9])\s*반?", class_raw)
                    if match:
                        norm_class = f"{match.group(1)}학년 {match.group(2)}반"
                    matched_classes.append(norm_class)
                
                for cname in matched_classes:
                    new_fixed_subj.append({
                        "class_name": cname,
                        "day": day,
                        "period": period,
                        "subject": subj
                    })
            data["fixed_subject_slots"] = new_fixed_subj
            logs.append(f"✅ [시간고정배정] 동기화 완료 (고정 {len(new_fixed_subj)}건 설정)")
        else:
            logs.append("⚠️ [시간고정배정] 필수 열(학급명, 요일, 교시, 과목명)이 없어 건너뜁니다.")
    except Exception:
        # [시간고정배정] 탭이 없는 경우 선택사항이므로 조용히 건너뜁니다.
        pass

    # 변경사항 저장
    save_data(data)
    return True, logs

