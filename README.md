# Servidor MCP Mejorado para Odoo 🚀

Un servidor Model Context Protocol (MCP) híbrido mejorado que permite a asistentes de IA interactuar con sistemas Odoo ERP. Compatible con **N8N**, **ChatGPT**, **Claude Desktop** y otros agentes de IA.

## 🎯 Características Principales

### ✨ Mejoras sobre el Repositorio Original

1. **🔐 Autenticación Robusta**
   - API Keys para acceso directo (configuradas en variables de entorno)
   - JWT Tokens para sesiones seguras (validadas contra credenciales de Odoo)
   - **OAuth 2.0 RFC 6749 completo** para ChatGPT:
     - Authorization Code Flow con Refresh Tokens
     - HTTP Basic Auth para credenciales de cliente (compatible ChatGPT)
     - Form-encoded credentials como fallback
     - Auto-detección de URL pública desde Replit
   - Sistema de autenticación multi-método con validación real

2. **🤖 Optimizado para LLMs**
   - Descripciones detalladas de herramientas
   - Schemas enriquecidos con ejemplos
   - Mensajes de error claros y accionables
   - Sugerencias automáticas para solucionar problemas

3. **⚡ Rendimiento Mejorado**
   - Sistema de caché opcional (Redis)
   - Reintentos automáticos con backoff exponencial
   - Manejo robusto de errores

4. **📊 Monitoreo y Logging**
   - Logging estructurado (JSON o consola)
   - Trazabilidad completa de requests
   - Health checks y métricas

5. **🔌 Integración Completa**
   - Modo HTTP para N8N y agentes web
   - Modo stdio para Claude Desktop
   - Documentación OpenAPI/Swagger automática
   - Endpoints específicos para N8N

## 🛠️ Herramientas MCP Disponibles

El servidor proporciona 7 herramientas optimizadas para trabajar con Odoo:

| Herramienta | Descripción | Uso Principal |
|------------|-------------|---------------|
| `odoo_search_records` | Buscar registros con filtros | Encontrar clientes, pedidos, productos |
| `odoo_read_records` | Leer datos de registros | Obtener detalles completos |
| `odoo_search_read_records` | Buscar y leer en una llamada | Operación combinada eficiente |
| `odoo_create_record` | Crear nuevos registros | Agregar clientes, productos, pedidos |
| `odoo_update_record` | Actualizar registros existentes | Modificar datos |
| `odoo_delete_record` | Eliminar registros | Borrar datos (con precaución) |
| `odoo_get_model_fields` | Obtener esquema del modelo | Descubrir campos disponibles |

Cada herramienta incluye:
- Descripciones detalladas y fáciles de entender para LLMs
- Ejemplos de uso prácticos
- Explicación de parámetros
- Casos de error comunes y cómo evitarlos

## 📦 Instalación

### Requisitos

- Python 3.10 o superior
- Acceso a una instancia de Odoo
- (Opcional) Redis para caché

### Instalación Rápida

```bash
# Clonar el repositorio
git clone <tu-repo>
cd odoo-mcp-server

# Instalar dependencias
pip install -e .

# Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus credenciales de Odoo
```

### Variables de Entorno

Edita el archivo `.env` con tus credenciales:

```env
# Configuración de Odoo (REQUERIDO)
ODOO_URL=https://tu-instancia-odoo.com
ODOO_DB=nombre_base_datos
ODOO_USERNAME=tu_usuario
ODOO_PASSWORD=tu_contraseña

# Modo del servidor
SERVER_MODE=http  # o "stdio" para Claude Desktop

# Autenticación (modo HTTP)
SECRET_KEY=tu-clave-secreta-segura
API_KEYS=clave_prueba_123,otra_clave_456

# Opcional: Redis para caché
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
```

## 🚀 Uso

### Modo 1: HTTP Server (para N8N, ChatGPT, agentes web)

Perfecto para integrar con N8N, APIs web y herramientas externas.

