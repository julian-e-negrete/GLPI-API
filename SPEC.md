# Especificación Técnica: GLPI API Proxy v1.0

## 1. Visión General del Proyecto

| Campo | Descripción |
|-------|-------------|
| **Nombre del Proyecto** | GLPI API Proxy |
| **Versión** | 1.0.0 |
| **Descripción** | Capa intermedia (Proxy) para centralizar la comunicación con la API de GLPI v2.2, gestionando autenticación OAuth, logging completo y control de peticiones |
| **Servidor GLPI Destino** | 192.168.1.33:80 |
| **Tecnología** | Python 3.10+ con FastAPI |

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE                                     │
│                   (Aplicación externa que consume API)                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ HTTP/HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        GLPI API PROXY                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Server (Puerto 8080)                                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │    │
│  │  │   OAuth    │  │   Middleware│  │    Logging Handler     │ │    │
│  │  │  Manager   │  │   Logging   │  │  (Input/Output)        │ │    │
│  │  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │    │
│  │         │                │                     │               │    │
│  │         ▼                │                     ▼               │    │
│  │  ┌─────────────────────────────────────────────────────────┐  │    │
│  │  │              Request Router / Proxy Pass                 │  │    │
│  │  └──────────────────────────┬────────────────────────────────┘  │    │
│  └─────────────────────────────┼───────────────────────────────────┘    │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼ (con Bearer Token)
┌─────────────────────────────────────────────────────────────────────────┐
│                    GLPI SERVER (192.168.1.33:80)                        │
│                         API v2.2                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐    │
│  │ /api.php/v2.2/  │  │  /token (OAuth) │  │  /Administration/   │    │
│  │    token        │  │                 │  │  User, Ticket, etc │    │
│  └─────────────────┘  └─────────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Componentes Principales

| Componente | Descripción | Responsabilidad |
|------------|-------------|------------------|
| **OAuth Manager** | Gestor de autenticación OAuth | Obtiene y renueva tokens de acceso |
| **Request Router** | Enrutador de peticiones | Reenvía peticiones al servidor GLPI |
| **Middleware Logging** | Middleware de registro | Captura y almacena logs de Input/Output |
| **Token Manager** | Gestor de tokens | Almacena y administra el Bearer Token |

---

## 3. Flujo OAuth

### 3.1 Flujo de Autenticación (Password Grant)

```
┌─────────┐                                      ┌─────────────┐
│  CLIENT │                                      │ PROXY GLPI  │
└────┬────┘                                      └──────┬──────┘
     │                                                  │
     │  1. POST /token (credentials)                     │
     │  ────────────────────────────────────────────▶   │
     │                                                  │
     │                                                  │ 2. Validate credentials
     │                                                  │    and env vars
     │                                                  │
     │                                                  ▼
     │                                         ┌─────────────┐
     │                                         │  GLPI API   │
     │                                         │  (Target)   │
     │                                         └──────┬──────┘
     │                                                │
     │  3. POST http://192.168.1.33:80/api.php/v2.2/token
     │  ──────────────────────────────────────────────────────────▶
     │                                                │
     │                                                │ 4. Validate and
     │                                                │    generate token
     │                                                │
     │  5. Response: { access_token, expires_in, ... }
     │  ◀───────────────────────────────────────────────────────────
     │                                                  │
     │  6. Return token to client                       │
     │  ◀─────────────────────────────────────────────
     │                                                  │
     │  7. Subsequent requests with Bearer Token       │
     │  ────────────────────────────────────────────▶  │
     │                                                  │
```

### 3.2 Parámetros de Autenticación

| Parámetro | Valor | Tipo | Descripción |
|-----------|-------|------|-------------|
| `grant_type` | `password` | string | Tipo de grant OAuth |
| `client_id` | Variable de entorno | string | ID de cliente OAuth |
| `client_secret` | Variable de entorno | string | Secreto del cliente |
| `username` | Variable de entorno | string | Usuario GLPI |
| `password` | Variable de entorno | string | Password del usuario |

### 3.3 Gestión del Token

- **Almacenamiento**: En memoria con estructura de datos segura
- **Renovación**: Automática cuando el token expire o antes de cada request válido
- **Expiration Time**: Se manejará según el valor `expires_in` de la respuesta GLPI
- **Timeout**: 30 segundos para requests al servidor GLPI

---

## 4. Headers Obligatorios

Todas las peticiones hacia GLPI deben incluir los siguientes headers:

| Header | Valor | Descripción |
|--------|-------|-------------|
| `Accept` | `application/json` | Formato de respuesta esperado |
| `GLPI-Entity-Recursive` | `true` | Búsqueda recursiva en entidades |
| `Accept-Language` | `en_GB` | Idioma de la respuesta |
| `Authorization` | `Bearer {access_token}` | Token de acceso OAuth |

---

## 5. Estrategia de Logging

### 5.1 Estructura de Logs

Cada interacción se registrará en formato JSON con los siguientes campos:

```json
{
  "timestamp": "2026-03-13T10:30:00.000Z",
  "request_id": "uuid-v4",
  "type": "input|output",
  "direction": "client_to_proxy|proxy_to_glpi|glpi_to_proxy|proxy_to_client",
  "method": "GET|POST|PUT|DELETE|PATCH",
  "path": "/api/v2.2/Administration/User",
  "headers": {
    "Accept": "application/json",
    "Authorization": "Bearer ***",
    "GLPI-Entity-Recursive": "true",
    "Accept-Language": "en_GB"
  },
  "body": { ... },
  "status_code": 200,
  "response_time_ms": 150,
  "source_ip": "192.168.1.100",
  "user_agent": "Python-httpx/..."
}
```

