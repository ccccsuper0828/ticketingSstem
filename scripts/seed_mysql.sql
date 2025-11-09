-- MySQL seed script: fix missing columns and insert minimal usable data
-- Safe to run multiple times (uses IF NOT EXISTS / INSERT ... ON DUPLICATE KEY UPDATE)

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

-- 1) Ensure required tables exist (idempotent creates for new helper tables)
CREATE TABLE IF NOT EXISTS event_sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  sessiontime DATETIME NOT NULL,
  capacity INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ensure columns exist even if table pre-existed with different schema
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_sessions' AND COLUMN_NAME = 'event_id');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE event_sessions ADD COLUMN event_id INT NOT NULL', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_sessions' AND COLUMN_NAME = 'sessiontime');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE event_sessions ADD COLUMN sessiontime DATETIME NOT NULL DEFAULT NOW()', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_sessions' AND COLUMN_NAME = 'capacity');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE event_sessions ADD COLUMN capacity INT NOT NULL DEFAULT 0', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- If legacy column 'session_time' exists and is NOT NULL w/o default, relax it
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_sessions' AND COLUMN_NAME = 'session_time');
SET @ddl := IF(@col_exists=1, 'ALTER TABLE event_sessions MODIFY COLUMN session_time DATETIME NULL DEFAULT NOW()', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  eventid INT NOT NULL,
  section VARCHAR(50) NULL,
  `row` VARCHAR(20) NULL,
  `number` VARCHAR(20) NULL,
  status ENUM('available','locked','sold','disabled') NOT NULL DEFAULT 'available',
  locked_until DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ensure seats has event_id as well for compatibility
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'seats' AND COLUMN_NAME = 'event_id');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE seats ADD COLUMN event_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
CREATE TABLE IF NOT EXISTS ticket_inventory (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  ticket_type_id INT NOT NULL,
  price INT NOT NULL DEFAULT 0,
  total INT NOT NULL DEFAULT 0,
  available INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_inventory_session_ticket_type (session_id, ticket_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Patch existing ticket_types columns to match backend expectations
-- Conditionally add columns for broader MySQL compatibility
SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'eventid');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE ticket_types ADD COLUMN eventid INT NULL AFTER id', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Detect presence of legacy 'event_id' (we will branch inserts accordingly)
SET @has_tt_event_id := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'event_id');

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'available_stock');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE ticket_types ADD COLUMN available_stock INT NOT NULL DEFAULT 0', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'totalstock');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE ticket_types ADD COLUMN totalstock INT NOT NULL DEFAULT 0', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'createdat');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE ticket_types ADD COLUMN createdat DATETIME NULL DEFAULT CURRENT_TIMESTAMP', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ticket_types' AND COLUMN_NAME = 'updatedat');
SET @ddl := IF(@col_exists=0, 'ALTER TABLE ticket_types ADD COLUMN updatedat DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'SELECT 1');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 3) Admin and demo users
INSERT INTO users (username, email, password, role, avatar, credit, created_at, updated_at)
VALUES
  ('admin', 'admin@example.com', 'admin123', 'admin', 'https://avatarfiles.alphacoders.com/368/thumb-1920-368375.png', 100000, NOW(), NOW()),
  ('alice', 'alice@example.com', 'alice123', 'customer', 'https://avatarfiles.alphacoders.com/368/thumb-1920-368375.png', 5000, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  role=VALUES(role),
  credit=VALUES(credit);

-- Resolve admin id
SET @admin_id := (SELECT id FROM users WHERE username='admin' ORDER BY id ASC LIMIT 1);

-- 4) Event
INSERT INTO events (name, description, start_time, end_time, location, cover_image, status, created_by, created_at, updated_at)
VALUES
  ('Mock Concert', 'Demo event for seeding', DATE_ADD(NOW(), INTERVAL 1 DAY), NULL, 'Demo Hall', NULL, 'published', @admin_id, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  status=VALUES(status),
  updated_at=NOW();

-- Get event id (assumes name unique enough for seed)
SET @event_id := (SELECT id FROM events WHERE name='Mock Concert' ORDER BY id DESC LIMIT 1);

-- 5) Session (single)
INSERT INTO event_sessions (event_id, sessiontime, capacity, created_at)
VALUES (@event_id, DATE_ADD(NOW(), INTERVAL 1 DAY), 100, NOW());
-- Fetch back
SET @session_id := (SELECT id FROM event_sessions WHERE event_id=@event_id ORDER BY id DESC LIMIT 1);

-- 6) Ticket types (Standard / VIP) — support both schemas (eventid or event_id)
SET @sql := IF(@has_tt_event_id=1,
  CONCAT('INSERT IGNORE INTO ticket_types (event_id, name, price, totalstock, available_stock, description, createdat, updatedat) VALUES (',
         @event_id, ', \"Standard\", 100, 100, 100, \"Standard seat\", NOW(), NOW()), (',
         @event_id, ', \"VIP\", 200, 20, 20, \"VIP seat\", NOW(), NOW())'),
  CONCAT('INSERT IGNORE INTO ticket_types (eventid, name, price, totalstock, available_stock, description, createdat, updatedat) VALUES (',
         @event_id, ', \"Standard\", 100, 100, 100, \"Standard seat\", NOW(), NOW()), (',
         @event_id, ', \"VIP\", 200, 20, 20, \"VIP seat\", NOW(), NOW())')
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- IDs back (by name)
SET @tt_std_id := (SELECT id FROM ticket_types WHERE name='Standard' ORDER BY id DESC LIMIT 1);
SET @tt_vip_id := (SELECT id FROM ticket_types WHERE name='VIP' ORDER BY id DESC LIMIT 1);

-- 7) Inventory for session+type (use INSERT IGNORE to avoid duplicates)
INSERT IGNORE INTO ticket_inventory (session_id, ticket_type_id, price, total, available, created_at, updated_at)
VALUES
  (@session_id, @tt_std_id, 100, 100, 100, NOW(), NOW()),
  (@session_id, @tt_vip_id, 200, 20, 20, NOW(), NOW());

-- Skipping seats seeding due to varying schemas; optional to seed manually via admin UI.

SET FOREIGN_KEY_CHECKS=1;
-- Done


