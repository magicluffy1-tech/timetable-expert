"""
constraints.py
시간표 제약조건 정의 및 검증 모듈
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SlotKey:
    """(요일, 교시) 를 나타내는 키"""
    day: str
    period: int

    def __hash__(self):
        return hash((self.day, self.period))

    def __eq__(self, other):
        return self.day == other.day and self.period == other.period

    def __repr__(self):
        return f"{self.day}{self.period}교시"


@dataclass
class Assignment:
    """시간표의 단일 셀 배정 결과"""
    class_name: str       # 예: '1학년 1반'
    day: str
    period: int
    subject: str
    teacher_id: str
    special_room: Optional[str] = None
    is_block: bool = False


def build_constraints(data: dict) -> dict:
    """
    학교 데이터에서 제약조건 딕셔너리를 빌드한다.

    반환:
        {
          "teacher_blocked": {teacher_id: set(SlotKey)},
          "teacher_fixed":   {teacher_id: {SlotKey: {class_name, subject}}},
          "room_occupied":   {room_name: set(SlotKey)},
          "block_groups":    [(class_name, subject, n_consecutive)],
          "teacher_subjects":{teacher_id: {grade: [subjects]}},
        }
    """
    teacher_blocked: dict[str, set] = {}
    teacher_fixed: dict[str, dict] = {}
    teacher_subjects: dict[str, dict] = {}

    for t in data.get("teachers", []):
        tid = t["id"]
        teacher_blocked[tid] = set()
        teacher_fixed[tid] = {}
        teacher_subjects[tid] = {}

        # 배정 금지 시간
        for slot in t.get("blocked_slots", []):
            teacher_blocked[tid].add(SlotKey(slot["day"], int(slot["period"])))

        # 고정 시간 (순회교사)
        for slot in t.get("fixed_slots", []):
            key = SlotKey(slot["day"], int(slot["period"]))
            teacher_fixed[tid][key] = {
                "class_name": slot.get("class_name", ""),
                "subject": slot.get("subject", ""),
            }

        # 교과-학년 매핑
        for grade in t.get("grades", []):
            teacher_subjects[tid][grade] = t.get("subjects", [])

    # 블록타임 그룹
    block_groups = []
    for bt in data.get("block_times", []):
        block_groups.append((
            bt["class_name"],
            bt["subject"],
            int(bt.get("n_consecutive", 2)),
        ))

    return {
        "teacher_blocked": teacher_blocked,
        "teacher_fixed": teacher_fixed,
        "room_occupied": {},   # 런타임에 채워짐
        "block_groups": block_groups,
        "teacher_subjects": teacher_subjects,
    }


def is_teacher_available(
    constraints: dict,
    teacher_id: str,
    day: str,
    period: int,
    current_assignments: list[Assignment],
) -> bool:
    """해당 요일/교시에 교사를 배정할 수 있는지 검증"""
    slot = SlotKey(day, period)

    # 배정 금지 시간 체크
    if slot in constraints["teacher_blocked"].get(teacher_id, set()):
        return False

    # 이미 같은 시간에 다른 반을 가르치고 있는지 체크
    for a in current_assignments:
        if (
            a.teacher_id == teacher_id
            and a.day == day
            and a.period == period
        ):
            return False

    return True


def is_room_available(
    room_name: str,
    day: str,
    period: int,
    current_assignments: list[Assignment],
) -> bool:
    """특별실이 해당 시간에 사용 가능한지 검증"""
    for a in current_assignments:
        if (
            a.special_room == room_name
            and a.day == day
            and a.period == period
        ):
            return False
    return True


def count_subject_on_day(
    class_name: str,
    subject: str,
    day: str,
    current_assignments: list[Assignment],
) -> int:
    """특정 학급/요일에 해당 과목이 몇 교시 배정되어 있는지 반환"""
    return sum(
        1
        for a in current_assignments
        if a.class_name == class_name
        and a.subject == subject
        and a.day == day
    )


def count_subject_total(
    class_name: str,
    subject: str,
    current_assignments: list[Assignment],
) -> int:
    """특정 학급에 해당 과목이 주간 총 몇 교시 배정되어 있는지 반환"""
    return sum(
        1
        for a in current_assignments
        if a.class_name == class_name
        and a.subject == subject
    )


def validate_timetable(data: dict, assignments: list[Assignment]) -> list[str]:
    """
    완성된 시간표의 제약조건 위반 사항을 검증한다.

    반환:
        위반 사항 메시지 목록 (빈 리스트 = 이상 없음)
    """
    errors = []

    # 1. 교사 중복 체크
    teacher_slots: dict[tuple, str] = {}
    for a in assignments:
        key = (a.teacher_id, a.day, a.period)
        if key in teacher_slots:
            t = _get_teacher_name(data, a.teacher_id)
            errors.append(
                f"❌ 교사 중복: {t} 선생님이 {a.day} {a.period}교시에 {teacher_slots[key]}와 {a.class_name} 동시 배정"
            )
        else:
            teacher_slots[key] = a.class_name

    # 2. 특별실 중복 체크
    room_slots: dict[tuple, str] = {}
    for a in assignments:
        if a.special_room:
            key = (a.special_room, a.day, a.period)
            if key in room_slots:
                errors.append(
                    f"❌ 특별실 중복: {a.special_room}이 {a.day} {a.period}교시에 {room_slots[key]}와 {a.class_name} 동시 사용"
                )
            else:
                room_slots[key] = a.class_name

    # 3. 하루 3회 이상 동일 과목 체크 (경고)
    for a in assignments:
        cnt = count_subject_on_day(a.class_name, a.subject, a.day, assignments)
        if cnt >= 3 and a.subject not in ["자습", "창체", ""]:
            msg = f"⚠️ 과목 집중: {a.class_name} {a.day}요일에 {a.subject} {cnt}교시 연속 배치"
            if msg not in errors:
                errors.append(msg)

    # 4. 시수 충족 여부
    curriculum = data.get("curriculum", {})
    assigned_counts: dict[tuple, int] = {}
    for a in assignments:
        grade = a.class_name.split()[0]
        key = (grade, a.subject)
        assigned_counts[key] = assigned_counts.get(key, 0) + 1

    grades = data.get("grades", {})
    for grade, ginfo in grades.items():
        n_classes = len(ginfo.get("classes", []))
        grade_curr = curriculum.get(grade, {})
        for subj, required in grade_curr.items():
            if required == 0:
                continue
            assigned = assigned_counts.get((grade, subj), 0)
            # 학급당 시수 비교 (전체 학급 총합 / 학급 수)
            per_class = assigned // n_classes if n_classes else 0
            if per_class < required:
                errors.append(
                    f"⚠️ 시수 부족: {grade} {subj} 요구 {required}시간/주, 배정 {per_class}시간/주"
                )

    return errors


def _get_teacher_name(data: dict, teacher_id: str) -> str:
    for t in data.get("teachers", []):
        if t["id"] == teacher_id:
            return t.get("name", teacher_id)
    return teacher_id


def calculate_quality_score(assignments: list[Assignment], data: dict) -> dict:
    """
    시간표 품질 지표 계산

    반환:
        {
          "score": 0~100 (높을수록 좋음),
          "balance_score": 과목 균형도,
          "morning_score": 1교시 배치 적절성,
          "detail": 상세 설명 문자열
        }
    """
    if not assignments:
        return {"score": 0, "balance_score": 0, "morning_score": 0, "detail": "배정 없음"}

    total_cells = len(assignments)
    penalty = 0
    details = []

    # 1. 동일 과목 하루 집중 패널티
    day_subj_count: dict = {}
    for a in assignments:
        key = (a.class_name, a.day, a.subject)
        day_subj_count[key] = day_subj_count.get(key, 0) + 1

    overload = sum(max(0, v - 2) for v in day_subj_count.values())
    if overload > 0:
        penalty += overload * 5
        details.append(f"과목 집중 패널티: -{overload * 5}점 ({overload}건)")

    # 2. 1교시 기피 과목 배치 (수학, 영어)
    avoid_first = ["수학", "영어", "과학"]
    first_period_bad = sum(
        1
        for a in assignments
        if a.period == 1 and a.subject in avoid_first
    )
    penalty += first_period_bad * 3
    if first_period_bad:
        details.append(f"1교시 기피과목: -{first_period_bad * 3}점 ({first_period_bad}건)")

    # 3. 5교시 (점심 후) 기피 과목
    after_lunch_bad = sum(
        1
        for a in assignments
        if a.period == 5 and a.subject in avoid_first
    )
    penalty += after_lunch_bad * 2
    if after_lunch_bad:
        details.append(f"5교시 기피과목: -{after_lunch_bad * 2}점 ({after_lunch_bad}건)")

    max_penalty = total_cells * 5
    score = max(0, 100 - int(penalty / max(max_penalty, 1) * 100))
    balance_score = max(0, 100 - int(overload / max(total_cells, 1) * 100))
    morning_score = max(0, 100 - int((first_period_bad + after_lunch_bad) / max(total_cells, 1) * 100))

    return {
        "score": score,
        "balance_score": balance_score,
        "morning_score": morning_score,
        "detail": " | ".join(details) if details else "최적 배치",
    }
