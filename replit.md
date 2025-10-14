# Servidor MCP para Odoo - Proyecto Replit

## Información del Proyecto

Este es un servidor MCP (Model Context Protocol) mejorado para Odoo, diseñado para ser compatible con N8N, ChatGPT, Claude y otros agentes de IA.

## Arquitectura

### Componentes Principales

1. **mcp_server_odoo/config.py** - Gestión de configuración con Pydantic
2. **mcp_server_odoo/auth.py** - Autenticación multi-método (API Keys, JWT)
3. **mcp_server_odoo/odoo_client.py** - Cliente Odoo con reintentos y caché
4. **mcp_server_odoo/tools.py** - 7 herramientas MCP optimizadas para LLMs
5. **mcp_server_odoo/http_server.py** - Servidor HTTP con FastAPI
6. **mcp_server_odoo/server.py** - Servidor stdio para Claude Desktop
7. **mcp_server_odoo/cache.py** - Sistema de caché Redis opcional

### Herramientas MCP Disponibles

1. `odoo_search_records` - Buscar registros con filtros
2. `odoo_read_records` - Leer datos de registros específicos
3. `odoo_search_read_records` - Buscar y leer en una operación
4. `odoo_create_record` - Crear nuevos registros
5. `odoo_update_record` - Actualizar registros existentes
6. `odoo_delete_record` - Eliminar registros
7. `odoo_get_model_fields` - Obtener definición de campos

## Mejoras sobre el Repositorio Original

### Autenticación Mejorada
- Soporte para API Keys estáticas
- Generación de JWT tokens
- Middleware de autenticación en FastAPI

### Optimización para LLMs
- Descripciones detalladas de herramientas con ejemplos
- Schemas enriquecidos con información de parámetros
- Mensajes de error claros con sugerencias de solución
- Documentación inline para cada campo

### Performance
- Sistema de caché opcional con Redis
- Caché local en memoria como fallback
- Reintentos automáticos con backoff exponencial
- Timeout configurables

### Observabilidad
- Logging estructurado con structlog
- Formato JSON o consola
- Trazabilidad de requests
- Health checks

### Compatibilidad
- Modo HTTP para N8N y agentes web
- Modo stdio para Claude Desktop
- Documentación OpenAPI/Swagger automática
- CORS habilitado para integraciones web

## Configuración Necesaria

El servidor requiere estas variables de entorno (configurar en Secrets):

- `ODOO_URL` - URL de la instancia Odoo
- `ODOO_DB` - Nombre de la base de datos
- `ODOO_USERNAME` - Usuario de Odoo
- `ODOO_PASSWORD` - Contraseña de Odoo
- `SECRET_KEY` - Clave secreta para JWT (opcional)
- `API_KEYS` - Claves API separadas por comas (opcional)

## Uso

### Modo HTTP (por defecto)

El servidor se ejecuta en modo HTTP en el puerto 5000:

```bash
python -m mcp_server_odoo
```

Endpoints disponibles:
- `POST /mcp` - **MCP HTTP Streamable** (para N8N con nodo MCP)
- `GET /` - Info del servidor
- `GET /health` - Health check
- `GET /docs` - Documentación Swagger
- `POST /login` - Obtener JWT
- `GET /.well-known/oauth-authorization-server` - **OAuth Discovery (RFC 8414)**
- `GET /.well-known/oauth-protected-resource` - **Resource Discovery (RFC 9728)**
- `POST /oauth/register` - **Dynamic Client Registration (RFC 7591)**
- `GET /oauth/authorize` - **OAuth 2.0 Autorización** (para ChatGPT)
- `POST /oauth/token` - **OAuth 2.0 Token Exchange** (para ChatGPT)
- `GET /oauth/credentials` - Obtener credenciales OAuth para configuración
- `GET /tools` - Listar herramientas REST
- `POST /call_tool` - Ejecutar herramienta REST
- `POST /webhook/n8n` - Webhook REST para N8N

### Integración con N8N

**Configuración del nodo MCP en N8N:**
1. Server Transport: `HTTP Streamable`
2. Endpoint: `https://tu-dominio.repl.co/mcp/` (incluir `/` al final)
3. Authentication: `Bearer Auth`
4. Token: API key (ej: `test_key_123`) o JWT

Ver [N8N_SETUP.md](./N8N_SETUP.md) para instrucciones detalladas.

### Integración con ChatGPT

**Configuración de OAuth en ChatGPT:**
1. Obtén credenciales: `GET https://tu-dominio.repl.co/oauth/credentials`
2. Crea conector personalizado en ChatGPT
3. Configura OAuth con las credenciales obtenidas
4. Authorization URL: `https://tu-dominio.repl.co/oauth/authorize`
5. Token URL: `https://tu-dominio.repl.co/oauth/token`

Ver [CHATGPT_OAUTH_SETUP.md](./CHATGPT_OAUTH_SETUP.md) para instrucciones paso a paso.

### Modo stdio

Para Claude Desktop, configurar `SERVER_MODE=stdio` en variables de entorno.

## Estado Actual

- ✅ Estructura del proyecto creada
- ✅ Sistema de autenticación multi-método (API Keys, JWT, OAuth 2.0)
- ✅ **OAuth 2.0 RFC 6749 completo para ChatGPT**:
  - ✅ Authorization Code Flow con Refresh Tokens
  - ✅ HTTP Basic Auth para credenciales de cliente (estándar ChatGPT)
  - ✅ Form-encoded credentials (RFC 6749)
  - ✅ Auto-detección de URL pública desde Replit
  - ✅ **OAuth Discovery Endpoints** (RFC 8414 y RFC 9728):
    - ✅ `/.well-known/oauth-authorization-server`
    - ✅ `/.well-known/oauth-protected-resource`
  - ✅ **Dynamic Client Registration** (RFC 7591):
    - ✅ Endpoint `POST /oauth/register`
    - ✅ Clientes públicos sin client_secret
    - ✅ Registro automático de ChatGPT
- ✅ Cliente Odoo mejorado
- ✅ 7 herramientas MCP optimizadas con FastMCP y Pydantic
- ✅ Servidor HTTP con FastAPI
- ✅ **MCP HTTP Streamable en /mcp (soporte completo para N8N)**
- ✅ **Schemas JSON corregidos con `json_schema_extra`** - Soluciona error "array schema missing items"
- ✅ **Soporte completo para filtros Odoo complejos** - Incluyendo `['id', 'in', [1,2,3]]`
- ✅ Servidor stdio
- ✅ Sistema de caché
- ✅ Logging estructurado
- ✅ Documentación completa + guía N8N + guía ChatGPT OAuth + prompts maestros

## Próximos Pasos Sugeridos

1. Configurar credenciales de Odoo en Secrets
2. Probar con una instancia demo de Odoo
3. Integrar con N8N o Claude Desktop
4. Agregar rate limiting
5. Implementar sistema de permisos granulares
6. Dashboard de monitoreo

## Versión

2.0.0 - Mejorado por Replit Agent (Octubre 2025)

Basado en: https://github.com/vzeman/odoo-mcp-server
