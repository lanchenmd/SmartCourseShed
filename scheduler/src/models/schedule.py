from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional


@dataclass
class ClassInfo:
    id: str
    name: str
    student_count: int


@dataclass
class TeacherInfo:
    id: str
    name: str


@dataclass
class RoomInfo:
    id: str
    name: str
    capacity: int
    room_type: str = "普通"  # 普通 | 实验室 | 机房 | 音乐教室 | 体育馆 | 美术室


@dataclass
class CombinedClass:
    class_set: List[str]  # 组成合班的班级ID列表
    teacher_id: str
    subject: str
    room_type: str  # 所需教室类型


@dataclass
class ScheduleInput:
    school_id: str
    timeslots: List[str]
    classes: List[ClassInfo]
    teachers: List[TeacherInfo]
    rooms: List[RoomInfo]
    subjects: List[str]
    teacher_of: Dict[str, Dict[str, str]]  # {class_id: {subject: teacher_id}}
    required_hours: Dict[str, Dict[str, int]]  # {class_id: {subject: hours}}
    combined_classes: List[CombinedClass] = field(default_factory=list)
    special_rooms: Dict[str, List[str]] = field(default_factory=dict)  # {room_id: [subject_list]}
    teacher_unavailability: Dict[str, Set[str]] = field(default_factory=dict)  # {teacher_id: {timeslot_set}}

    @classmethod
    def from_request(cls, request_dict: dict) -> "ScheduleInput":
        classes = [ClassInfo(**c) for c in request_dict["classes"]]
        teachers = [TeacherInfo(**t) for t in request_dict["teachers"]]
        rooms = [RoomInfo(**r) for r in request_dict["rooms"]]
        combined = [
            CombinedClass(
                class_set=cc["class_set"],
                teacher_id=cc["teacher_id"],
                subject=cc["subject"],
                room_type=cc.get("room_type", "普通")
            ) for cc in request_dict.get("combined_classes", [])
        ]
        special = {k: v for k, v in request_dict.get("special_rooms", {}).items()}
        unavail = {
            k: set(v) for k, v in request_dict.get("teacher_unavailability", {}).items()
        }
        return cls(
            school_id=request_dict["school_id"],
            timeslots=request_dict["timeslots"],
            classes=classes,
            teachers=teachers,
            rooms=rooms,
            subjects=request_dict["subjects"],
            teacher_of=request_dict["teacher_of"],
            required_hours=request_dict["required_hours"],
            combined_classes=combined,
            special_rooms=special,
            teacher_unavailability=unavail
        )
