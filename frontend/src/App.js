import React, { useState, useEffect } from 'react';
import { Calendar, Users, Clock, BarChart3, Plus, Trash2, Edit, LogOut, User, Shield } from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('login');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedStore, setSelectedStore] = useState(null); // Selected store for viewing schedule
  const [stores, setStores] = useState([]); // Available stores
  const [schedule, setSchedule] = useState(null);
  const [users, setUsers] = useState([]);
  const [myShifts, setMyShifts] = useState({ shifts: [], stats: {} });
  const [loading, setLoading] = useState(false);

  const months = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ];

  const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    if (token && userData) {
      setUser(JSON.parse(userData));
      setCurrentView(JSON.parse(userData).role === 'manager' ? 'schedule' : 'my-schedule');
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchStores();
    }
  }, [user]);

  useEffect(() => {
    if (user && selectedStore) {
      fetchSchedule();
      if (user.role === 'manager') {
        fetchUsers();
      } else {
        fetchMyShifts();
      }
    }
  }, [user, selectedStore, selectedMonth, selectedYear]);

  const apiCall = async (endpoint, options = {}) => {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_URL}/api${endpoint}`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  };

  const login = async (email, password) => {
    try {
      setLoading(true);
      const response = await apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });

      localStorage.setItem('token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      setUser(response.user);
      setCurrentView(response.user.role === 'manager' ? 'schedule' : 'my-schedule');
    } catch (error) {
      alert('Ошибка входа: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setSelectedStore(null);
    setCurrentView('login');
  };

  const fetchStores = async () => {
    try {
      const response = await apiCall('/stores');
      setStores(response);
      // Auto-select first store if available
      if (response.length > 0 && !selectedStore) {
        setSelectedStore(response[0]);
      }
    } catch (error) {
      console.error('Error fetching stores:', error);
    }
  };

  const createStore = async (storeData) => {
    try {
      await apiCall('/stores', {
        method: 'POST',
        body: JSON.stringify(storeData)
      });
      fetchStores();
      alert('Точка продаж создана успешно');
    } catch (error) {
      alert('Ошибка создания: ' + error.message);
    }
  };

  const deleteStore = async (storeId) => {
    try {
      await apiCall(`/stores/${storeId}`, { method: 'DELETE' });
      fetchStores();
      // If deleted store was selected, select first available
      if (selectedStore?.id === storeId && stores.length > 1) {
        setSelectedStore(stores.find(s => s.id !== storeId));
      }
      alert('Точка продаж удалена');
    } catch (error) {
      alert('Ошибка удаления: ' + error.message);
    }
  };

  const fetchSchedule = async () => {
    if (!selectedStore) return;
    try {
      const response = await apiCall(`/schedules/${selectedStore.id}/${selectedYear}/${selectedMonth}`);
      setSchedule(response.schedule);
    } catch (error) {
      console.error('Error fetching schedule:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await apiCall('/users');
      setUsers(response.filter(u => u.role === 'employee'));
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const fetchMyShifts = async () => {
    if (!selectedStore) return;
    try {
      const response = await apiCall(`/my-shifts/${selectedStore.id}/${selectedYear}/${selectedMonth}`);
      setMyShifts(response);
    } catch (error) {
      console.error('Error fetching my shifts:', error);
    }
  };

  const createUser = async (userData) => {
    try {
      await apiCall('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData)
      });
      fetchUsers();
      alert('Сотрудник успешно создан');
    } catch (error) {
      alert('Ошибка создания: ' + error.message);
    }
  };

  const deleteUser = async (userId) => {
    try {
      await apiCall(`/users/${userId}`, { method: 'DELETE' });
      fetchUsers();
      alert('Сотрудник удален');
    } catch (error) {
      alert('Ошибка удаления: ' + error.message);
    }
  };

  const saveSchedule = async (days) => {
    if (!selectedStore) return;
    try {
      setLoading(true);
      await apiCall('/schedules', {
        method: 'POST',
        body: JSON.stringify({
          store_id: selectedStore.id,
          month: selectedMonth,
          year: selectedYear,
          days
        })
      });
      fetchSchedule();
      alert('Расписание сохранено');
    } catch (error) {
      alert('Ошибка сохранения: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getDaysInMonth = (month, year) => {
    return new Date(year, month, 0).getDate();
  };

  const getFirstDayOfMonth = (month, year) => {
    const firstDay = new Date(year, month - 1, 1).getDay();
    return firstDay === 0 ? 6 : firstDay - 1; // Convert to Monday = 0
  };

  const renderCalendarGrid = () => {
    const daysInMonth = getDaysInMonth(selectedMonth, selectedYear);
    const firstDay = getFirstDayOfMonth(selectedMonth, selectedYear);
    const days = [];

    // Empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
    }

    // Days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${selectedYear}-${selectedMonth.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      const daySchedule = schedule?.days?.find(d => d.date === dateStr);
      
      days.push(
        <div key={day} className="calendar-day">
          <div className="day-header">
            <span className="day-number">{day}</span>
            <span className="day-week">{weekDays[(firstDay + day - 1) % 7]}</span>
          </div>
          
          {/* Day Shift */}
          {daySchedule?.day_shift && (
            <div className="shift-info">
              <div className="shift-type shift-day">
                ☀️ День
              </div>
              <div className="shift-employees">
                {daySchedule.day_shift.assignments?.map((assignment, idx) => (
                  <div key={idx} className="employee-name">
                    {assignment.employee_name}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Night Shift */}
          {daySchedule?.night_shift && (
            <div className="shift-info">
              <div className="shift-type shift-night">
                🌙 Ночь
              </div>
              <div className="shift-employees">
                {daySchedule.night_shift.assignments?.map((assignment, idx) => (
                  <div key={idx} className="employee-name">
                    {assignment.employee_name}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {user?.role === 'manager' && (
            <button 
              className="edit-day-btn"
              onClick={() => editDayShift(dateStr)}
            >
              <Edit size={12} />
            </button>
          )}
        </div>
      );
    }

    return days;
  };

  const [editingDay, setEditingDay] = useState(null);
  const [dayShiftForm, setDayShiftForm] = useState({
    selectedEmployees: []
  });
  const [nightShiftForm, setNightShiftForm] = useState({
    selectedEmployees: []
  });

  const editDayShift = (dateStr) => {
    const daySchedule = schedule?.days?.find(d => d.date === dateStr);
    
    // Initialize day shift form
    setDayShiftForm({
      selectedEmployees: daySchedule?.day_shift?.assignments?.map(a => a.employee_id) || []
    });
    
    // Initialize night shift form  
    setNightShiftForm({
      selectedEmployees: daySchedule?.night_shift?.assignments?.map(a => a.employee_id) || []
    });
    
    setEditingDay(dateStr);
  };

  const saveShiftForm = () => {
    const dayAssignments = dayShiftForm.selectedEmployees.map(employeeId => {
      const user = users.find(u => u.id === employeeId);
      return { employee_id: employeeId, employee_name: user.name };
    });
    
    const nightAssignments = nightShiftForm.selectedEmployees.map(employeeId => {
      const user = users.find(u => u.id === employeeId);
      return { employee_id: employeeId, employee_name: user.name };
    });

    const updatedDays = [...(schedule?.days || [])];
    const existingIndex = updatedDays.findIndex(d => d.date === editingDay);

    const newDaySchedule = {
      date: editingDay,
      day_shift: dayAssignments.length > 0 ? {
        type: "day",
        assignments: dayAssignments,
        hours: null
      } : null,
      night_shift: nightAssignments.length > 0 ? {
        type: "night", 
        assignments: nightAssignments,
        hours: null
      } : null,
      custom_shifts: []
    };

    if (existingIndex >= 0) {
      if (dayAssignments.length === 0 && nightAssignments.length === 0) {
        updatedDays.splice(existingIndex, 1);
      } else {
        updatedDays[existingIndex] = newDaySchedule;
      }
    } else if (dayAssignments.length > 0 || nightAssignments.length > 0) {
      updatedDays.push(newDaySchedule);
    }

    saveSchedule(updatedDays);
    setEditingDay(null);
  };

  const cancelShiftForm = () => {
    setEditingDay(null);
    setDayShiftForm({ selectedEmployees: [] });
    setNightShiftForm({ selectedEmployees: [] });
  };

  if (!user) {
    return <LoginForm onLogin={login} loading={loading} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <Calendar className="logo-icon" />
            <span>График Смен</span>
          </div>
          <nav className="nav-menu">
            {user.role === 'manager' ? (
              <>
                <button 
                  className={currentView === 'schedule' ? 'nav-btn active' : 'nav-btn'}
                  onClick={() => setCurrentView('schedule')}
                >
                  <Calendar size={18} />
                  Расписание
                </button>
                <button 
                  className={currentView === 'users' ? 'nav-btn active' : 'nav-btn'}
                  onClick={() => setCurrentView('users')}
                >
                  <Users size={18} />
                  Сотрудники
                </button>
              </>
            ) : (
              <>
                <button 
                  className={currentView === 'my-schedule' ? 'nav-btn active' : 'nav-btn'}
                  onClick={() => setCurrentView('my-schedule')}
                >
                  <Calendar size={18} />
                  Мое расписание
                </button>
                <button 
                  className={currentView === 'stats' ? 'nav-btn active' : 'nav-btn'}
                  onClick={() => setCurrentView('stats')}
                >
                  <BarChart3 size={18} />
                  Статистика
                </button>
              </>
            )}
          </nav>
          <div className="user-menu">
            <div className="user-info">
              {user.role === 'manager' ? <Shield size={16} /> : <User size={16} />}
              <span>{user.name}</span>
            </div>
            <button className="logout-btn" onClick={logout}>
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        {(currentView === 'schedule' || currentView === 'my-schedule') && (
          <div className="schedule-container">
            <div className="schedule-header">
              <h2>
                {currentView === 'schedule' ? 'Управление расписанием' : 'Мое расписание'}
              </h2>
              <div className="month-selector">
                <select 
                  value={selectedMonth} 
                  onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                >
                  {months.map((month, idx) => (
                    <option key={idx} value={idx + 1}>{month}</option>
                  ))}
                </select>
                <select 
                  value={selectedYear} 
                  onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                >
                  {[2024, 2025, 2026].map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="calendar-grid">
              {renderCalendarGrid()}
            </div>

            {loading && <div className="loading">Загрузка...</div>}
            
            {editingDay && (
              <DayShiftEditForm
                date={editingDay}
                users={users}
                dayShiftForm={dayShiftForm}
                setDayShiftForm={setDayShiftForm}
                nightShiftForm={nightShiftForm}
                setNightShiftForm={setNightShiftForm}
                onSave={saveShiftForm}
                onCancel={cancelShiftForm}
              />
            )}
          </div>
        )}

        {currentView === 'users' && (
          <UsersManagement 
            users={users} 
            onCreateUser={createUser} 
            onDeleteUser={deleteUser} 
          />
        )}

        {currentView === 'stats' && (
          <StatsView stats={myShifts.stats} shifts={myShifts.shifts} />
        )}
      </main>
    </div>
  );
}

const LoginForm = ({ onLogin, loading }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(email, password);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <Calendar className="login-icon" />
          <h1>График Смен</h1>
          <p>Войдите в систему для управления расписанием</p>
        </div>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="manager@company.com"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="login-demo">
          <p><strong>Демо данные:</strong></p>
          <p>Менеджер: manager@company.com / manager123</p>
        </div>
      </div>
    </div>
  );
};

const DayShiftEditForm = ({ date, users, dayShiftForm, setDayShiftForm, nightShiftForm, setNightShiftForm, onSave, onCancel }) => {
  const toggleDayEmployee = (employeeId) => {
    const isSelected = dayShiftForm.selectedEmployees.includes(employeeId);
    if (isSelected) {
      setDayShiftForm({
        ...dayShiftForm,
        selectedEmployees: dayShiftForm.selectedEmployees.filter(id => id !== employeeId)
      });
    } else {
      setDayShiftForm({
        ...dayShiftForm,
        selectedEmployees: [...dayShiftForm.selectedEmployees, employeeId]
      });
    }
  };

  const toggleNightEmployee = (employeeId) => {
    const isSelected = nightShiftForm.selectedEmployees.includes(employeeId);
    if (isSelected) {
      setNightShiftForm({
        ...nightShiftForm,
        selectedEmployees: nightShiftForm.selectedEmployees.filter(id => id !== employeeId)
      });
    } else {
      setNightShiftForm({
        ...nightShiftForm,
        selectedEmployees: [...nightShiftForm.selectedEmployees, employeeId]
      });
    }
  };

  const formattedDate = new Date(date + 'T00:00:00').toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    weekday: 'long'
  });

  return (
    <div className="shift-edit-overlay">
      <div className="shift-edit-form">
        <h3>Редактирование смен</h3>
        <p className="edit-date">{formattedDate}</p>
        
        {/* Day Shift Section */}
        <div className="form-section">
          <label className="shift-section-label">
            ☀️ Дневная смена (12 часов)
          </label>
          <div className="employees-list">
            {users.map(user => (
              <div 
                key={user.id} 
                className={dayShiftForm.selectedEmployees.includes(user.id) ? 'employee-item selected' : 'employee-item'}
                onClick={() => toggleDayEmployee(user.id)}
              >
                <div className="employee-checkbox">
                  {dayShiftForm.selectedEmployees.includes(user.id) ? '✓' : ''}
                </div>
                <div className="employee-details">
                  <span className="employee-name">{user.name}</span>
                  <span className="employee-email">{user.email}</span>
                </div>
              </div>
            ))}
          </div>
          {users.length === 0 && (
            <p className="no-employees">Нет сотрудников. Создайте сотрудников на вкладке "Сотрудники".</p>
          )}
        </div>

        {/* Night Shift Section */}
        <div className="form-section">
          <label className="shift-section-label">
            🌙 Ночная смена (12 часов)
          </label>
          <div className="employees-list">
            {users.map(user => (
              <div 
                key={user.id} 
                className={nightShiftForm.selectedEmployees.includes(user.id) ? 'employee-item selected' : 'employee-item'}
                onClick={() => toggleNightEmployee(user.id)}
              >
                <div className="employee-checkbox">
                  {nightShiftForm.selectedEmployees.includes(user.id) ? '✓' : ''}
                </div>
                <div className="employee-details">
                  <span className="employee-name">{user.name}</span>
                  <span className="employee-email">{user.email}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="cancel-btn">
            Отмена
          </button>
          <button 
            type="button" 
            onClick={onSave} 
            className="save-btn"
          >
            Сохранить смены
          </button>
        </div>
      </div>
    </div>
  );
};

const ShiftEditForm = ({ date, users, shiftForm, setShiftForm, onSave, onCancel }) => {
  const toggleEmployee = (employeeId) => {
    const isSelected = shiftForm.selectedEmployees.includes(employeeId);
    if (isSelected) {
      setShiftForm({
        ...shiftForm,
        selectedEmployees: shiftForm.selectedEmployees.filter(id => id !== employeeId)
      });
    } else {
      setShiftForm({
        ...shiftForm,
        selectedEmployees: [...shiftForm.selectedEmployees, employeeId]
      });
    }
  };

  const formattedDate = new Date(date + 'T00:00:00').toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    weekday: 'long'
  });

  return (
    <div className="shift-edit-overlay">
      <div className="shift-edit-form">
        <h3>Редактирование смены</h3>
        <p className="edit-date">{formattedDate}</p>
        
        <div className="form-section">
          <label>Тип смены:</label>
          <div className="shift-type-buttons">
            <button 
              type="button"
              className={shiftForm.type === 'day' ? 'type-btn active' : 'type-btn'}
              onClick={() => setShiftForm({...shiftForm, type: 'day'})}
            >
              ☀️ День (12ч)
            </button>
            <button 
              type="button"
              className={shiftForm.type === 'night' ? 'type-btn active' : 'type-btn'}
              onClick={() => setShiftForm({...shiftForm, type: 'night'})}
            >
              🌙 Ночь (12ч)
            </button>
            <button 
              type="button"
              className={shiftForm.type === 'custom' ? 'type-btn active' : 'type-btn'}
              onClick={() => setShiftForm({...shiftForm, type: 'custom'})}
            >
              ⏰ Свои часы
            </button>
          </div>
        </div>

        {shiftForm.type === 'custom' && (
          <div className="form-section">
            <label>Количество часов:</label>
            <input
              type="number"
              min="1"
              max="24"
              value={shiftForm.hours || ''}
              onChange={(e) => setShiftForm({...shiftForm, hours: parseInt(e.target.value)})}
              placeholder="8"
            />
          </div>
        )}

        <div className="form-section">
          <label>Сотрудники на смене:</label>
          <div className="employees-list">
            {users.map(user => (
              <div 
                key={user.id} 
                className={shiftForm.selectedEmployees.includes(user.id) ? 'employee-item selected' : 'employee-item'}
                onClick={() => toggleEmployee(user.id)}
              >
                <div className="employee-checkbox">
                  {shiftForm.selectedEmployees.includes(user.id) ? '✓' : ''}
                </div>
                <div className="employee-details">
                  <span className="employee-name">{user.name}</span>
                  <span className="employee-email">{user.email}</span>
                </div>
              </div>
            ))}
          </div>
          {users.length === 0 && (
            <p className="no-employees">Нет сотрудников. Создайте сотрудников на вкладке "Сотрудники".</p>
          )}
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="cancel-btn">
            Отмена
          </button>
          <button 
            type="button" 
            onClick={onSave} 
            className="save-btn"
            disabled={shiftForm.type === 'custom' && !shiftForm.hours}
          >
            Сохранить смену
          </button>
        </div>
      </div>
    </div>
  );
};

const UsersManagement = ({ users, onCreateUser, onDeleteUser }) => {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreateUser({ ...formData, role: 'employee' });
    setFormData({ name: '', email: '', password: '' });
    setShowForm(false);
  };

  return (
    <div className="users-container">
      <div className="users-header">
        <h2>Управление сотрудниками</h2>
        <button className="add-user-btn" onClick={() => setShowForm(true)}>
          <Plus size={18} />
          Добавить сотрудника
        </button>
      </div>

      {showForm && (
        <div className="user-form-overlay">
          <div className="user-form">
            <h3>Новый сотрудник</h3>
            <form onSubmit={handleSubmit}>
              <input
                type="text"
                placeholder="Имя"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
              <input
                type="password"
                placeholder="Пароль"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required
              />
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)}>Отмена</button>
                <button type="submit">Создать</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="users-list">
        {users.map(user => (
          <div key={user.id} className="user-card">
            <div className="user-info">
              <User className="user-icon" />
              <div>
                <h4>{user.name}</h4>
                <p>{user.email}</p>
                <small>ID: {user.id}</small>
              </div>
            </div>
            <button 
              className="delete-user-btn"
              onClick={() => onDeleteUser(user.id)}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

const StatsView = ({ stats, shifts }) => {
  return (
    <div className="stats-container">
      <h2>Статистика за месяц</h2>
      
      <div className="stats-grid">
        <div className="stat-card">
          <Clock className="stat-icon" />
          <div className="stat-info">
            <h3>{stats.total_shifts || 0}</h3>
            <p>Всего смен</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">☀️</div>
          <div className="stat-info">
            <h3>{stats.day_shifts || 0}</h3>
            <p>Дневных смен</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">🌙</div>
          <div className="stat-info">
            <h3>{stats.night_shifts || 0}</h3>
            <p>Ночных смен</p>
          </div>
        </div>
        
        <div className="stat-card">
          <BarChart3 className="stat-icon" />
          <div className="stat-info">
            <h3>{stats.total_hours || 0}</h3>
            <p>Часов работы</p>
          </div>
        </div>
      </div>

      <div className="shifts-list">
        <h3>Мои смены</h3>
        {shifts.map((shift, idx) => (
          <div key={idx} className="shift-item">
            <div className="shift-date">{shift.date}</div>
            <div className={`shift-badge shift-${shift.type}`}>
              {shift.type === 'day' ? '☀️ День' : shift.type === 'night' ? '🌙 Ночь' : `⏰ ${shift.hours}ч`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;