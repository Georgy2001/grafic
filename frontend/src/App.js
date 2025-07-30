import React, { useState, useEffect } from 'react';
import { Calendar, Users, Clock, BarChart3, Plus, Trash2, Edit, LogOut, User, Shield } from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('login');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
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
      fetchSchedule();
      if (user.role === 'manager') {
        fetchUsers();
      } else {
        fetchMyShifts();
      }
    }
  }, [user, selectedMonth, selectedYear]);

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
    setCurrentView('login');
  };

  const fetchSchedule = async () => {
    try {
      const response = await apiCall(`/schedules/${selectedYear}/${selectedMonth}`);
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
    try {
      const response = await apiCall(`/my-shifts/${selectedYear}/${selectedMonth}`);
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

  const saveSchedule = async (shifts) => {
    try {
      setLoading(true);
      await apiCall('/schedules', {
        method: 'POST',
        body: JSON.stringify({
          month: selectedMonth,
          year: selectedYear,
          shifts
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
      const dayShift = schedule?.shifts?.find(s => s.date === dateStr);
      
      days.push(
        <div key={day} className="calendar-day">
          <div className="day-header">
            <span className="day-number">{day}</span>
            <span className="day-week">{weekDays[(firstDay + day - 1) % 7]}</span>
          </div>
          {dayShift && (
            <div className="shift-info">
              <div className={`shift-type shift-${dayShift.type}`}>
                {dayShift.type === 'day' ? '☀️ День' : dayShift.type === 'night' ? '🌙 Ночь' : '⏰ ' + dayShift.hours + 'ч'}
              </div>
              <div className="shift-employees">
                {dayShift.assignments?.map((assignment, idx) => (
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

  const editDayShift = (dateStr) => {
    const dayShift = schedule?.shifts?.find(s => s.date === dateStr) || {
      date: dateStr,
      type: 'day',
      assignments: [],
      hours: null
    };

    const newType = prompt('Тип смены (day/night/custom):', dayShift.type);
    if (!newType) return;

    let hours = null;
    if (newType === 'custom') {
      hours = parseInt(prompt('Количество часов:', dayShift.hours || 8));
      if (!hours) return;
    }

    const employeeIds = prompt(
      'ID сотрудников через запятую:\n' + users.map(u => `${u.id}: ${u.name}`).join('\n'),
      dayShift.assignments?.map(a => a.employee_id).join(',') || ''
    );

    if (employeeIds === null) return;

    const assignments = employeeIds
      .split(',')
      .map(id => id.trim())
      .filter(id => id)
      .map(id => {
        const user = users.find(u => u.id === id);
        return user ? { employee_id: id, employee_name: user.name } : null;
      })
      .filter(Boolean);

    const updatedShifts = [...(schedule?.shifts || [])];
    const existingIndex = updatedShifts.findIndex(s => s.date === dateStr);

    const newShift = {
      date: dateStr,
      type: newType,
      assignments,
      hours: newType === 'custom' ? hours : null
    };

    if (existingIndex >= 0) {
      if (assignments.length === 0) {
        updatedShifts.splice(existingIndex, 1);
      } else {
        updatedShifts[existingIndex] = newShift;
      }
    } else if (assignments.length > 0) {
      updatedShifts.push(newShift);
    }

    saveSchedule(updatedShifts);
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