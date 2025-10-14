# Configuración de N8N con Servidor MCP de Odoo

## Pasos para conectar N8N al servidor MCP

### 1. Obtener la URL del servidor

Tu servidor MCP está corriendo en:
```
https://tu-dominio-replit.repl.co/mcp
```

O si usas ngrok u otro túnel:
```
https://tu-subdominio.ngrok-free.app/mcp
```

### 2. Configurar el nodo MCP en N8N

1. En N8N, agrega un nodo **"MCP"**
2. Configura los siguientes campos:

| Campo | Valor |
|-------|-------|
| **Server Transport** | `HTTP Streamable` |
| **Endpoint** | `https://tu-dominio.repl.co/mcp/` (nota la `/` al final) |
| **Authentication** | `Bearer Auth` |
| **Bearer Token** | Tu API key (ej: `test_key_123`) o JWT token |

**Nota importante**: Asegúrate de incluir la barra final `/` en la URL del endpoint. El servidor MCP requiere `/mcp/` para funcionar correctamente.

### 3. Opciones de autenticación

#### Opción A: Usar API Key (Más Simple)

1. Usa una de las API keys configuradas en las variables de entorno `API_KEYS`
2. Por defecto, el servidor incluye: `test_key_123` y `demo_key_456`
3. En N8N, pon este valor directamente en "Bearer Token"

#### Opción B: Usar JWT Token

1. Primero, obtén un JWT token del servidor:
```bash
curl -X POST https://tu-dominio.repl.co/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tu_usuario_odoo",
    "password": "tu_contraseña_odoo"
  }'
```

2. Usa el `access_token` recibido en N8N como Bearer Token

### 4. Verificar la conexión

Una vez configurado, N8N debería mostrar las 7 herramientas disponibles:

- ✅ `odoo_search_records`
- ✅ `odoo_read_records`
- ✅ `odoo_search_read_records`
- ✅ `odoo_create_record`
- ✅ `odoo_update_record`
- ✅ `odoo_delete_record`
- ✅ `odoo_get_model_fields`

### 5. Solución de problemas

#### Error 405 Method Not Allowed

✅ **Solucionado**: El servidor ahora soporta el protocolo MCP HTTP Streamable en `/mcp`

#### Error 401 Unauthorized

- Verifica que el Bearer Token sea correcto
- Asegúrate de usar una API key válida de `API_KEYS`
- O que el JWT token no haya expirado (válido por 30 minutos)

#### Error de conexión

1. Verifica que el servidor esté corriendo
2. Comprueba que la URL sea accesible desde N8N
3. Si usas ngrok, asegúrate de que esté activo

### 6. Ejemplo de uso en N8N

**Workflow de ejemplo: Buscar clientes**

1. Nodo MCP configurado
2. Selecciona herramienta: `odoo_search_read_records`
3. Argumentos:
```json
{
  "model": "res.partner",
  "domain": [["customer_rank", ">", 0]],
  "fields": ["name", "email", "phone"],
  "limit": 10
}
```

**Resultado esperado:**
```json
{
  "success": true,
  "records": [
    {
      "id": 1,
      "name": "Cliente Ejemplo",
      "email": "cliente@ejemplo.com",
      "phone": "+1234567890"
    }
  ],
  "count": 1
}
```

## Configuración de credenciales de Odoo

Para que las herramientas funcionen, configura estas variables de entorno en Replit Secrets:

```
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=tu_base_datos  
ODOO_USERNAME=tu_usuario
ODOO_PASSWORD=tu_contraseña
```

## Endpoints alternativos

Si prefieres no usar el nodo MCP de N8N, puedes usar el nodo "HTTP Request" con:

**POST** `https://tu-dominio.repl.co/webhook/n8n`

Headers:
```
Authorization: Bearer test_key_123
Content-Type: application/json
```

Body:
```json
{
  "tool": "odoo_search_records",
  "arguments": {
    "model": "res.partner",
    "domain": [["name", "ilike", "test"]],
    "limit": 5
  }
}
```

## Recursos adicionales

- Documentación API: `https://tu-dominio.repl.co/docs`
- Health check: `https://tu-dominio.repl.co/health`
- Listar herramientas: `https://tu-dominio.repl.co/tools` (requiere autenticación)
