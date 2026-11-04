-- Source requests and normalized 3NF schema in cs528_hw6.
CREATE TABLE IF NOT EXISTS requests_source (
 request_id BIGINT PRIMARY KEY, request_time DATETIME(6) NOT NULL,
 country VARCHAR(100), client_ip VARCHAR(45), gender VARCHAR(30),
 age VARCHAR(20), income VARCHAR(100), is_banned BOOLEAN NOT NULL,
 time_of_day VARCHAR(50), requested_file VARCHAR(1024), http_status SMALLINT
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS countries (
 country_id INT AUTO_INCREMENT PRIMARY KEY,
 country_name VARCHAR(100) NOT NULL UNIQUE, is_banned BOOLEAN NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS clients (
 client_id INT AUTO_INCREMENT PRIMARY KEY, client_ip VARCHAR(45) NOT NULL UNIQUE,
 country_id INT NOT NULL, FOREIGN KEY(country_id) REFERENCES countries(country_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS requests (
 request_id BIGINT PRIMARY KEY, request_time DATETIME(6) NOT NULL,
 client_id INT NOT NULL, gender VARCHAR(30), age VARCHAR(20), income VARCHAR(100),
 time_of_day VARCHAR(50), requested_file VARCHAR(1024), http_status SMALLINT,
 FOREIGN KEY(client_id) REFERENCES clients(client_id)
) ENGINE=InnoDB;
START TRANSACTION;
INSERT INTO countries(country_name,is_banned)
SELECT country,MAX(is_banned) FROM requests_source GROUP BY country
ON DUPLICATE KEY UPDATE country_name=VALUES(country_name);
INSERT INTO clients(client_ip,country_id)
SELECT r.client_ip,MIN(c.country_id) FROM requests_source r
JOIN countries c ON c.country_name=r.country GROUP BY r.client_ip
ON DUPLICATE KEY UPDATE client_ip=VALUES(client_ip);
INSERT INTO requests
SELECT r.request_id,r.request_time,c.client_id,r.gender,r.age,r.income,
 r.time_of_day,r.requested_file,r.http_status
FROM requests_source r JOIN clients c USING(client_ip)
ON DUPLICATE KEY UPDATE request_id=VALUES(request_id);
COMMIT;
CREATE OR REPLACE VIEW request_details AS
SELECT r.request_id,r.request_time,country.country_name AS country,c.client_ip,
 r.gender,r.age,r.income,country.is_banned,r.time_of_day,r.requested_file,r.http_status
FROM requests r JOIN clients c USING(client_id) JOIN countries country USING(country_id);
