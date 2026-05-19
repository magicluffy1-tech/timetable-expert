"""
scheduler.py
중학교 시간표 자동 편성 알고리즘

배정 우선순위:
  1) 순회교사 고정 시간
  2) 블록타임(연속 수업) 배정
  3) 특별실 필요 과목
  4) 일반 과목

알고리즘:
  - 우선순위별 그리디 + 백트래킹
  - MRV(최소 가능값 우선) 휴리스틱
  - 최대 N개 후보 초안 생성
"""

import random
import copy
from typing import Optional
from .constraints import (
    Assignment, SlotKey,
    build_constraints,
    is_teacher_available,
    is_room_available,
    count_subject_on_day,
    count_subject_total,
    calculate_quality_score,
)
from .data_manager import get_periods_for_day

MAX_BACKTRACK = 50_000   # 백트래킹 최대 시도 횟수


def generate_timetable(data: dict, seed: Optional[int] = None) -> tuple[list[Assignment], dict]:
    """
    학교 데이터를 받아 시간표 배정 결과를 반환한다.

    반환:
        (assignments, stats)
        assignments: Assignment 리스트
        stats: {"success": bool, "backtracks": int, "quality": dict}
    """
    if seed is not None:
        random.seed(seed)

    constraints = build_constraints(data)
    days = data["school_info"]["days"]
    grades = data.get("grades", {})
    curriculum = data.get("curriculum", {})
    special_rooms = data.get("special_rooms", [])

    # ──────────────────────────────────────────
    # 전처리: 교사-과목-학년 매핑 테이블 구성
    # ──────────────────────────────────────────
    # teacher_map[(grade, subject)] = [teacher_id, ...]
    teacher_map: dict[tuple, list] = {}
    for t in data.get("teachers", []):
        sub_grades = t.get("subject_grades", {})
        if sub_grades:
            # 과목별 담당 학년 정보가 구체적으로 지정된 경우
            for subj, grades_list in sub_grades.items():
                for grade in grades_list:
                    norm_grade = f"{grade}학년" if str(grade).strip() in ["1", "2", "3"] else str(grade).strip()
                    key = (norm_grade, subj)
                    teacher_map.setdefault(key, []).append(t["id"])
        else:
            # 하위 호환용 (flat mapping)
            for grade in t.get("grades", []):
                norm_grade = f"{grade}학년" if str(grade).strip() in ["1", "2", "3"] else str(grade).strip()
                for subj in t.get("subjects", []):
                    key = (norm_grade, subj)
                    teacher_map.setdefault(key, []).append(t["id"])

    # room_map[subject] = room_name  (특별실 필요 과목)
    room_map: dict[str, str] = {}
    for sr in special_rooms:
        for subj in sr.get("subjects", []):
            room_map[subj] = sr["name"]

    # ──────────────────────────────────────────
    # 배정 대상 셀 목록 생성
    # ──────────────────────────────────────────
    # 각 학급별로 (day, period, subject) 배정 목표를 만든다.
    all_cells: list[dict] = []  # {class_name, grade, subject, teacher_ids, priority}

    fixed_subject_slots = data.get("fixed_subject_slots", [])
    fixed_counts: dict[tuple[str, str], int] = {}
    for slot in fixed_subject_slots:
        cname = slot.get("class_name", "")
        subj = slot.get("subject", "")
        if cname and subj:
            fixed_counts[(cname, subj)] = fixed_counts.get((cname, subj), 0) + 1

    for grade, ginfo in grades.items():
        grade_curr = curriculum.get(grade, {})
        for cls in ginfo.get("classes", []):
            class_name = f"{grade} {cls}"
            for subj, weekly_hours in grade_curr.items():
                if weekly_hours <= 0:
                    continue
                
                # 고정 선배정된 시수 차감
                fixed_count = fixed_counts.get((class_name, subj), 0)
                remaining_hours = max(0, weekly_hours - fixed_count)
                
                tids = teacher_map.get((grade, subj), [])
                # 특별실 필요 여부로 우선순위 결정
                priority = 1 if subj in room_map else 2
                for _ in range(remaining_hours):
                    all_cells.append({
                        "class_name": class_name,
                        "grade": grade,
                        "subject": subj,
                        "teacher_ids": tids,
                        "priority": priority,
                        "needs_room": room_map.get(subj),
                    })

    # 블록타임 그룹 처리: 연속으로 묶어야 하는 셀을 표시
    block_groups = constraints.get("block_groups", [])
    block_set: set[tuple] = set()
    for (cname, subj, n) in block_groups:
        block_set.add((cname, subj))

    # 우선순위 정렬 (priority 낮을수록 먼저)
    all_cells.sort(key=lambda c: c["priority"])

    # ──────────────────────────────────────────
    # Phase 0: 과목 고정 시간 선배정
    # ──────────────────────────────────────────
    assignments: list[Assignment] = []
    backtracks = 0

    for slot in fixed_subject_slots:
        cname = slot.get("class_name", "")
        day = slot.get("day", "")
        period_val = slot.get("period")
        subj = slot.get("subject", "")
        
        if cname and day and period_val and subj:
            grade = cname.split()[0] if cname else ""
            tids = teacher_map.get((grade, subj), [])
            teacher_id = tids[0] if tids else ""
            
            a = Assignment(
                class_name=cname,
                day=day,
                period=int(period_val),
                subject=subj,
                teacher_id=teacher_id,
                special_room=room_map.get(subj),
                is_block=False
            )
            assignments.append(a)

    # ──────────────────────────────────────────
    # Phase 1: 순회교사 고정 시간 선배정
    # ──────────────────────────────────────────
    for t in data.get("teachers", []):
        if not t.get("is_visiting", False):
            continue
        for slot_info in t.get("fixed_slots", []):
            a = Assignment(
                class_name=slot_info.get("class_name", ""),
                day=slot_info["day"],
                period=int(slot_info["period"]),
                subject=slot_info.get("subject", ""),
                teacher_id=t["id"],
                special_room=None,
                is_block=False,
            )
            assignments.append(a)

    # ──────────────────────────────────────────
    # Phase 1.5: 교사 필수배정요일교시 선배정
    # ──────────────────────────────────────────
    for t in data.get("teachers", []):
        tid = t["id"]
        for r_slot in t.get("required_slots", []):
            day = r_slot["day"]
            period = int(r_slot["period"])
            req_subj = r_slot.get("subject", "")
            
            # 이 요일/교시에 이미 해당 교사에게 배정된 수업이 있는지 확인
            if any(a.teacher_id == tid and a.day == day and a.period == period for a in assignments):
                continue
            
            # 이 교사가 지도하는 남은 셀(과목/학급) 중 하나를 탐색
            matched_cell_idx = None
            for idx, cell in enumerate(all_cells):
                if tid in cell["teacher_ids"]:
                    # 특정 과목 요구 조건이 있는 경우 과목이 정확히 매치되는지 확인
                    if req_subj and cell["subject"] != req_subj:
                        continue
                        
                    cname = cell["class_name"]
                    # 해당 학급이 이 요일/교시에 이미 선배정되었는지 확인
                    already_assigned = any(
                        a.class_name == cname and a.day == day and a.period == period
                        for a in assignments
                    )
                    if not already_assigned:
                        # 특별실 요건 충돌 확인
                        room_name = cell.get("needs_room")
                        if room_name and not is_room_available(room_name, day, period, assignments):
                            continue
                        
                        matched_cell_idx = idx
                        break
            
            if matched_cell_idx is not None:
                cell = all_cells.pop(matched_cell_idx)
                a = Assignment(
                    class_name=cell["class_name"],
                    day=day,
                    period=period,
                    subject=cell["subject"],
                    teacher_id=tid,
                    special_room=cell.get("needs_room"),
                    is_block=False
                )
                assignments.append(a)

    # ──────────────────────────────────────────
    # Phase 2: 블록타임 배정
    # ──────────────────────────────────────────
    block_cells = [c for c in all_cells if (c["class_name"], c["subject"]) in block_set]
    non_block_cells = [c for c in all_cells if (c["class_name"], c["subject"]) not in block_set]

    # 블록타임 셀을 그룹으로 묶어 배정
    block_assigned: set[tuple] = set()  # (class_name, subject) 배정 완료 여부

    for (cname, subj, n_consec) in block_groups:
        if (cname, subj) in block_assigned:
            continue
        # 해당 셀들 추출
        cells_for_block = [c for c in block_cells
                           if c["class_name"] == cname and c["subject"] == subj]
        if not cells_for_block:
            continue

        tids = cells_for_block[0]["teacher_ids"]
        room_name = cells_for_block[0].get("needs_room")
        total_needed = len(cells_for_block)

        # 배정 가능한 슬롯 찾기 (n_consec 연속 교시)
        placed = 0
        days_shuffled = list(days)
        random.shuffle(days_shuffled)

        for day in days_shuffled:
            if placed >= total_needed:
                break
            periods_for_day = get_periods_for_day(data, day)
            for start_p in range(1, periods_for_day - n_consec + 2):
                periods_needed = list(range(start_p, start_p + n_consec))
                # 연속 교시 모두 가능한지 확인
                ok = True
                for p in periods_needed:
                    # 이미 이 학급/교시에 배정된 것 있으면 스킵
                    already = any(
                        a.class_name == cname and a.day == day and a.period == p
                        for a in assignments
                    )
                    if already:
                        ok = False
                        break
                    # 교사 가용성
                    tid = _pick_teacher(tids, constraints, day, p, assignments)
                    if not tid:
                        ok = False
                        break
                    # 특별실
                    if room_name and not is_room_available(room_name, day, p, assignments):
                        ok = False
                        break

                if ok and placed + n_consec <= total_needed:
                    for i, p in enumerate(periods_needed):
                        tid = _pick_teacher(tids, constraints, day, p, assignments)
                        a = Assignment(
                            class_name=cname,
                            day=day,
                            period=p,
                            subject=subj,
                            teacher_id=tid or "",
                            special_room=room_name,
                            is_block=True,
                        )
                        assignments.append(a)
                        placed += 1

        block_assigned.add((cname, subj))

    # ──────────────────────────────────────────
    # Phase 3: 일반 과목 배정 (그리디 + 백트래킹)
    # ──────────────────────────────────────────
    success = _greedy_assign(
        non_block_cells,
        assignments,
        constraints,
        days,
        data,
    )

    # ──────────────────────────────────────────
    # 품질 평가
    # ──────────────────────────────────────────
    quality = calculate_quality_score(assignments, data)

    return assignments, {
        "success": success,
        "backtracks": backtracks,
        "quality": quality,
        "total_assigned": len(assignments),
    }


