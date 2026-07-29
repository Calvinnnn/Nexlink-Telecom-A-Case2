INSERT INTO SUBSCRIPTION_PLANS (name, monthly_cost_usd, max_speed_mbps) VALUES
('Basic', 20, 30),
('Standard', 35, 50),
('Premium', 60, 100);

INSERT INTO ACCOUNTS (plan_id, customer_name, account_pin, address) VALUES
(3, 'Sarah Branden', '1234', '1428 Elm St, Springfield'),
(1, 'Walter White', '5678', '308 Negra Arroyo Lane, Albuquerque'),
(2, 'Ellen Ripley', '9999', 'LV-426 Nostromo Ave, Seattle');


--to add more error logs to fit the demo
INSERT INTO EQUIPMENT (serial_num, account_id, model_type, status, last_error_log) VALUES
('SN-99X-001', 1, 'Nextlink-Optic-V1', 'online', '2026-07-28 10:00:00 - SYS_OK: Uptime 45 days. Optic levels nominal.'),
('SN-99X-002', 2, 'Nextlink-Coax-V2', 'error', '2026-07-28 18:45:12 - CRIT_ERR: eth0 link down. 2026-07-28 18:45:15 - WARN: Optical sensor timeout. 2026-07-28 18:46:00 - HW_FAULT: Solid Red LED triggered. Cause unknown (loss of physical medium).'),
('SN-99X-003', 3, 'Nextlink-Optic-V1', 'online', '2026-07-28 09:15:00 - SYS_OK: Firmware updated.');

INSERT INTO SUPPORT_TICKETS (account_id, ticket_type, status, description) VALUES
(3, 'billing', 'closed', 'Customer called to verify first month payment received.'),
(2, 'technical', 'open', 'Customer complains of intermittent drops during thunderstorms. Line sweep pending.');