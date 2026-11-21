CREATE DATABASE IF NOT EXISTS korochki_pm09 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE korochki_pm09;

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE application_statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(40) NOT NULL
);

CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(8,2) NOT NULL,
    duration_min INT NOT NULL,
    img_color VARCHAR(20) DEFAULT '#6b4c4f'
);

CREATE TABLE stylists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    specialization VARCHAR(100) NOT NULL
);

CREATE TABLE applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    service_id INT NOT NULL,
    stylist_id INT NOT NULL,
    status_id INT NOT NULL DEFAULT 1,
    start_date DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (stylist_id) REFERENCES stylists(id),
    FOREIGN KEY (status_id) REFERENCES application_statuses(id)
);

-- Индексы оптимизации (Раздел 2.2 и 4.1)
CREATE INDEX idx_apps_user_created ON applications (user_id, created_at DESC);
CREATE INDEX idx_apps_status_created ON applications (status_id, created_at DESC);
CREATE INDEX idx_services_cat_price ON services (category, price);

INSERT INTO roles (id, name) VALUES (1, 'admin'), (2, 'operator'), (3, 'user');
INSERT INTO application_statuses (id, name) VALUES (1, 'Новая'), (2, 'В работе'), (3, 'Выполнена'), (4, 'Отменена');

INSERT INTO users (login, password_hash, full_name, role_id) VALUES
('Admin', SHA2('KorokNET', 256), 'Соколова Елена (Админ)', 1),
('operator1', SHA2('Oper1234', 256), 'Морозов Дмитрий (Оператор)', 2),
('testuser', SHA2('qazqaz123', 256), 'Петрухина Мария Викторовна', 3);

INSERT INTO stylists (full_name, specialization) VALUES
('Лебедева Кристина', 'Топ-стилист, колорист'),
('Орлов Максим', 'Барбер, мужские стрижки'),
('Новикова Дарья', 'Стилист-универсал');

INSERT INTO services (name, category, price, duration_min, img_color) VALUES
('Женская модельная стрижка', 'Стрижки', 1800.00, 60, '#5a3d40'),
('Мужская стрижка и укладка', 'Стрижки', 1200.00, 45, '#3b4d5e'),
('Сложное окрашивание AirTouch', 'Окрашивание', 5500.00, 180, '#7a4b58'),
('Окрашивание в один тон', 'Окрашивание', 3200.00, 90, '#6c4f3d'),
('Вечерняя укладка у топ-стилиста', 'Укладки', 2500.00, 60, '#4f5d4e'),
('Экспресс-укладка локоны', 'Укладки', 1600.00, 40, '#6e5773'),
('Спа-восстановление волос', 'Уход', 2100.00, 50, '#3e635b'),
('Кератиновое выпрямление', 'Уход', 4800.00, 150, '#785a3c'),
('Детская стрижка', 'Стрижки', 900.00, 30, '#4a607a');

INSERT INTO applications (user_id, service_id, stylist_id, status_id, start_date) VALUES
(3, 3, 1, 1, '2026-07-22 14:00:00'),
(3, 1, 3, 3, '2026-07-15 11:00:00'),
(3, 7, 1, 2, '2026-07-25 16:30:00');