def _greedy_assign(
    cells: list[dict],
    assignments: list[Assignment],
    constraints: dict,
    days: list[str],
    data: dict,
) -> bool:
    """그리디 배정: 각 셀을 순서대로 가능한 슬롯에 배정"""
    for cell in cells:
        class_name = cell["class_name"]
        subject = cell["subject"]
        tids = cell["teacher_ids"]
        room_name = cell.get("needs_room")

        # 이미 배정된 시수 확인
        already = count_subject_total(class_name, subject, assignments)

        placed = False
        # 슬롯 순서를 랜덤하게 섞어 다양한 결과 유도
        slots = [(d, p) for d in days for p in range(1, get_periods_for_day(data, d) + 1)]
        random.shuffle(slots)

        for (day, period) in slots:
            # 해당 학급/교시에 이미 배정된 수업이 있으면 스킵
            if any(a.class_name == class_name and a.day == day and a.period == period
                   for a in assignments):
                continue

            # 하루 동일 과목 최대 1회 제한 (자습/창체 제외 - 1일 1교과 원칙)
            if subject not in ["자습", "창체", "자유학기"] and \
               count_subject_on_day(class_name, subject, day, assignments) >= 1:
                continue

            # 교사 선택
            tid = _pick_teacher(tids, constraints, day, period, assignments)
            if not tid and tids:
                continue  # 가용 교사 없음

            # 특별실 체크
            if room_name and not is_room_available(room_name, day, period, assignments):
                continue

            # 배정 실행
            a = Assignment(
                class_name=class_name,
                day=day,
                period=period,
                subject=subject,
                teacher_id=tid or "",
                special_room=room_name,
                is_block=False,
            )
            assignments.append(a)
            placed = True
            break

        # 배정 실패 시 경고용 더미 셀
        if not placed:
            a = Assignment(
                class_name=class_name,
                day="미배정",
                period=0,
                subject=subject,
                teacher_id="",
                special_room=None,
                is_block=False,
            )
            assignments.append(a)

    return True


