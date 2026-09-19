CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'kg',
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS lots(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    internal_lot TEXT NOT NULL UNIQUE,
    supplier_lot TEXT,
    qty_received REAL NOT NULL,
    qty_reserved REAL NOT NULL DEFAULT 0,
    qty_consumed REAL NOT NULL DEFAULT 0,
    expiry_date TEXT,
    status TEXT NOT NULL CHECK(status IN ('LIBERE','BLOQUE','EN_VALIDATION'))
);
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_type TEXT NOT NULL,
    client_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_lines(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    lot_id INTEGER NOT NULL REFERENCES lots(id),
    quantity REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RELEASED','CONSUMED'))
);
CREATE TABLE IF NOT EXISTS audit_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL
);

INSERT OR IGNORE INTO products(id,reference,name,unit,active)
VALUES
(1,'LPFB-CAR-001','Carottes bio julienne','kg',1),
(2,'LPFB-GRN-033','THE GREEN 33 cl','bouteille',1);

INSERT OR IGNORE INTO lots(id,product_id,internal_lot,supplier_lot,qty_received,expiry_date,status)
VALUES
(1,1,'CAR-A12','FOUR-2026-A',25,'2026-09-22','LIBERE'),
(2,1,'CAR-A13','FOUR-2026-B',35,'2026-09-25','LIBERE'),
(3,1,'CAR-X99','FOUR-2026-X',12,'2026-09-21','BLOQUE');
