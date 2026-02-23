# BCP Warhammer Dashboard (Django)

Dashboard en Django para analizar composición de ejércitos de Warhammer a partir de datos de Best Coast Pairings (BCP), almacenando los datos en SQLite para su explotación posterior.

## Funcionalidades
- Ingesta de listas de torneos desde JSON exportado de BCP.
- Ingesta de evento directamente desde la web de BCP autenticando usuario.
- Persistencia local en base de datos SQLite.
- Dashboard con métricas clave:
  - Torneos importados
  - Listas analizadas
  - Facciones únicas
  - Facciones más jugadas
  - Unidades más frecuentes
  - Rendimiento por facción

## Instalación
```bash
pip install -r requirements.txt
python manage.py migrate
```

## Importar datos desde JSON
```bash
python manage.py import_bcp_lists data_samples/sample_tournament.json
```

## Importar evento desde web BCP
```bash
python manage.py import_bcp_event <event_id_o_url>
```

También puedes sobrescribir credenciales:
```bash
python manage.py import_bcp_event <event_id_o_url> --email tu_email --password tu_password
```

## Ejecutar dashboard
```bash
python manage.py runserver
```
Abrir `http://127.0.0.1:8000/`.

## Formato esperado de input JSON
Ver `data_samples/sample_tournament.json`.