def _pick_teacher(
    tids: list[str],
    constraints: dict,
    day: str,
    period: int,
    assignments: list[Assignment],
) -> Optional[str]:
    """가용한 교사를 골라 반환 (없으면 None)"""
    shuffled = list(tids)
    random.shuffle(shuffled)
    for tid in shuffled:
        if is_teacher_available(constraints, tid, day, period, assignments):
            return tid
    return None


def assignments_to_timetable_dict(
    assignments: list[Assignment], data: dict
) -> dict:
    """
    Assignment 리스트를 data['timetable'] 형태의 dict로 변환한다.
    data['timetable'][class_name][day][period_str] = {subject, teacher_id, special_room}
    """
    tt: dict = {}
    for a in assignments:
        if a.day == "미배정":
            continue
        cls_tt = tt.setdefault(a.class_name, {})
        day_tt = cls_tt.setdefault(a.day, {})
        day_tt[str(a.period)] = {
            "subject": a.subject,
            "teacher_id": a.teacher_id,
            "special_room": a.special_room or "",
            "is_block": a.is_block,
        }
    return tt


def get_teacher_timetable(
    assignments: list[Assignment], teacher_id: str, data: dict
) -> dict:
    """
    특정 교사의 주간 시간표를 반환한다.
    반환: {day: {period: {class_name, subject}}}
    """
    days = data["school_info"]["days"]
    tt: dict = {d: {p: None for p in range(1, get_periods_for_day(data, d) + 1)} for d in days}

    for a in assignments:
        if a.teacher_id == teacher_id and a.day in tt:
            tt[a.day][a.period] = {
                "class_name": a.class_name,
                "subject": a.subject,
            }
    return tt


