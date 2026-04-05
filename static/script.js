let currentGroupId = null;
let activeWeek = null;
let searchDebounceTimer = null;

const $searchInput = $('#groupSearch');
const $searchResults = $('#searchResults');
const $groupInfo = $('#groupInfo');
const $groupName = $('#groupName');
const $groupSpecialty = $('#groupSpecialty');
const $groupStudyForm = $('#groupStudyForm');
const $scheduleDesktop = $('#scheduleContainer');
const $scheduleMobile = $('#mobileScheduleContainer');
const $emptyState = $('#emptyState');
const $weekNumber = $('#weekNumber');
const $weekDate = $('#weekDate');
const $prevWeekBtn = $('#prevWeek');
const $nextWeekBtn = $('#nextWeek');
const $currentWeekBtn = $('#currentWeekBtn');

const API = {
    search: (q) => `/api/schedule/search?query=${encodeURIComponent(q)}`,
    groupInfo: (id) => `/api/schedule/group/${id}/info`,
    schedule: (id, week) => `/api/schedule/group/${id}${week ? `?week=${week}` : ''}`,
    currentWeek: '/api/schedule/current-week'
};

$(document).ready(function() {
    loadCurrentWeek();
    attachEventListeners();
    showEmptyState();
});

function attachEventListeners() {
    $searchInput.on('input', handleSearchInput);
    $(document).on('click', handleOutsideClick);
    $prevWeekBtn.on('click', () => navigateWeek(-1));
    $nextWeekBtn.on('click', () => navigateWeek(1));
    $currentWeekBtn.on('click', loadCurrentWeekAndRefresh);
}

async function performSearch(query) {
    if (query.length < 2) {
        $searchResults.removeClass('show').empty();
        return;
    }
    
    try {
        const response = await fetch(API.search(query));
        const result = await response.json();
        
        if (!result.success || !result.data.length) {
            $searchResults.html('<div class="search-result-item">Ничего не найдено</div>').addClass('show');
            return;
        }
        
        renderSearchResults(result.data);
        $searchResults.addClass('show');
    } catch (error) {
        console.error('Ошибка поиска:', error);
        $searchResults.html('<div class="search-result-item" style="color:#ef4444;">Ошибка поиска</div>').addClass('show');
    }
}

function renderSearchResults(items) {
    $searchResults.empty();
    
    items.forEach(item => {
        const $item = $(`
            <div class="search-result-item" data-id="${item.value}" data-name="${item.label}">
                <strong>${escapeHtml(item.label)}</strong>
            </div>
        `);
        $item.on('click', () => selectGroup(item.value, item.label));
        $searchResults.append($item);
    });
}

async function selectGroup(groupId, groupName) {
    $searchInput.val(groupName);
    $searchResults.removeClass('show').empty();
    currentGroupId = groupId;
    
    await loadGroupInformation(groupId);
    await loadTimetable(groupId, activeWeek);
}

async function loadGroupInformation(groupId) {
    try {
        const response = await fetch(API.groupInfo(groupId));
        const result = await response.json();
        
        if (result.success && result.data) {
            const info = result.data;
            $groupName.text(info.name || groupId);
            $groupSpecialty.text(info.specialty || '');
            $groupStudyForm.text(info.study_format || 'Очная форма');
            $groupInfo.show();
        }
    } catch (error) {
        console.error('Ошибка загрузки информации:', error);
    }
}

async function loadTimetable(groupId, week) {
    if (!groupId) {
        showEmptyState();
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(API.schedule(groupId, week));
        const result = await response.json();
        
        if (!result.success) {
            throw new Error('Ошибка загрузки');
        }
        
        const timetable = result.data;
        activeWeek = timetable.week;
        
        updateWeekDisplay(timetable.week, '');
        
        if (timetable.has_data && timetable.lessons_table && timetable.lessons_table.length) {
            renderDesktopTimetable(timetable);
            renderMobileTimetable(timetable);
            $emptyState.hide();
        } else {
            renderEmptyTimetable();
        }
    } catch (error) {
        console.error('Ошибка расписания:', error);
        showError('Не удалось загрузить расписание');
    }
}

function renderDesktopTimetable(timetable) {
    const { calendar_days, time_intervals, lessons_table } = timetable;
    
    if (!calendar_days.length || !lessons_table.length) {
        renderEmptyTimetable();
        return;
    }
    
    let html = '<table class="schedule-table"><thead><tr><th>Время</th>';
    
    calendar_days.forEach(day => {
        html += `<th><div class="weekday">${escapeHtml(day.name)}</div><div class="date">${escapeHtml(day.date)}</div></th>`;
    });
    html += '</tr></thead><tbody>';
    
    for (let rowIdx = 0; rowIdx < lessons_table.length; rowIdx++) {
        const row = lessons_table[rowIdx];
        const timeSlot = rowIdx < time_intervals.length ? time_intervals[rowIdx] : '—';
        
        html += '<tr>';
        html += `<td class="time-cell">${escapeHtml(timeSlot)}</td>`;
        
        for (let colIdx = 0; colIdx < calendar_days.length; colIdx++) {
            const cell = colIdx < row.length ? row[colIdx] : null;
            
            if (cell && cell.length) {
                html += '<td class="lesson-cell">';
                cell.forEach(lesson => {
                    const typeClass = getTypeClass(lesson.type);
                    html += `
                        <div class="lesson-item">
                            <span class="lesson-type ${typeClass}">${escapeHtml(lesson.type || 'Занятие')}</span>
                            <div class="lesson-discipline">${escapeHtml(lesson.subject)}</div>
                            <div class="lesson-place">${escapeHtml(lesson.room)}</div>
                            <div class="lesson-teacher">${escapeHtml(lesson.teacher || '—')}</div>
                    `;
                    
                    if (lesson.subgroup && lesson.subgroup.trim()) {
                        html += `<div class="lesson-subgroup">${escapeHtml(lesson.subgroup)}</div>`;
                    }
                    
                    if (lesson.groups && lesson.groups.trim()) {
                        html += `<div class="lesson-groups">${escapeHtml(lesson.groups)}</div>`;
                    }
                    
                    html += `</div>`;
                });
                html += '</td>';
            } else {
                html += '<td class="empty-lesson">—</td>';
            }
        }
        html += '</tr>';
    }
    
    html += '</tbody></table>';
    $scheduleDesktop.html(html);
}

