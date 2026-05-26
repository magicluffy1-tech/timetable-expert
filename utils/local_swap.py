"""
local_swap.py
스마트 연쇄 재배정 - Local Swap 알고리즘

전체 시간표를 재생성하지 않고, 변경된 셀과 충돌하는 최소 범위만 국소적으로
교환(swap)하여 다른 학급/교사의 시간표 변경을 최소화합니다.

알고리즘 개요:
  1) 사용자가 '셀 A → 새 과목/요일/교시'를 요청
  2) 충돌 탐지: 새 슬롯의 교사/학급 중복 여부 확인
  3) 충돌이 없으면 즉시 적용 (단순 이동)
  4) 충돌이 있으면 동일 학급·동일 과목 중 빈 슬롯 또는 교환 가능 슬롯을 찾아 Swap
  5) Swap 대상을 찾지 못할 경우 사용자에게 안내 메시지 반환
"""

import copy
from typing import Optional


def _get_cell(timetable: dict, class_name: str, day: str, period: int) -> dict:
    """시간표 딕셔너리에서 특정 셀 반환 (없으면 빈 dict)"""
    return timetable.get(class_name, {}).get(day, {}).get(str(period), {})


def _set_cell(timetable: dict, class_name: str, day: str, period: int, cell: dict):
    """시간표 딕셔너리의 특정 셀 설정"""
    timetable.setdefault(class_name, {}).setdefault(day, {})[str(period)] = cell


def _clear_cell(timetable: dict, class_name: str, day: str, period: int):
    """특정 셀을 비운다"""
    _set_cell(timetable, class_name, day, period, {"subject": "", "teacher_id": "", "special_room": "", "is_block": False})


def _is_teacher_busy(timetable: dict, teacher_id: str, day: str, period: int, exclude_class: str = "") -> bool:
    """해당 요일/교시에 해당 교사가 다른 학급에 배정되어 있는지 확인"""
    if not teacher_id:
        return False
    for cname, cls_tt in timetable.items():
        if cname == exclude_class:
            continue
        cell = cls_tt.get(day, {}).get(str(period), {})
        if cell.get("teacher_id") == teacher_id and cell.get("subject"):
            return True
    return False


def _is_teacher_blocked(data: dict, teacher_id: str, day: str, period: int) -> bool:
    """교사의 배정 금지 시간인지 확인"""
    for t in data.get("teachers", []):
        if t.get("id") == teacher_id:
            for bs in t.get("blocked_slots", []):
                if bs.get("day") == day and int(bs.get("period", 0)) == period:
                    return True
    return False


def _find_swappable_slot(
    timetable: dict,
    data: dict,
    class_name: str,
    subject: str,
    teacher_id: str,
    target_day: str,
    target_period: int,
) -> Optional[tuple[str, int]]:
    """
    동일 학급·동일 과목 중, 새 슬롯으로 이동시킬 수 있는 기존 슬롯을 찾는다.
    반환: (day, period) 또는 None
    """
    days = data.get("school_info", {}).get("days", ["월", "화", "수", "목", "금"])
    from .data_manager import get_periods_for_day

    for day in days:
        if day == target_day:
            continue
        max_p = get_periods_for_day(data, day)
        for p in range(1, max_p + 1):
            cell = _get_cell(timetable, class_name, day, p)
            if cell.get("subject") == subject and cell.get("teacher_id") == teacher_id:
                # 이 슬롯이 target_day/period로 이동 가능한지 확인
                # target 위치에서 교사 충돌 없어야 함
                if not _is_teacher_busy(timetable, teacher_id, target_day, target_period, exclude_class=class_name):
                    if not _is_teacher_blocked(data, teacher_id, target_day, target_period):
                        return (day, p)
    return None


