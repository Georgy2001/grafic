# График Смен - Deployment Guide

Система управления графиками смен с расширенной функциональностью заработка.

## 🚀 Быстрый старт

### Требования
- Docker и Docker Compose
- 2GB RAM минимум
- 10GB свободного места

### Локальная разработка
```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd shift-scheduler

# Запустите в режиме разработки
docker-compose up -d

# Приложение будет доступно по адресам:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8001
# MongoDB: localhost:27017
```

### Продакшн развертывание
```bash
# 1. Настройте окружение
cp .env.example .env
# Отредактируйте .env файл со своими настройками

# 2. Запустите скрипт развертывания
./deploy.sh

# Приложение будет доступно на вашем домене
```

## 🔧 Конфигурация

### Environment Variables (.env)
```bash
# Database
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=your-strong-password

# Security
JWT_SECRET_KEY=your-super-secret-key-32-chars-min

# Domain
BACKEND_URL=https://yourdomain.com
DOMAIN=yourdomain.com
```

### SSL Certificates
Разместите ваши SSL сертификаты в `nginx/ssl/`:
- `cert.pem` - SSL сертификат
- `key.pem` - Приватный ключ

Для тестирования скрипт создаст самоподписанные сертификаты.

## 🌐 Поддерживаемые хостинги

### VPS/Dedicated серверы
- **DigitalOcean** - рекомендуется Droplet от $12/месяц
- **AWS EC2** - t3.small или больше
- **Google Cloud** - e2-small или больше
- **Hetzner** - CX21 или больше
- **Vultr** - High Performance от $12/месяц

### Платформы как сервис
- **Railway** - поддерживает Docker Compose
- **Render** - требует отдельные сервисы
- **Fly.io** - поддерживает Docker
- **Heroku** - с дополнительными настройками

### Облачные платформы
- **AWS ECS/EKS**
- **Google Cloud Run**
- **Azure Container Instances**

## 📋 Инструкции по хостингам

### DigitalOcean Droplet
```bash
# 1. Создайте Droplet (Ubuntu 22.04, 2GB RAM)
# 2. Подключитесь по SSH
ssh root@your-server-ip

# 3. Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Склонируйте код и развертывайте
git clone <your-repo>
cd shift-scheduler
cp .env.example .env
# Отредактируйте .env
./deploy.sh
```

### Railway
```bash
# 1. Подключите GitHub репозиторий
# 2. Railway автоматически обнаружит docker-compose.yml
# 3. Настройте переменные окружения через панель Railway
# 4. Развертывание произойдет автоматически
```

### AWS EC2
```bash
# 1. Запустите t3.small instance с Ubuntu 22.04
# 2. Настройте Security Group (порты 80, 443, 22)
# 3. Подключитесь и установите Docker (как выше)
# 4. Настройте Route 53 для домена
# 5. Получите SSL сертификат через Let's Encrypt:
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
# Скопируйте сертификаты в nginx/ssl/
```

## 🔒 Безопасность

### Обязательные настройки
- Измените пароли по умолчанию
- Используйте сильный JWT_SECRET_KEY
- Настройте SSL сертификаты
- Настройте файрвол
- Регулярно обновляйте систему

### Firewall (UFW)
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## 📊 Мониторинг

### Просмотр логов
```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Отдельный сервис
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Статус сервисов
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Ресурсы
```bash
docker stats
```

## 🔄 Обновление

```bash
# 1. Получите новый код
git pull origin main

# 2. Пересоберите и перезапустите
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

## 🆘 Troubleshooting

### Частые проблемы

**Порты заняты**
```bash
sudo lsof -i :80
sudo lsof -i :443
# Остановите конфликтующие сервисы
```

**SSL ошибки**
```bash
# Проверьте сертификаты
openssl x509 -in nginx/ssl/cert.pem -text -noout
```

**База данных не подключается**
```bash
# Проверьте логи MongoDB
docker-compose -f docker-compose.prod.yml logs mongodb
```

**Backend недоступен**
```bash
# Проверьте health endpoint
curl http://localhost:8001/api/health
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сервисов
2. Убедитесь, что все переменные окружения настроены
3. Проверьте доступность портов
4. Проверьте SSL сертификаты

## 🏗️ Архитектура

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Nginx     │────│  Frontend   │    │   Backend   │
│  (Proxy)    │    │  (React)    │────│  (FastAPI)  │
└─────────────┘    └─────────────┘    └─────────────┘
                                               │
                                      ┌─────────────┐
                                      │   MongoDB   │
                                      │ (Database)  │
                                      └─────────────┘
```

- **Nginx**: Реверс-прокси, SSL терминация, статические файлы
- **Frontend**: React SPA с Tailwind CSS
- **Backend**: FastAPI с JWT аутентификацией  
- **Database**: MongoDB для хранения данных

## 🎯 Функциональность

- ✅ Управление графиками смен
- ✅ Система заработка сотрудников
- ✅ Управление магазинами/точками продаж
- ✅ Аутентификация и авторизация
- ✅ Адаптивный интерфейс
- ✅ API для интеграций