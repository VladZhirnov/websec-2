from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Optional
import os

from parser import (
    search_educational_groups,
    get_catalog_of_groups,
    get_teaching_staff,
    fetch_timetable,
    fetch_group_details,
    calculate_academic_week
)

app = FastAPI(title="University Schedule API", description="API для получения расписания СГАУ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/schedule/search")
async def search_schedule(query: str = Query(..., min_length=1, description="Поисковый запрос")):
    """Поиск групп по названию"""
    results = search_educational_groups(query)
    return {"success": True, "data": results}


@app.get("/api/schedule/groups")
async def get_groups_list():
    """Получить список всех групп"""
    groups = get_catalog_of_groups()
    return {"success": True, "data": groups}


@app.get("/api/schedule/teachers")
async def get_teachers_list():
    """Получить список преподавателей"""
    teachers = get_teaching_staff()
    return {"success": True, "data": teachers}


@app.get("/api/schedule/group/{group_id}")
async def get_group_schedule(group_id: str, week: Optional[int] = None):
    """Получить расписание группы"""
    schedule = fetch_timetable("group", group_id, week)
    return {"success": True, "data": schedule}


@app.get("/api/schedule/teacher/{staff_id}")
async def get_teacher_schedule(staff_id: str, week: Optional[int] = None):
    """Получить расписание преподавателя"""
    schedule = fetch_timetable("teacher", staff_id, week)
    return {"success": True, "data": schedule}


@app.get("/api/schedule/group/{group_id}/info")
async def get_group_information(group_id: str):
    """Получить информацию о группе"""
    info = fetch_group_details(group_id)
    return {"success": True, "data": info}


@app.get("/api/schedule/current-week")
async def get_current_week_number():
    """Получить номер текущей учебной недели"""
    week = calculate_academic_week()
    return {"success": True, "week": week}


static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Отдать главную страницу"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Schedule App</h1><p>Frontend not found</p>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)