```bash
# Iniciar servidor HTTP
python -m mcp_server_odoo

# El servidor estará disponible en http://0.0.0.0:5000
```

#### Endpoints Disponibles

- `GET /` - Información del servidor
- `GET /health` - Health check
- `GET /docs` - Documentación Swagger interactiva
- `POST /login` - Obtener JWT token
- `GET /.well-known/oauth-authorization-server` - OAuth Discovery (RFC 8414)
- `GET /.well-known/oauth-protected-resource` - Resource Discovery (RFC 9728)
- `GET /oauth/authorize` - OAuth authorization endpoint
- `POST /oauth/token` - OAuth token endpoint
- `GET /oauth/credentials` - Obtener credenciales OAuth para configuración
- `GET /tools` - Listar herramientas disponibles
- `POST /call_tool` - Ejecutar una herramienta
- `POST /webhook/n8n` - Endpoint específico para N8N

#### Ejemplo con cURL

```bash
# Opción 1: Usar API Key directamente (más simple)
curl -X POST http://localhost:5000/call_tool \
  -H "Authorization: Bearer clave_prueba_123" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "odoo_search_records",
    "arguments": {
      "model": "res.partner",
      "domain": [["name", "ilike", "John"]],
      "limit": 5
    }
  }'

# Opción 2: Obtener JWT token primero (usa credenciales de Odoo)
# 2a. Login para obtener token
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tu_usuario_odoo",
    "password": "tu_contraseña_odoo"
  }'

# 2b. Usar el token recibido
curl -X POST http://localhost:5000/call_tool \
  -H "Authorization: Bearer <token_jwt_recibido>" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "odoo_search_records",
    "arguments": {
      "model": "res.partner",
      "domain": [["name", "ilike", "John"]],
      "limit": 5
    }
  }'
```

**Nota de Seguridad**: 
- **API Keys**: Configuradas en `API_KEYS` (variable de entorno), proveen acceso directo
- **JWT Login**: Valida contra las credenciales de Odoo (`ODOO_USERNAME` y `ODOO_PASSWORD`), luego genera un token temporal

#### Integración con N8N

**Método 1: Usar el nodo MCP (Recomendado)**

1. Agregar nodo "MCP" en N8N
2. Configurar:
   - **Server Transport**: `HTTP Streamable`
   - **Endpoint**: `https://tu-dominio.repl.co/mcp/` (incluir `/` final)
   - **Authentication**: `Bearer Auth`
   - **Bearer Token**: Tu API key (ej: `test_key_123`) o JWT token
3. N8N mostrará las 7 herramientas de Odoo disponibles automáticamente

**Nota**: Es importante incluir la barra final `/` en la URL del endpoint MCP.

**Método 2: Usar HTTP Request (Alternativo)**

1. Agregar nodo "HTTP Request"
2. Configurar:
   - **Method**: POST
   - **URL**: `https://tu-servidor:5000/webhook/n8n`
   - **Authentication**: Bearer Token
   - **Token**: Tu API key
   - **Body**: JSON con `tool` y `arguments`

Ver [N8N_SETUP.md](./N8N_SETUP.md) para instrucciones detalladas.

**⚠️ Importante - Corrección de Schema:** Si ves el error "array schema missing items", consulta [SCHEMA_FIX.md](./SCHEMA_FIX.md) para la solución.

### Modo 2: stdio (para Claude Desktop)

Ideal para usar con Claude Desktop en tu computadora local.

#### Configuración en Claude Desktop

Edita `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["-m", "mcp_server_odoo"],
      "env": {
        "ODOO_URL": "https://tu-instancia.odoo.com",
        "ODOO_DB": "tu_base_datos",
        "ODOO_USERNAME": "tu_usuario",
        "ODOO_PASSWORD": "tu_contraseña",
        "SERVER_MODE": "stdio"
      }
    }
  }
}
```

Reinicia Claude Desktop y las herramientas de Odoo aparecerán automáticamente.

## 🔧 Ejemplos de Uso con LLMs

### Ejemplo 1: Buscar Clientes