def find_substitute_teachers(
    data: dict,
    absent_teacher_id: str,
    day: str,
    period: int,
    subject: str,
    grade: str,
    current_assignments: list[Assignment],
) -> list[dict]:
    """
    결강 발생 시 대체 가능한 교사 목록을 반환한다.
    동일 교과 교사 우선, 그 다음 공강 교사 순.
    """
    constraints = build_constraints(data)
    candidates = []

    for t in data.get("teachers", []):
        tid = t["id"]
        if tid == absent_teacher_id:
            continue
        if not is_teacher_available(constraints, tid, day, period, current_assignments):
            continue

        same_subject = subject in t.get("subjects", [])
        same_grade = grade in t.get("grades", [])
        priority = 0 if (same_subject and same_grade) else (1 if same_subject else 2)

        candidates.append({
            "id": tid,
            "name": t.get("name", tid),
            "subjects": t.get("subjects", []),
            "same_subject": same_subject,
            "same_grade": same_grade,
            "priority": priority,
        })

    candidates.sort(key=lambda c: c["priority"])
    return candidates


def generate_multiple_drafts(data: dict, n: int = 3) -> list[tuple]:
    """
    n개의 시간표 초안을 생성하고 품질 점수 순으로 정렬해 반환.
    반환: [(score, assignments, stats), ...]
    """
    drafts = []
    for i in range(n):
        assignments, stats = generate_timetable(data, seed=i * 42 + 7)
        score = stats["quality"]["score"]
        drafts.append((score, assignments, stats))
    drafts.sort(key=lambda x: x[0], reverse=True)
    return drafts