### 5.2 Categorías de Logging

| Tipo | Descripción | Datos Registrados |
|------|-------------|-------------------|
| **Input (Cliente → Proxy)** | Petición recibida del cliente | Headers, Body, Método, Path, IP origen |
| **Output (Proxy → Cliente)** | Respuesta enviada al cliente | Status, Headers, Body, Tiempo de respuesta |
| **Upstream (Proxy → GLPI)** | Petición reenviada a GLPI | Headers completos, Body, Método, URL |
| **Upstream Response (GLPI → Proxy)** | Respuesta recibida de GLPI | Status, Headers, Body |

### 5.3 Destino de Logs

- **Formato**: JSON Lines (JSONL) para facilitar procesamiento
- **Ubicación**: `/var/log/glpi-proxy/` (configurable)
- **Rotación**: Diaria, máximo 30 días de retención
- **Niveles**: INFO para operaciones normales, ERROR para fallos

---

## 6. Requisitos Técnicos

### 6.1 Dependencias Python

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.26.0
python-dotenv>=1.0.0
pydantic>=2.5.0
python-json-logger>=2.0.0
```

### 6.2 Variables de Entorno Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `GLPI_API_URL` | URL base del servidor GLPI | `http://192.168.1.33:80` |
| `GLPI_CLIENT_ID` | ID de cliente OAuth | `ad656bf992e92a427b4dfd75063bbaf63813049c59ac69f8e874c45d088caa18` |
| `GLPI_CLIENT_SECRET` | Secreto del cliente | `415ade7681bc086a64dfb36ec0f81b1e6126e211ca4072c3e9f2c7df603d81bc` |
| `GLPI_USERNAME` | Usuario GLPI | `admin` |
| `GLPI_PASSWORD` | Password del usuario | `password_seguro` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `LOG_DIR` | Directorio de logs | `/var/log/glpi-proxy` |
| `PROXY_PORT` | Puerto del servidor proxy | `8080` |

### 6.3 Seguridad

- Las credenciales se almacenan exclusivamente en variables de entorno
- No se registran passwords ni secretos en los logs
- El token de acceso se mascara en los logs de salida
- Timeout de 30 segundos para todas las peticiones HTTP
- Validación de esquemas de request/response con Pydantic

---

## 7. Endpoints del Proxy

### 7.1 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v2.2/token` | Obtener token de acceso |
| `GET` | `/api/v2.2/Health` | Verificar estado del proxy |
| `GET` | `/api/v2.2/ping` | Ping de salud |
| `*` | `/api/v2.2/{resource}` | Proxy genérico a cualquier endpoint GLPI |
| `GET` | `/api/v2.2/logs` | Ver logs recientes (solo desarrollo) |

### 7.2 Reenvío de Peticiones

Todas las peticiones que no sean `/token`, `/Health` o `/ping` se reenviarán a GLPI manteniendo:
- Método HTTP original
- Headers originales (con adiciones obligatorias)
- Body original
- Query parameters

---

## 8. Manejo de Errores

| Código | Descripción | Acción |
|--------|-------------|--------|
| 400 | Bad Request | Retornar error al cliente |
| 401 | Unauthorized | Intentar renovación de token |
| 403 | Forbidden | Retornar error al cliente |
| 404 | Not Found | Retornar error al cliente |
| 500 | Server Error | Loguear y retornar error genérico |
| 502 | Bad Gateway | Loguear error de conexión GLPI |
| 503 | Service Unavailable | Retornar mensaje de no disponibilidad |

---

## 9. Estructura del Proyecto

```
glpi-api/
├── SPEC.md
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicación FastAPI
│   ├── config.py               # Configuración
│   ├── models/
│   │   ├── __init__.py
│   │   ├── token.py            # Modelos de token
│   │   └── requests.py         # Modelos de request
│   ├── services/
│   │   ├── __init__.py
│   │   ├── oauth.py            # Gestor OAuth
│   │   ├── glpi_client.py     # Cliente HTTP hacia GLPI
│   │   └── logger.py           # Sistema de logging
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── token.py            # Endpoint de token
│   │   ├── proxy.py            # Endpoints proxy
│   │   └── health.py           # Endpoints de salud
│   └── middleware/
│       ├── __init__.py
│       └── logging.py          # Middleware de logging
├── logs/                       # Directorio de logs
└── tests/
    └── test_proxy.py           # Tests unitarios
```

---

## 10. Diagrama de Secuencia (Request Típica)

```
┌────────┐     ┌────────┐     ┌─────────┐     ┌─────────┐
│ Client │     │ Proxy  │     │  OAuth  │     │  GLPI   │
└───┬────┘     └───┬────┘     └───┬─────┘     └───┬─────┘
    │             │             │               │
    │ Request     │             │               │
    │────────────▶│             │               │
    │             │             │               │
    │             │ Log Input  │               │
    │             │────────────▶│               │
    │             │             │               │
    │             │ Has Token?  │               │
    │             │────────────▶│               │
    │             │             │               │
    │             │◀────────────│               │
    │             │ Valid/Invalid│               │
    │             │             │               │
    │             │             │ Request Token │
    │             │─────────────────────────────▶│
    │             │             │               │
    │             │◀─────────────────────────────│
    │             │             │  Token Response│
    │             │             │               │
    │             │ Log Output  │               │
    │             │ (Success)   │               │
    │             │────────────▶│               │
    │             │             │               │
    │ Response    │             │               │
    │◀────────────│             │               │
    │             │             │               │
```