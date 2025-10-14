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
- `GET /tools` - Listar herramientas REST
- `POST /call_tool` - Ejecutar herramienta REST
- `POST /webhook/n8n` - Webhook REST para N8N

### Integración con N8N

**Configuración del nodo MCP en N8N:**
1. Server Transport: `HTTP Streamable`
2. Endpoint: `https://tu-dominio.repl.co/mcp`
3. Authentication: `Bearer Auth`
4. Token: API key (ej: `test_key_123`) o JWT

Ver [N8N_SETUP.md](./N8N_SETUP.md) para instrucciones detalladas.

### Modo stdio

Para Claude Desktop, configurar `SERVER_MODE=stdio` en variables de entorno.

## Estado Actual

- ✅ Estructura del proyecto creada
- ✅ Sistema de autenticación implementado y corregido
- ✅ Cliente Odoo mejorado
- ✅ 7 herramientas MCP optimizadas con FastMCP
- ✅ Servidor HTTP con FastAPI
- ✅ **MCP HTTP Streamable en /mcp (soporte completo para N8N)**
- ✅ Servidor stdio
- ✅ Sistema de caché
- ✅ Logging estructurado
- ✅ Documentación completa + guía N8N

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
