ALTER TABLE departamento ADD COLUMN IF NOT EXISTS parent_id INT REFERENCES departamento(id);

ALTER TABLE bien DROP CONSTRAINT IF EXISTS bien_estado_check;
ALTER TABLE bien ALTER COLUMN estado TYPE VARCHAR(100);

UPDATE bien SET estado = '01) OPERATIVO, EN USO, EXCELENTE ESTADO' WHERE estado = 'Activo';
UPDATE bien SET estado = '07) DESINCORPORADO EN DESUSO' WHERE estado = 'En desuso';

ALTER TABLE bien ADD CONSTRAINT bien_estado_check CHECK (estado IN (
        '01) OPERATIVO, EN USO, EXCELENTE ESTADO',
        '02) OPERATIVO, EN USO PERO REQUIERE REPARACIÓN',
        '03) OPERATIVO, SIN USO, EN EXCELENTE ESTADO',
        '04) OPERATIVO, SIN USO, PERO REQUIERE REPARACIÓN',
        '05) INOPERATIVO, PERO RECUPERABLE',
        '06) INOPERATIVO, IRRECUPERABLE',
        '07) DESINCORPORADO EN DESUSO',
        'Faltante'
));

INSERT INTO departamento (id, codigo, nombre, parent_id) VALUES
(4, 'DEP-IT-SOP', 'Soporte Técnico', 1),
(5, 'DEP-RRHH-REC', 'Reclutamiento y Selección', 2)
ON CONFLICT (id) DO NOTHING;

SELECT setval('departamento_id_seq', (SELECT MAX(id) FROM departamento));

ALTER TABLE formulario_bm ADD COLUMN IF NOT EXISTS archivo_pdf BYTEA;