```
Usuario: "Muéstrame los clientes que tienen 'Tech' en su nombre"

Asistente usa:
- Tool: odoo_search_read_records
- Arguments:
  {
    "model": "res.partner",
    "domain": [["name", "ilike", "Tech"], ["customer_rank", ">", 0]],
    "fields": ["name", "email", "phone", "city"],
    "limit": 10
  }
```

### Ejemplo 2: Crear Producto

```
Usuario: "Crea un nuevo producto llamado 'Laptop Pro' con precio $1299"

Asistente usa:
- Tool: odoo_get_model_fields (primero, para ver campos requeridos)
- Arguments: {"model": "product.product"}

Luego:
- Tool: odoo_create_record
- Arguments:
  {
    "model": "product.product",
    "values": {
      "name": "Laptop Pro",
      "list_price": 1299.00,
      "type": "consu"
    }
  }
```

### Ejemplo 3: Actualizar Pedido

```
Usuario: "Marca el pedido SO042 como urgente"

Asistente:
1. Busca el pedido: odoo_search_records con domain [["name", "=", "SO042"]]
2. Actualiza: odoo_update_record con values {"priority": "1"}
```

## 🔍 Modelos Odoo Comunes

| Modelo | Descripción | Campos Comunes |
|--------|-------------|----------------|
| `res.partner` | Contactos/Clientes | name, email, phone, street, city |
| `product.product` | Productos | name, list_price, default_code, qty_available |
| `sale.order` | Pedidos de venta | name, partner_id, date_order, amount_total |
| `account.move` | Facturas | name, partner_id, invoice_date, amount_total |
| `stock.picking` | Transferencias | name, partner_id, state, scheduled_date |
| `purchase.order` | Órdenes de compra | name, partner_id, date_order, amount_total |

## 🐛 Solución de Problemas

### Error de Autenticación

```bash
# Verifica credenciales
curl http://localhost:5000/health

# Si falla, revisa tu .env:
# - ODOO_URL debe incluir https:// 
# - ODOO_DB debe ser el nombre exacto de la base de datos
# - Usuario y contraseña deben ser correctos
```

### Error "Model not found"

```bash
# Usa el nombre técnico del modelo, no el nombre de visualización
# Correcto: "res.partner"
# Incorrecto: "Contact" o "Contacto"

# Para ver modelos disponibles, usa odoo_search_records con model="ir.model"
```

### Timeout en operaciones

```bash
# Aumenta el timeout en .env:
ODOO_TIMEOUT=60
ODOO_MAX_RETRIES=5
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│     Clientes (N8N, ChatGPT, Claude)     │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
    ┌───▼────┐        ┌────▼─────┐
    │  HTTP  │        │  stdio   │
    │ Server │        │  Server  │
    └───┬────┘        └────┬─────┘
        │                  │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  Odoo Client     │
        │  - Autenticación │
        │  - Reintentos    │
        │  - Caché         │
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  Odoo XML-RPC    │
        │  API             │
        └──────────────────┘
```

## 📝 Mejoras Futuras

Ideas para próximas versiones:

- ✅ Rate limiting por API key
- ✅ Sistema de permisos granulares
- ✅ Dashboard de monitoreo
- ✅ Batching de operaciones
- ✅ Webhooks de Odoo en tiempo real
- ✅ Soporte para múltiples instancias de Odoo
- ✅ Exportación/importación de datos masivos

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Este proyecto está basado en [odoo-mcp-server](https://github.com/vzeman/odoo-mcp-server) con mejoras significativas.

## 📄 Licencia

GPL-3.0 License - Ver archivo LICENSE

## 🙏 Agradecimientos

- Proyecto original: [vzeman/odoo-mcp-server](https://github.com/vzeman/odoo-mcp-server)
- Model Context Protocol by Anthropic
- Comunidad de Odoo

---

**¿Necesitas ayuda?** Revisa la [documentación de Odoo](https://www.odoo.com/documentation) o la [especificación de MCP](https://modelcontextprotocol.io/).