def local_swap_reschedule(
    timetable: dict,
    data: dict,
    class_name: str,
    target_day: str,
    target_period: int,
    new_subject: str,
    new_teacher_id: str,
) -> tuple[bool, str, dict]:
    """
    Local Swap 스마트 재배정 메인 함수.

    Parameters
    ----------
    timetable    : 현재 시간표 딕셔너리 (data["timetable"])
    data         : 전체 학교 데이터
    class_name   : 변경할 학급 (예: '1학년 1반')
    target_day   : 변경할 요일
    target_period: 변경할 교시
    new_subject  : 넣고 싶은 새 과목
    new_teacher_id: 담당 교사 ID

    Returns
    -------
    (success: bool, message: str, new_timetable: dict)
    """
    tt = copy.deepcopy(timetable)

    # ─── 현재 target 셀 내용 저장 ───
    existing_cell = _get_cell(tt, class_name, target_day, target_period)
    existing_subject = existing_cell.get("subject", "")
    existing_teacher_id = existing_cell.get("teacher_id", "")

    # ─── Case 1: 교사 충돌이 없으면 바로 배정 ───
    teacher_conflict_class = None
    if new_teacher_id:
        for cname, cls_tt in tt.items():
            if cname == class_name:
                continue
            cell = cls_tt.get(target_day, {}).get(str(target_period), {})
            if cell.get("teacher_id") == new_teacher_id and cell.get("subject"):
                teacher_conflict_class = cname
                break

    if teacher_conflict_class is None:
        # 충돌 없음 → 직접 배정
        # 기존 내용이 있으면, 같은 학급의 빈 슬롯 또는 동일 과목 교환
        if existing_subject and existing_subject != new_subject:
            # 기존 과목을 옮길 빈 자리 탐색
            moved = _try_move_existing(tt, data, class_name, target_day, target_period,
                                       existing_subject, existing_teacher_id)
            if not moved:
                # 이동 실패 - 기존 과목을 비우고 배정 (안내 포함)
                _set_cell(tt, class_name, target_day, target_period, {
                    "subject": new_subject,
                    "teacher_id": new_teacher_id,
                    "special_room": "",
                    "is_block": False,
                })
                return True, (
                    f"✅ '{new_subject}' 배정 완료.\n"
                    f"⚠️ 기존 '{existing_subject}' 수업은 이동할 빈 슬롯이 없어 제거되었습니다. "
                    "수동으로 재배치해 주세요."
                ), tt
            else:
                msg_extra = f"기존 '{existing_subject}' 수업을 빈 슬롯으로 이동했습니다."
        else:
            msg_extra = ""

        _set_cell(tt, class_name, target_day, target_period, {
            "subject": new_subject,
            "teacher_id": new_teacher_id,
            "special_room": "",
            "is_block": False,
        })
        msg = f"✅ '{new_subject}' 배정이 완료되었습니다."
        if msg_extra:
            msg += f"\n📌 {msg_extra}"
        return True, msg, tt

    # ─── Case 2: 교사 충돌 → Swap 시도 ───
    # target 위치의 new_subject와 conflict 위치의 과목을 교환할 수 있는지 시도
    conflict_cell = _get_cell(tt, teacher_conflict_class, target_day, target_period)
    conflict_subject = conflict_cell.get("subject", "")

    # conflict 학급에서 new_subject 교사가 필요 없는 다른 슬롯과 교환 시도
    swap_slot = _find_swappable_slot(
        tt, data, class_name, new_subject if existing_subject else new_subject,
        new_teacher_id, target_day, target_period
    )

    if swap_slot:
        swap_day, swap_period = swap_slot
        swap_cell = _get_cell(tt, class_name, swap_day, swap_period)

        # 현재 target ↔ swap_slot 교환
        _set_cell(tt, class_name, target_day, target_period, {
            "subject": new_subject,
            "teacher_id": new_teacher_id,
            "special_room": "",
            "is_block": False,
        })
        _set_cell(tt, class_name, swap_day, swap_period, existing_cell if existing_subject else {
            "subject": "", "teacher_id": "", "special_room": "", "is_block": False
        })

        msg = (
            f"✅ 스마트 재배정 완료!\n"
            f"'{new_subject}'을 {target_day}요일 {target_period}교시로 이동했습니다.\n"
            f"기존 '{existing_subject}'은 {swap_day}요일 {swap_period}교시로 이동했습니다."
        )
        return True, msg, tt

    # ─── Case 3: Swap 불가 → 실패 안내 ───
    conflicting_teacher = next(
        (t["name"] for t in data.get("teachers", []) if t.get("id") == new_teacher_id), new_teacher_id
    )
    return False, (
        f"⛔ 배정 실패: {conflicting_teacher} 선생님이 {target_day}요일 {target_period}교시에 "
        f"{teacher_conflict_class}에 이미 배정되어 있으며, 자동으로 교환 가능한 슬롯을 찾지 못했습니다.\n"
        "다른 시간대나 '단순 강제 수정' 모드를 이용해 주세요."
    ), timetable


