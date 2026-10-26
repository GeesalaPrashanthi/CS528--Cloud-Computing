"""Create HW5 MySQL database and tables; safe to run again.

Uses the Cloud SQL Auth Proxy locally or from a VM. Never hardcode secrets.
Required: DB_PASSWORD (or MYSQL_PWD); optional DB_HOST, DB_PORT, DB_USER, DB_NAME.
"""
import os
import pymysql

DB_NAME = os.getenv('DB_NAME', 'cs528_hw5')
if not DB_NAME.replace('_', '').isalnum() or not (DB_NAME[0].isalpha() or DB_NAME[0] == '_'):
    raise ValueError('Invalid DB_NAME')

password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PWD')
if not password:
    raise SystemExit('Set DB_PASSWORD in your shell; do not put it in code.')

conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '3307')),
    user=os.getenv('DB_USER', 'root'),
    password=password,
    charset='utf8mb4',
    autocommit=True,
    connect_timeout=15,
)
try:
    with conn.cursor() as cur:
        cur.execute(f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4')
        cur.execute(f'USE `{DB_NAME}`')
        cur.execute('''CREATE TABLE IF NOT EXISTS requests (
            request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            request_time DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            country VARCHAR(100),
            client_ip VARCHAR(45),
            gender VARCHAR(30),
            age VARCHAR(20),
            income VARCHAR(100),
            is_banned BOOLEAN NOT NULL DEFAULT FALSE,
            time_of_day VARCHAR(50),
            requested_file VARCHAR(1024),
            http_status SMALLINT,
            INDEX idx_requests_country (country),
            INDEX idx_requests_status (http_status)
        ) ENGINE=InnoDB''')
        cur.execute('''CREATE TABLE IF NOT EXISTS request_errors (
            error_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            request_time DATETIME(6) NOT NULL,
            requested_file VARCHAR(1024),
            error_code SMALLINT NOT NULL
        ) ENGINE=InnoDB''')
        cur.execute('SHOW TABLES')
        print(f'Database `{DB_NAME}` ready. Tables:', [row[0] for row in cur.fetchall()])
finally:
    conn.close()
