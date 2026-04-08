from pydantic import BaseModel, Field
from typing import Dict, List, Set, Optional

from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo, CombinedClass


class ScheduleRequest(BaseModel):
    school_id: str = Field(..., description="学校ID")
    timeslots: List[str] = Field(..., description="时间槽列表，例：['周一第1节', '周一第2节', ...]")
    classes: List[dict] = Field(..., description="班级列表，每个班级含 id, name, student_count")
    teachers: List[dict] = Field(..., description="教师列表，每个教师含 id, name")
    rooms: List[dict] = Field(..., description="教室列表，每个教室含 id, name, capacity, room_type")
    subjects: List[str] = Field(..., description="科目列表，例：['语文', '数学', '英语']")
    teacher_of: Dict[str, Dict[str, str]] = Field(
        ..., description="查表：{class_id: {subject: teacher_id}}"
    )
    required_hours: Dict[str, Dict[str, int]] = Field(
        ..., description="课时要求：{class_id: {subject: weekly_hours}}"
    )
    combined_classes: List[dict] = Field(
        default=[], description="合班组列表，每项含 class_set, teacher_id, subject, room_type"
    )
    special_rooms: Dict[str, List[str]] = Field(
        default={}, description="专用教室允许科目：{room_id: [subject_list]}"
    )
    teacher_unavailability: Dict[str, List[str]] = Field(
        default={}, description="教师不可用时段：{teacher_id: [timeslot_list]}"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id": "school_001",
                "timeslots": ["周一第1节", "周一第2节", "周二第1节"],
                "classes": [
                    {"id": "class_001", "name": "初一(1)班", "student_count": 45}
                ],
                "teachers": [
                    {"id": "teacher_zhang", "name": "张老师"}
                ],
                "rooms": [
                    {"id": "room_101", "name": "101教室", "capacity": 50, "room_type": "普通"}
                ],
                "subjects": ["语文", "数学", "英语"],
                "teacher_of": {
                    "class_001": {"语文": "teacher_zhang", "数学": "teacher_wang"}
                },
                "required_hours": {
                    "class_001": {"语文": 4, "数学": 4, "英语": 3}
                },
                "combined_classes": [],
                "special_rooms": {},
                "teacher_unavailability": {}
            }
        }
    }

    def to_schedule_input(self) -> ScheduleInput:
        """将请求转换为 ScheduleInput"""
        combined = [
            CombinedClass(
                class_set=cc["class_set"],
                teacher_id=cc["teacher_id"],
                subject=cc["subject"],
                room_type=cc.get("room_type", "普通")
            ) for cc in self.combined_classes
        ]
        special = {k: v for k, v in self.special_rooms.items()}
        unavail = {
            k: set(v) for k, v in self.teacher_unavailability.items()
        }
        return ScheduleInput(
            school_id=self.school_id,
            timeslots=self.timeslots,
            classes=[ClassInfo(**c) for c in self.classes],
            teachers=[TeacherInfo(**t) for t in self.teachers],
            rooms=[RoomInfo(**r) for r in self.rooms],
            subjects=self.subjects,
            teacher_of=self.teacher_of,
            required_hours=self.required_hours,
            combined_classes=combined,
            special_rooms=special,
            teacher_unavailability=unavail
        )
