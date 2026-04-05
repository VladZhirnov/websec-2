import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE_URL = "https://ssau.ru"


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Загружает страницу и возвращает BeautifulSoup объект"""
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        if response.status_code == 200:
            return BeautifulSoup(response.text, "html.parser")
        print(f"Ошибка {response.status_code} при загрузке {url}")
        return None
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None


def search_educational_groups(query: str) -> List[Dict]:
    """Поиск групп по названию"""
    query_lower = query.lower()
    groups_db = [
        {"id": "1213641978", "title": "6413-100503D"},
        {"id": "1282690301", "title": "6411-100503D"},
        {"id": "1282690279", "title": "6412-100503D"},
    ]
    
    matches = []
    for group in groups_db:
        if query_lower in group["title"].lower():
            matches.append({"value": group["id"], "label": group["title"]})
    
    return matches[:10]


def get_catalog_of_groups() -> List[Dict]:
    """Возвращает список доступных групп"""
    return [
        {"identifier": "1213641978", "full_name": "6413-100503D"},
        {"identifier": "1282690301", "full_name": "6411-100503D"},
        {"identifier": "1282690279", "full_name": "6412-100503D"},
    ]


def get_teaching_staff() -> List[Dict]:
    """Возвращает список преподавателей"""
    return [
        {"staff_id": "432837452", "fullname": "Юзькив Р.Р."},
        {"staff_id": "114869468", "fullname": "Сергеев А.В."},
        {"staff_id": "62061001", "fullname": "Мясников В.В."},
        {"staff_id": "594502705", "fullname": "Чернышев П.В."},
        {"staff_id": "335824546", "fullname": "Максимов А.И."},
        {"staff_id": "664017039", "fullname": "Борисов А.Н."},
        {"staff_id": "364272302", "fullname": "Агафонов А.А."},
        {"staff_id": "147619112", "fullname": "Кузнецов А.В."},
        {"staff_id": "333991624", "fullname": "Веричев А.В."},
        {"staff_id": "544973937", "fullname": "Шапиро Д.А."},
    ]


def fetch_timetable(target_type: str, entity_identifier: str, week_number: Optional[int] = None) -> Dict:
    """
    Получает расписание для группы или преподавателя
    target_type: 'group' или 'teacher'
    entity_identifier: ID группы или ID преподавателя
    """
    param_key = "groupId" if target_type == "group" else "staffId"
    query_params = {param_key: entity_identifier}
    
    if week_number is not None:
        query_params["selectedWeek"] = week_number

    url = f"{BASE_URL}/rasp?{'&'.join(f'{k}={v}' for k, v in query_params.items())}"
    soup = fetch_page(url)
    
    if not soup:
        return create_empty_timetable(week_number or 1)

    current_week = determine_current_week(soup, week_number)
    
    entity_title = extract_entity_title(soup, entity_identifier)
    
    week_days = parse_weekdays(soup)
    
    time_intervals = parse_time_slots(soup)
    
    lessons_grid = parse_lessons_grid(soup, len(week_days))
    
    while len(time_intervals) < len(lessons_grid):
        time_intervals.append("—")
    time_intervals = time_intervals[:len(lessons_grid)]

    return {
        "week": current_week,
        "entity_name": entity_title,
        "calendar_days": week_days,
        "time_intervals": time_intervals,
        "lessons_table": lessons_grid,
        "has_data": len(lessons_grid) > 0 and any(any(cell for cell in row) for row in lessons_grid)
    }


def determine_current_week(soup: BeautifulSoup, fallback_week: Optional[int]) -> int:
    """Определяет номер текущей недели из HTML"""
    week_indicator = soup.find('span', class_='week-nav-current_week')
    if week_indicator:
        week_text = week_indicator.get_text(strip=True)
        week_match = re.search(r'(\d+)', week_text)
        if week_match:
            return int(week_match.group(1))
    
    if fallback_week is not None:
        return fallback_week
    
    return calculate_academic_week()


def calculate_academic_week() -> int:
    """Вычисляет номер недели от 1 сентября"""
    today = datetime.now()
    academic_year_start = datetime(today.year, 9, 1)
    
    if today < academic_year_start:
        academic_year_start = datetime(today.year - 1, 9, 1)
    
    days_passed = (today - academic_year_start).days
    if days_passed < 0:
        return 1
    
    week_number = (days_passed // 7) + 1
    return max(1, min(week_number, 52))


def extract_entity_title(soup: BeautifulSoup, default_id: str) -> str:
    """Извлекает название группы или преподавателя"""
    title_element = soup.select_one('.info-block__title')
    if not title_element:
        title_element = soup.find('h1', class_='h1-text')
    
    if title_element:
        raw_title = title_element.get_text(strip=True)
        if 'Расписание,' in raw_title:
            return raw_title.replace('Расписание,', '').strip()
        return raw_title
    
    return f"Группа {default_id}"


def parse_weekdays(soup: BeautifulSoup) -> List[Dict]:
    """Парсит дни недели и даты"""
    days_list = []
    
    day_headers = soup.select('.schedule__head')
    for header in day_headers[1:]:
        weekday_elem = header.select_one('.schedule__head-weekday')
        date_elem = header.select_one('.schedule__head-date')
        
        if weekday_elem and date_elem:
            days_list.append({
                "name": weekday_elem.get_text(strip=True).capitalize(),
                "date": date_elem.get_text(strip=True)
            })
    
    if not days_list:
        standard_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        days_list = [{"name": day, "date": ""} for day in standard_days]
    
    return days_list[:7]


def parse_time_slots(soup: BeautifulSoup) -> List[str]:
    """Парсит временные интервалы занятий"""
    time_slots = []
    
    time_blocks = soup.select('.schedule__time')
    for block in time_blocks:
        time_items = block.select('.schedule__time-item')
        if len(time_items) >= 2:
            start_time = time_items[0].get_text(strip=True)
            end_time = time_items[1].get_text(strip=True)
            start_clean = re.sub(r'[^\d:]', '', start_time)[:5]
            end_clean = re.sub(r'[^\d:]', '', end_time)[:5]
            time_slots.append(f"{start_clean}–{end_clean}")
    
    return time_slots


def parse_lessons_grid(soup: BeautifulSoup, days_count: int) -> List[List[Optional[List[Dict]]]]:
    """Парсит сетку занятий"""
    all_lesson_cells = []
    
    for container in soup.select('.schedule__item'):
        if 'schedule__head' in (container.get('class') or []):
            continue
        
        lesson_blocks = container.select('.schedule__lesson')
        cell_content = []
        
        for lesson in lesson_blocks:
            lesson_info = extract_lesson_details(lesson)
            if lesson_info and lesson_info.get("subject"):
                cell_content.append(lesson_info)
        
        all_lesson_cells.append(cell_content if cell_content else None)
    
    if days_count == 0:
        days_count = 6
    
    lessons_matrix = []
    for idx in range(0, len(all_lesson_cells), days_count):
        row = all_lesson_cells[idx:idx + days_count]
        while len(row) < days_count:
            row.append(None)
        lessons_matrix.append(row)
    
    return lessons_matrix


def extract_lesson_details(lesson_element) -> Optional[Dict]:
    """Извлекает детали одного занятия"""
    type_badge = lesson_element.select_one('.schedule__lesson-type-chip')
    lesson_type = type_badge.get_text(strip=True) if type_badge else ""
    
    subject_elem = lesson_element.select_one('.schedule__discipline')
    subject = subject_elem.get_text(strip=True) if subject_elem else ""
    
    if not subject:
        return None
    
    room_elem = lesson_element.select_one('.schedule__place')
    classroom = room_elem.get_text(strip=True) if room_elem else "online"
    
    teacher_elem = lesson_element.select_one('.schedule__teacher')
    instructor = teacher_elem.get_text(strip=True) if teacher_elem else ""
    
    groups_block = lesson_element.select_one('.schedule__groups')
    subgroup_info = ""
    group_list = ""
    
    if groups_block:
  
        subgroup_span = groups_block.select_one('span.caption-text')
        if subgroup_span:
            subgroup_text = subgroup_span.get_text(strip=True)
            if "подгрупп" in subgroup_text.lower() or "Подгрупп" in subgroup_text:
                subgroup_info = subgroup_text
        
        if not subgroup_info:
            groups_text = groups_block.get_text(strip=True)
            if "подгрупп" in groups_text.lower():
                subgroup_info = groups_text
        
        group_links = groups_block.select('a.schedule__group')
        if group_links:
            group_names = [link.get_text(strip=True) for link in group_links]
            group_list = ", ".join(group_names)
    
    return {
        "subject": subject,
        "type": lesson_type,
        "teacher": instructor,
        "room": classroom,
        "subgroup": subgroup_info,  
        "groups": group_list
    }


def fetch_group_details(group_id: str) -> Dict:
    """Получает подробную информацию о группе"""
    soup = fetch_page(f"{BASE_URL}/rasp?groupId={group_id}")
    
    if not soup:
        return {
            "id": group_id,
            "name": f"Группа {group_id}",
            "specialty": "",
            "study_format": "Очная"
        }
    
    name_element = soup.select_one('.info-block__title')
    group_name = ""
    if name_element:
        raw = name_element.get_text(strip=True)
        group_name = raw.replace('Расписание,', '').strip()
    
    if not group_name:
        group_name = f"Группа {group_id}"
    
    description_block = soup.select_one('.info-block__description')
    specialty = ""
    study_format = "Очная форма обучения"
    
    if description_block:
        paragraphs = description_block.find_all('div')
        if len(paragraphs) > 0:
            specialty = paragraphs[0].get_text(strip=True)
        if len(paragraphs) > 1:
            study_format = paragraphs[1].get_text(strip=True)
    
    return {
        "id": group_id,
        "name": group_name,
        "specialty": specialty,
        "study_format": study_format
    }


def search_teachers(query: str) -> List[Dict]:
    """Поиск преподавателей по имени"""
    query_lower = query.lower()
    teachers_db = get_teaching_staff()
    
    matches = []
    for teacher in teachers_db:
        if query_lower in teacher["fullname"].lower():
            matches.append({"value": teacher["staff_id"], "label": teacher["fullname"]})
    
    return matches


def create_empty_timetable(week: int) -> Dict:
    """Создаёт пустое расписание"""
    return {
        "week": week,
        "entity_name": "",
        "calendar_days": [],
        "time_intervals": [],
        "lessons_table": [],
        "has_data": False
    }