function renderMobileTimetable(timetable) {
    const { calendar_days, time_intervals, lessons_table } = timetable;
    
    if (!calendar_days.length) {
        $scheduleMobile.html('<div class="empty-lesson">Нет данных</div>');
        return;
    }
    
    let html = '';
    
    for (let dayIdx = 0; dayIdx < calendar_days.length; dayIdx++) {
        const day = calendar_days[dayIdx];
        
        html += `
            <div class="mobile-day-card">
                <div class="mobile-day-header">
                    <div class="weekday">${escapeHtml(day.name)}</div>
                    <div class="date">${escapeHtml(day.date)}</div>
                </div>
        `;
        
        let hasLessons = false;
        
        for (let rowIdx = 0; rowIdx < lessons_table.length; rowIdx++) {
            const row = lessons_table[rowIdx];
            const cell = dayIdx < row.length ? row[dayIdx] : null;
            const timeSlot = rowIdx < time_intervals.length ? time_intervals[rowIdx] : '—';
            
            if (cell && cell.length) {
                hasLessons = true;
                html += `
                    <div class="mobile-time-slot">
                        <div class="mobile-time">${escapeHtml(timeSlot)}</div>
                        <div class="mobile-lessons">
                `;
                
                cell.forEach(lesson => {
                    const typeClass = getTypeClass(lesson.type);
                    html += `
                        <div class="mobile-lesson">
                            <span class="lesson-type ${typeClass}">${escapeHtml(lesson.type || 'Занятие')}</span>
                            <div class="lesson-discipline">${escapeHtml(lesson.subject)}</div>
                            <div class="lesson-place">${escapeHtml(lesson.room)}</div>
                            <div class="lesson-teacher">${escapeHtml(lesson.teacher || '—')}</div>
                    `;
                    
                    if (lesson.subgroup && lesson.subgroup.trim()) {
                        html += `<div class="lesson-subgroup">👥 ${escapeHtml(lesson.subgroup)}</div>`;
                    }
                    
                    if (lesson.groups && lesson.groups.trim()) {
                        html += `<div class="lesson-groups">${escapeHtml(lesson.groups)}</div>`;
                    }
                    
                    html += `</div>`;
                });
                
                html += `</div></div>`;
            }
        }
        
        if (!hasLessons) {
            html += `<div class="mobile-time-slot"><div class="mobile-lessons"><div class="mobile-lesson" style="text-align:center;color:#94a3b8;">Нет занятий</div></div></div>`;
        }
        
        html += '</div>';
    }
    
    $scheduleMobile.html(html);
}

function getTypeClass(type) {
    const t = (type || '').toLowerCase();
    if (t.includes('лекц')) return 'type-lecture';
    if (t.includes('практ')) return 'type-practice';
    if (t.includes('лабор')) return 'type-lab';
    if (t.includes('экзам')) return 'type-exam';
    if (t.includes('зачёт') || t.includes('зачет')) return 'type-credit';
    return 'type-other';
}

function navigateWeek(delta) {
    if (!currentGroupId) {
        showError('Сначала выберите группу');
        return;
    }
    
    let newWeek = (activeWeek || 1) + delta;
    if (newWeek < 1) newWeek = 52;
    if (newWeek > 52) newWeek = 1;
    
    loadTimetable(currentGroupId, newWeek);
}

async function loadCurrentWeek() {
    try {
        const response = await fetch(API.currentWeek);
        const data = await response.json();
        activeWeek = data.week;
        $weekNumber.text(`Неделя ${activeWeek}`);
    } catch (error) {
        console.error('Ошибка загрузки недели:', error);
        activeWeek = 1;
        $weekNumber.text('Неделя 1');
    }
}

async function loadCurrentWeekAndRefresh() {
    await loadCurrentWeek();
    if (currentGroupId) {
        await loadTimetable(currentGroupId, activeWeek);
    }
}

function updateWeekDisplay(week, date) {
    $weekNumber.text(`Неделя ${week}`);
    if (date) $weekDate.text(date);
}

function handleSearchInput() {
    const query = $searchInput.val().trim();
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => performSearch(query), 400);
}

function handleOutsideClick(e) {
    if (!$(e.target).closest('.search-input-group').length) {
        $searchResults.removeClass('show');
    }
}

function showLoading() {
    const loader = '<div class="loading"><div class="spinner"></div><p>Загрузка расписания...</p></div>';
    $scheduleDesktop.html(loader);
    $scheduleMobile.html(loader);
}

function showEmptyState() {
    $emptyState.show();
    $groupInfo.hide();
    $scheduleDesktop.html('');
    $scheduleMobile.html('');
}

function showError(msg) {
    const errorHtml = `<div class="loading"><p style="color:#ef4444;">${escapeHtml(msg)}</p></div>`;
    $scheduleDesktop.html(errorHtml);
    $scheduleMobile.html(errorHtml);
    $emptyState.hide();
}

function renderEmptyTimetable() {
    const empty = '<div class="empty-lesson" style="text-align:center;padding:40px;">Нет занятий на эту неделю</div>';
    $scheduleDesktop.html(empty);
    $scheduleMobile.html(empty);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}