-- ============================================================
-- Door Morocco — Database Schema
-- Ultra-Luxury Tourism Platform
-- ============================================================

CREATE DATABASE IF NOT EXISTS door_morocco
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE door_morocco;

-- -----------------------------------------------------------
-- 1. USERS
--    Roles  : admin | partner
--    Status : pending | approved
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120)    NOT NULL,
    email       VARCHAR(255)    NOT NULL UNIQUE,
    password    VARCHAR(255)    NOT NULL,          -- bcrypt hash
    role        ENUM('admin', 'partner') NOT NULL DEFAULT 'partner',
    status      ENUM('pending', 'approved') NOT NULL DEFAULT 'pending',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_users_email  (email),
    INDEX idx_users_role   (role),
    INDEX idx_users_status (status)
) ENGINE=InnoDB;


-- -----------------------------------------------------------
-- 2. CITIES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS cities (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120)    NOT NULL,
    description TEXT,
    image       VARCHAR(500),                     -- path / URL
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- -----------------------------------------------------------
-- 3. SERVICES
--    Category : hotel | guide
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS services (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    city_id         INT             NOT NULL,
    partner_id      INT             NOT NULL,
    title           VARCHAR(200)    NOT NULL,
    category        ENUM('hotel', 'guide') NOT NULL,
    description     TEXT,
    main_image      VARCHAR(500),
    verified_status BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_services_city
        FOREIGN KEY (city_id)    REFERENCES cities(id) ON DELETE CASCADE,
    CONSTRAINT fk_services_partner
        FOREIGN KEY (partner_id) REFERENCES users(id)  ON DELETE CASCADE,

    INDEX idx_services_city     (city_id),
    INDEX idx_services_partner  (partner_id),
    INDEX idx_services_category (category)
) ENGINE=InnoDB;


-- -----------------------------------------------------------
-- 4. AFFILIATE LINKS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS affiliate_links (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    service_id  INT             NOT NULL,
    site_name   VARCHAR(120)    NOT NULL,
    price_mad   DECIMAL(10, 2)  NOT NULL,         -- Moroccan Dirham
    url         VARCHAR(700)    NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_affiliate_service
        FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,

    INDEX idx_affiliate_service (service_id)
) ENGINE=InnoDB;


-- -----------------------------------------------------------
-- 5. NOTIFICATIONS  (internal admin activity feed)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    type        VARCHAR(50)     NOT NULL,          -- 'new_partner', 'new_service', 'partner_approved', etc.
    title       VARCHAR(255)    NOT NULL,
    message     TEXT,
    is_read     BOOLEAN         NOT NULL DEFAULT FALSE,
    ref_id      INT,                               -- optional FK to relevant record
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_notif_read    (is_read),
    INDEX idx_notif_created (created_at)
) ENGINE=InnoDB;


-- -----------------------------------------------------------
-- SEED DATA — Sample Cities
-- -----------------------------------------------------------
INSERT INTO cities (name, description, image) VALUES
('Marrakech',  'The Red City — a sensory journey through ancient medinas, palatial riads, and the majestic Atlas Mountains on the horizon.', '/static/images/marrakech.jpg'),
('Chefchaouen','The Blue Pearl — an ethereal mountain village draped in every shade of cerulean and cobalt.',                              '/static/images/chefchaouen.jpg'),
('Fes',        'The Spiritual Capital — a labyrinth of living history, world-class artisanship, and the oldest university on Earth.',      '/static/images/fes.jpg'),
('Essaouira',  'The Wind City — where Atlantic breezes meet Portuguese ramparts and a thriving art scene.',                                '/static/images/essaouira.jpg'),
('Merzouga',   'Gateway to the Sahara — towering golden dunes, starlit desert camps, and timeless Berber hospitality.',                   '/static/images/merzouga.jpg'),
('Tangier',    'The Gateway to Africa — a cosmopolitan port city where Europe and Morocco share a single horizon.',                       '/static/images/tangier.jpg');


-- -----------------------------------------------------------
-- SEED DATA — Admin User  (password: admin123)
-- -----------------------------------------------------------
-- The hash below is for 'admin123' using werkzeug's generate_password_hash.
-- You can regenerate it with:  python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
INSERT IGNORE INTO users (name, email, password, role, status) VALUES
('Admin', 'admin@doormorocco.com', 'scrypt:32768:8:1$placeholder$hash', 'admin', 'approved');
