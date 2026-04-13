import pytest
from fastapi.testclient import TestClient
from scheduler.src.main import app

client = TestClient(app)

def test_check_conflict_endpoint():
    response = client.post("/api/v1/schedule/check-conflict", json={
        "school_id": "test",
        "timeslots": ["day1_s1", "day1_s2"],
        "classes": [{"id": "c1", "name": "c1", "student_count": 45}],
        "teachers": [{"id": "t1", "name": "t1"}],
        "rooms": [{"id": "r1", "name": "r1", "capacity": 50, "room_type": "普通"}],
        "subjects": ["语文"],
        "teacher_of": {"c1": {"语文": "t1"}},
        "required_hours": {"c1": {"语文": 2}},
        "assignments": [
            {"class_id": "c1", "timeslot": "day1_s1", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "conflicts" in data

def test_modes_endpoint():
    response = client.get("/api/v1/schedule/modes")
    assert response.status_code == 200
    data = response.json()
    assert "modes" in data
    assert len(data["modes"]) == 3

def test_score_endpoint():
    response = client.post("/api/v1/schedule/score", json={
        "school_id": "test",
        "timeslots": ["day1_s1", "day1_s2"],
        "classes": [{"id": "c1", "name": "c1", "student_count": 45}],
        "teachers": [{"id": "t1", "name": "t1"}],
        "rooms": [{"id": "r1", "name": "r1", "capacity": 50, "room_type": "普通"}],
        "subjects": ["语文"],
        "teacher_of": {"c1": {"语文": "t1"}},
        "required_hours": {"c1": {"语文": 2}},
        "assignments": [
            {"class_id": "c1", "timeslot": "day1_s1", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
        ],
        "threshold": 60
    })
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "blocked" in data

def test_validate_endpoint():
    response = client.post("/api/v1/schedule/validate", json={
        "assignments": [{"class_id": "c1", "timeslot": "day1_s1"}],
        "required_hours": {"c1": {"语文": 2}}
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "missing" in data
