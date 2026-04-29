INSERT INTO departamento (id, codigo, nombre) VALUES
(1, 'DEP-IT', 'Tecnología de Información'),
(2, 'DEP-RRHH', 'Recursos Humanos'),
(3, 'DEP-ADM', 'Administración')
ON CONFLICT (id) DO NOTHING;

SELECT setval('departamento_id_seq', (SELECT MAX(id) FROM departamento));

INSERT INTO bien (codigo_activo, codigo_nivel, descripcion, categoria_id, marca, modelo, serial_bien, color, tipo, num_piezas, orden_compra, fecha_compra, precio_sin_iva, moneda, vida_util_meses, departamento_id, cuenta_contable, estado, observaciones, creado_por) VALUES 
('ACT-0001', 'N-1', 'Laptop Dell XPS 15', 2, 'Dell', 'XPS 15 9500', 'SN-998877', 'Gris', 'Portátil', 1, 'OC-2023-01', '2023-05-10', 1200.00, 'Dólares', 60, 1, '2-1-214-13', '01) OPERATIVO, EN USO, EXCELENTE ESTADO', 'Equipo asignado a desarrollo', 1),
('ACT-0002', 'N-1', 'Escritorio de Madera Tipo L', 1, 'Generica', 'L-Office', 'N/A', 'Marrón', 'Mobiliario', 1, 'OC-2022-04', '2022-08-15', 150.50, 'Dólares', 120, 2, '2-1-214-01', '01) OPERATIVO, EN USO, EXCELENTE ESTADO', 'Ubicado en oficina de RRHH', 1),
('ACT-0003', 'N-2', 'Aire Acondicionado Split 12000 BTU', 3, 'Samsung', 'AS-12', 'SN-AC-1122', 'Blanco', 'Climatización', 1, 'OC-2023-11', '2023-12-01', 320.00, 'Dólares', 60, 1, '2-1-214-01', '01) OPERATIVO, EN USO, EXCELENTE ESTADO', 'En el cuarto de servidores', 1);