def _try_move_existing(
    tt: dict, data: dict,
    class_name: str, cur_day: str, cur_period: int,
    subject: str, teacher_id: str
) -> bool:
    """
    기존 셀(subject)을 동일 학급 내 빈 슬롯으로 이동 시도.
    성공 시 tt를 직접 수정하고 True 반환.
    """
    days = data.get("school_info", {}).get("days", ["월", "화", "수", "목", "금"])
    from .data_manager import get_periods_for_day

    for day in days:
        max_p = get_periods_for_day(data, day)
        for p in range(1, max_p + 1):
            if day == cur_day and p == cur_period:
                continue
            cell = _get_cell(tt, class_name, day, p)
            if cell.get("subject"):
                continue  # 이미 차있는 슬롯
            # 교사 가용성 체크
            if _is_teacher_busy(tt, teacher_id, day, p, exclude_class=class_name):
                continue
            if _is_teacher_blocked(data, teacher_id, day, p):
                continue
            # 빈 슬롯 발견 → 이동
            _set_cell(tt, class_name, day, p, {
                "subject": subject,
                "teacher_id": teacher_id,
                "special_room": "",
                "is_block": False,
            })
            _clear_cell(tt, class_name, cur_day, cur_period)
            return True
    return False


def validate_feasibility(data: dict) -> list[str]:
    """
    편성 전 물리적 모순 입력을 사전 탐지하여 경고 목록 반환.
    
    반환: 경고 문자열 리스트 (빈 리스트면 문제 없음)
    """
    warnings = []
    curriculum = data.get("curriculum", {})
    grades = data.get("grades", {})
    school_info = data.get("school_info", {})
    teachers = data.get("teachers", [])

    # 요일별 최대 교시 수 계산
    from .data_manager import get_periods_for_day
    days = school_info.get("days", ["월", "화", "수", "목", "금"])

    # ① 교사별 주간 필요 시수 vs 가용 슬롯 검증
    for t in teachers:
        tid = t["id"]
        t_name = t.get("name", tid)
        blocked = set()
        for bs in t.get("blocked_slots", []):
            blocked.add((bs["day"], int(bs["period"])))

        total_available = sum(
            get_periods_for_day(data, d) for d in days
        ) - len(blocked)

        # 이 교사가 담당하는 총 수업 시수 계산
        sub_grades = t.get("subject_grades", {})
        total_needed = 0
        if sub_grades:
            for subj, g_list in sub_grades.items():
                for grade in g_list:
                    n_classes = len(grades.get(grade, {}).get("classes", []))
                    weekly_h = curriculum.get(grade, {}).get(subj, 0)
                    total_needed += n_classes * weekly_h
        else:
            for grade in t.get("grades", []):
                n_classes = len(grades.get(grade, {}).get("classes", []))
                for subj in t.get("subjects", []):
                    weekly_h = curriculum.get(grade, {}).get(subj, 0)
                    total_needed += n_classes * weekly_h

        if total_needed > total_available:
            warnings.append(
                f"⚠️ [{t_name}] 주간 필요 시수 {total_needed}시간 > 가용 슬롯 {total_available}시간 "
                f"(배정금지 {len(blocked)}개 제외). 일부 수업이 미배정될 수 있습니다."
            )

    # ② 교사 미배정 과목 탐지
    teacher_map: dict[tuple, list] = {}
    for t in teachers:
        sub_grades = t.get("subject_grades", {})
        if sub_grades:
            for subj, g_list in sub_grades.items():
                for grade in g_list:
                    teacher_map.setdefault((grade, subj), []).append(t["id"])
        else:
            for grade in t.get("grades", []):
                for subj in t.get("subjects", []):
                    teacher_map.setdefault((grade, subj), []).append(t["id"])

    for grade, grade_curr in curriculum.items():
        for subj, hrs in grade_curr.items():
            if hrs <= 0:
                continue
            key = (grade, subj)
            if key not in teacher_map or not teacher_map[key]:
                warnings.append(
                    f"⚠️ [{grade} {subj}] 담당 교사가 지정되지 않았습니다. "
                    "구글 시트의 [교사기초자료]를 확인해 주세요."
                )

    return warnings
