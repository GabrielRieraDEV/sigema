-- ==============================================================================
-- SIGEMA - Sistema de Gestión de Bienes Muebles
-- Script de Creación de Base de Datos para PostgreSQL 15
-- Creado: Marzo 2026
-- ==============================================================================

-- ==========================================
-- LIMPIEZA DE TABLAS (En orden de dependencias)
-- ==========================================
DROP TABLE IF EXISTS auditoria CASCADE;
DROP TABLE IF EXISTS formulario_bm CASCADE;
DROP TABLE IF EXISTS movimiento CASCADE;
DROP TABLE IF EXISTS bien CASCADE;
DROP TABLE IF EXISTS cuenta_contable CASCADE;
DROP TABLE IF EXISTS categoria CASCADE;
DROP TABLE IF EXISTS departamento CASCADE;
DROP TABLE IF EXISTS usuario CASCADE;


-- ==========================================
-- 1. CATÁLOGOS Y SEGURIDAD
-- ==========================================

CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    cargo VARCHAR(100),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    perfil VARCHAR(50) NOT NULL CHECK (perfil IN ('Administrador', 'Almacenista', 'Consulta')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE departamento (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE categoria (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE cuenta_contable (
    codigo VARCHAR(20) PRIMARY KEY,
    descripcion VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);


-- ==========================================
-- 2. NÚCLEO (CORE) - BIENES Y MOVIMIENTOS
-- ==========================================

CREATE TABLE bien (
    id SERIAL PRIMARY KEY,
    codigo_activo VARCHAR(50) UNIQUE NOT NULL,
    codigo_nivel VARCHAR(20) NOT NULL,
    descripcion TEXT NOT NULL,
    categoria_id INT NOT NULL REFERENCES categoria(id),
    marca VARCHAR(100),
    modelo VARCHAR(100),
    serial_bien VARCHAR(100),
    color VARCHAR(50),
    tipo VARCHAR(50),
    num_piezas INT NOT NULL DEFAULT 1,
    orden_compra VARCHAR(50),
    fecha_compra DATE NOT NULL,
    precio_sin_iva NUMERIC(15, 2) NOT NULL,
    moneda VARCHAR(10) NOT NULL CHECK (moneda IN ('Bolívares', 'Dólares')),
    vida_util_meses INT NOT NULL DEFAULT 60,
    departamento_id INT NOT NULL REFERENCES departamento(id),
    cuenta_contable VARCHAR(20) NOT NULL REFERENCES cuenta_contable(codigo),
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('Activo', 'En desuso', 'Faltante')),
    observaciones TEXT,
    creado_por INT REFERENCES usuario(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE movimiento (
    id SERIAL PRIMARY KEY,
    bien_id INT NOT NULL REFERENCES bien(id),
    tipo_movimiento VARCHAR(50) NOT NULL CHECK (tipo_movimiento IN ('Incorporación', 'Desincorporación', 'Marcado como faltante', 'Cambio de departamento destino')),
    departamento_origen INT REFERENCES departamento(id),
    departamento_destino INT REFERENCES departamento(id),
    motivo VARCHAR(255),
    responsable_faltante VARCHAR(150),
    registrado_por INT NOT NULL REFERENCES usuario(id),
    fecha_movimiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT
);

CREATE TABLE formulario_bm (
    id SERIAL PRIMARY KEY,
    tipo_bm VARCHAR(10) NOT NULL CHECK (tipo_bm IN ('BM-1', 'BM-2', 'BM-3', 'BM-4')),
    generado_por INT NOT NULL REFERENCES usuario(id),
    fecha_generacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('Vigente', 'Anulado')),
    motivo_anulacion VARCHAR(255),
    parametros JSONB
);


-- ==========================================
-- 3. AUDITORÍA
-- ==========================================

CREATE TABLE auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuario(id),
    tabla_afectada VARCHAR(50) NOT NULL,
    accion VARCHAR(50) NOT NULL,
    registro_id INT,
    datos_antes JSONB,
    datos_despues JSONB,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_origen VARCHAR(45)
);


-- ==========================================
-- 4. ÍNDICES Y RESTRICCIONES (Performance)
-- ==========================================

CREATE INDEX idx_bien_codigo_activo ON bien(codigo_activo);
CREATE INDEX idx_bien_estado ON bien(estado);
CREATE INDEX idx_bien_departamento_id ON bien(departamento_id);
CREATE INDEX idx_movimiento_bien_id ON movimiento(bien_id);
CREATE INDEX idx_auditoria_usuario_id ON auditoria(usuario_id);
CREATE INDEX idx_auditoria_fecha_hora ON auditoria(fecha_hora);


-- ==========================================
-- 5. DATOS INICIALES (SEEDS)
-- ==========================================

-- 5.1 Cuentas contables (Plan de cuentas 2-1-214-XX)
INSERT INTO cuenta_contable (codigo, descripcion) VALUES
('2-1-214-01', 'Máquinas muebles y demás equipos de oficina'),
('2-1-214-02', 'Mobiliario y enseres de alojamiento'),
('2-1-214-03', 'Maquinarias y demás equipos de construcción'),
('2-1-214-04', 'Equipos de transporte'),
('2-1-214-05', 'Equipos de comunicación y señalamiento'),
('2-1-214-06', 'Equipos médicos quirúrgicos dentales'),
('2-1-214-07', 'Colecciones culturales, artísticas e históricas'),
('2-1-214-08', 'Armamento y material de defensa'),
('2-1-214-09', 'Instalaciones provisionales'),
('2-1-214-10', 'Semovientes'),
('2-1-214-11', '(Reservado)'),
('2-1-214-13', 'Equipos de procesamiento de datos');

-- 5.2 Usuario Administrador Inicial
-- Contraseña (admin123) en hash bcrypt
INSERT INTO usuario (nombre, apellido, cargo, username, password_hash, perfil, activo) VALUES
('Administrador', 'Sistema', 'Jefe División Control de Bienes', 'admin', '$2b$12$Kig0h7i.o.7z3X./520eFeWjD8z9/hX6m0q2QJIt20iM23D0r2uOS', 'Administrador', TRUE);

-- 5.3 Categorías básicas
INSERT INTO categoria (nombre, descripcion) VALUES
('Mobiliario de Oficina', 'Escritorios, sillas, archivadores, estantes y mesas de sala de juntas'),
('Equipos de Computación', 'Computadoras de escritorio, laptops, monitores, impresoras multifuncionales'),
('Equipos de Climatización', 'Aires acondicionados, ventiladores, extractores'),
('Vehículos', 'Camionetas, carros, motos, maquinaria pesada y transporte institucional'),
('Herramientas de Mantenimiento', 'Cajas de herramientas, taladros, esmeriles, equipos de taller'),
('Equipos Electrónicos y Comunicación', 'Televisores, proyectores, teléfonos IP, radios transmisores');

-- Fin del script
