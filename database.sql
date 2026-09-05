CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. OMMAS Table (Administrative & Procurement)
DROP TABLE IF EXISTS ommas_projects CASCADE;
CREATE TABLE ommas_projects (
    package_id VARCHAR(20) PRIMARY KEY,
    work_name TEXT NOT NULL,
    state_name VARCHAR(50),
    district_name VARCHAR(50),
    block_name VARCHAR(50),
    sanctioned_cost_cr NUMERIC(8, 4),
    sanctioned_length_km NUMERIC(6, 3),
    sanction_year VARCHAR(10),
    status VARCHAR(30),
    stated_delay_reason VARCHAR(100)
);

-- 2. GeoSadak Table (Spatial Alignments)
DROP TABLE IF EXISTS geosadak_alignments CASCADE;
CREATE TABLE geosadak_alignments (
    cn_code INT PRIMARY KEY,
    mrl_id INT,
    work_name TEXT NOT NULL,
    proposed_length_km INT,
    ims_year INT,
    lgd_state_code INT,
    lgd_district_code INT,
    lgd_block_id INT,
    geom GEOMETRY(LineString, 4326) NOT NULL
);
CREATE INDEX idx_geosadak_geom ON geosadak_alignments USING GIST(geom);

-- 3. DILRMP Cadastral Parcels Table
DROP TABLE IF EXISTS dilrmp_cadastral_parcels CASCADE;
CREATE TABLE dilrmp_cadastral_parcels (
    ulpin VARCHAR(14) PRIMARY KEY,
    state_code INT,
    district_code INT,
    mouza_name VARCHAR(50),
    jl_number INT,
    dag_khasra_no VARCHAR(20),
    owner_name VARCHAR(100),
    land_classification VARCHAR(50),
    encumbrance_status VARCHAR(50),
    case_ref_no VARCHAR(50),
    geom GEOMETRY(Polygon, 4326) NOT NULL
);
CREATE INDEX idx_dilrmp_geom ON dilrmp_cadastral_parcels USING GIST(geom);

-- Seed Data: WB2315 Golden Record
INSERT INTO ommas_projects VALUES (
    'WB2315',
    'MRL03-SHIBPUR (PART OF SHIBPUR GOURBAZAR RD.) TO SRIMPUR',
    'West Bengal',
    'Paschim Burdwan',
    'Kanksa',
    8.0674,
    6.750,
    '2024-2025',
    'In-progress',
    'Legal Case'
);

INSERT INTO geosadak_alignments VALUES (
    668713,
    248626,
    'MRL03-SHIBPUR (PART OF SHIBPUR GOURBAZAR RD.) TO SRIMPUR',
    7,
    2024,
    19,
    704,
    7128,
    ST_GeomFromText('LINESTRING(87.42150 23.56800, 87.43200 23.57520, 87.44450 23.58610, 87.45800 23.59750)', 4326)
);

INSERT INTO dilrmp_cadastral_parcels VALUES 
('1970407128001A', 19, 704, 'Shibpur', 82, 'Plot 101/A', 'Animesh Banerjee', 'Rayati (Private)', 'Clear', NULL,
 ST_GeomFromText('POLYGON((87.4200 23.5670, 87.4230 23.5670, 87.4230 23.5700, 87.4200 23.5700, 87.4200 23.5670))', 4326)),
('1970407128002B', 19, 704, 'Shibpur', 82, 'Plot 102', 'Mukesh Roy & Others', 'Sthitiban (Private)', 'Stay Order', 'HC-CAL-WP-11204/2025',
 ST_GeomFromText('POLYGON((87.4300 23.5740, 87.4350 23.5740, 87.4350 23.5770, 87.4300 23.5770, 87.4300 23.5740))', 4326)),
('1970407128003C', 19, 704, 'Gourbazar', 83, 'Plot 404', 'WB State PWD', 'Government Vested', 'Clear', NULL,
 ST_GeomFromText('POLYGON((87.4430 23.5850, 87.4470 23.5850, 87.4470 23.5880, 87.4430 23.5880, 87.4430 23.5850))', 4326)),
('1970407128004D', 19, 704, 'Srimpur', 85, 'Plot 512', 'Forest Department', 'Protected Forest (Zudpi)', 'Pending Clearance', 'PARIVESH-FP-WB-2025-09',
 ST_GeomFromText('POLYGON((87.4560 23.5960, 87.4600 23.5960, 87.4600 23.5990, 87.4560 23.5990, 87.4560 23.5960))', 4326));