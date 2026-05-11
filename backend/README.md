# Backend de Transfreezer Insight Suite

API REST construida con FastAPI para servir los módulos de series de tiempo y econometría al frontend.

## Requisitos

- Python 3.10 o superior
- pip actualizado

## Instalación de dependencias

Desde la carpeta backend:

```bash
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Recomendaciones adicionales

- El proyecto usa `spacy` para procesamiento de texto en español. Tras instalar las dependencias, instala el modelo en español recomendado:

```bash
python -m spacy download es_core_news_sm
```

- Las versiones de `scikit-learn` deben coincidir con las usadas para serializar modelos. El archivo `requirements.txt` está fijado en `scikit-learn==1.6.1` para evitar warnings al desempaquetar modelos.

- Los modelos entrenados (archivos grandes, p.ej. `.pkl`/`.joblib`) NO están incluidos en el repositorio por defecto; colócalos en `app/modules/forecast_operativo/artifacts/models/` como indica la sección "Dónde copiar los modelos entrenados".

Si usas entorno virtual (recomendado):

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Variables de entorno

Puedes crear backend/.env (opcional para correr local con modelos ya entrenados).

Ejemplo minimo:

```env
MODEL_FILE=app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl
ECONOMETRIA_MODEL_FILE=app/modules/econometria/artifacts/models/transfreezer_modelo_econometrico_v1.pkl
```

Variables de Snowflake (solo necesarias para capas descriptivas conectadas al DW):

- SNOWFLAKE_ACCOUNT
- SNOWFLAKE_USER
- SNOWFLAKE_PASSWORD
- SNOWFLAKE_WAREHOUSE
- SNOWFLAKE_DATABASE
- SNOWFLAKE_SCHEMA
- SNOWFLAKE_ROLE

## Levantar servidor backend

Desde backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints base:

- API base: http://127.0.0.1:8000/api/v1
- Swagger: http://127.0.0.1:8000/docs

## Modelos y rutas

Coloca los modelos entrenados en:

- **Forecast Operativo**: `app/modules/forecast_operativo/artifacts/models/`
  - Archivo esperado: `forecast_model.pkl` o `transfreezer_modelo_ts.pkl`
  - Configurable vía: `MODEL_FILE`

- **Econometría**: `app/modules/econometria/artifacts/models/`
  - Archivo esperado: `transfreezer_modelo_econometrico_v1.pkl`
  - Soporta alternativas: `.plk` (fallback), o desde `forecast_operativo/artifacts/models/`
  - Configurable vía: `ECONOMETRIA_MODEL_FILE`

- **Torre de Control SIO (Minería)**: `app/modules/mineria/artifacts/models/`
  - Archivo esperado: `best_model.pkl`
  - Soporta alternativas: `.plk` como fallback

Formatos soportados:

- .pkl
- .plk (alternativa/fallback)
- .joblib

## Qué expone este backend

- Series de tiempo: /api/v1/forecast-operativo/*
- Econometría: /api/v1/econometria/*
- Salud: /api/v1/health
