# Frontend de Transfreezer Insight Suite

Aplicacion web en Next.js para visualizar dashboards de series de tiempo y econometria.

## Requisitos

- Node.js 20 o superior
- npm

## Instalacion de dependencias

Desde la carpeta frontend:

```bash
cd frontend
npm install
```

## Variables de entorno

Crea frontend/.env.local para definir la URL del backend cuando sea necesario.

Ejemplo:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1/econometria
```

Notas:

- El modulo econometria usa fallback de URLs (localhost/127.0.0.1) si la variable no existe.
- El modulo forecast actualmente consume directo: http://127.0.0.1:8000/api/v1/forecast-operativo/dashboard.

## Levantar servidor frontend

Desde frontend:

```bash
npm run dev
```

Abre:

- http://localhost:3000

## Build de produccion

```bash
npm run build
npm start
```

## Rutas de modulos principales

- /modules/forecast
- /modules/econometria

## Tecnologias clave

- Next.js 15
- React 19
- TypeScript
- Recharts
- react-katex
