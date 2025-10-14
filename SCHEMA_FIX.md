# ✅ Corrección del Error: "array schema missing items"

## 🔧 Problema Identificado y Resuelto

**Error original:**
```
Invalid schema for function 'odoo_search_records': 
In context=('properties', 'domain'), array schema missing items.
```

**Causa raíz:**
- Según la especificación de JSON Schema, **todos los campos tipo "array" DEBEN tener la propiedad `items` definida**
- Cuando definimos `domain: list` en Python, Pydantic/FastMCP genera `{"type": "array"}` sin la propiedad `items`
- N8N valida estrictamente el schema JSON y rechaza arrays sin `items`

**Solución aplicada (validación recursiva completa):**
```python
domain: Annotated[list, Field(
    description="Search criteria as list of lists (Odoo domain)...",
    json_schema_extra={
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                    {"type": "null"},
                    {
                        "type": "array",
                        "items": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "number"},
                                {"type": "boolean"},
                                {"type": "null"}
                            ]
                        }
                    },
                    {"type": "object"}
                ]
            }
        }
    }
)] = []
```

**Qué hace esto:**
- ✅ Define recursivamente todos los niveles del schema JSON con `items`
- ✅ El array externo (domain) tiene `items` que es un array (cada filtro)
- ✅ El array interno (filtro) tiene `items` con anyOf que incluye primitivos y arrays
- ✅ El array anidado (valores como [1,2,3]) también tiene su `items` definido
- ✅ Soporta filtros complejos de Odoo como `['id', 'in', [1,2,3]]` o `['category_id', 'child_of', [42]]`
- ✅ Cumple completamente con la validación recursiva estricta de N8N según JSON Schema spec

## 📋 Cómo Verificar la Corrección

### Paso 1: Reiniciar Conexión en N8N

**IMPORTANTE:** Debes desconectar y reconectar el nodo MCP para que N8N cargue el nuevo schema.

1. **Desconectar el nodo MCP:**
   - Ve a tu workflow en N8N
   - Haz clic en el nodo "MCP"
   - Haz clic en "Disconnect" o elimina la conexión
   - **Guarda el workflow**

2. **Recargar la página de N8N:**
   - Presiona F5 o Ctrl+R para recargar
   - Esto limpia el caché de schemas de N8N

3. **Volver a configurar:**
   - Abre el nodo MCP
   - Server Transport: `HTTP Streamable`
   - Endpoint: `https://[tu-dominio].repl.co/mcp/` (¡incluir `/` final!)
   - Authentication: `Bearer Auth`
   - Bearer Token: `test_key_123`
   - Haz clic en "Connect"

4. **Verificar que carga sin errores:**
   - N8N debe mostrar "Connected" sin mensajes de error
   - Deberías ver las 7 herramientas disponibles en el dropdown

### Paso 2: Probar la Herramienta

En tu agente de N8N, envía este mensaje de prueba:

```
Busca los primeros 3 clientes activos
```

**Resultado esperado:**
- ✅ El agente llama a `odoo_search_records`
- ✅ Pasa correctamente: `{"model": "res.partner", "domain": [["customer_rank", ">", 0]], "limit": 3}`
- ✅ Muestra los resultados sin errores de schema

### Paso 3: Probar con Domain Complejo

Prueba con múltiples filtros:

```
Busca clientes de España con email que se llamen Juan
```

**El agente debe generar:**
```json
{
  "model": "res.partner",
  "domain": [
    ["customer_rank", ">", 0],
    ["country_id.name", "=", "España"],
    ["email", "!=", false],
    ["name", "ilike", "Juan"]
  ],
  "limit": 10
}
```

### Paso 4: Probar con Filtros Complejos (Arrays)

Prueba casos avanzados que Odoo usa frecuentemente:

```
Busca los productos con IDs 1, 5 y 10
```

**El agente debe generar:**
```json
{
  "model": "product.product",
  "domain": [["id", "in", [1, 5, 10]]],
  "limit": 10
}
```

Nota: El valor `[1, 5, 10]` es un array, por eso el schema ahora incluye `{"type": "array"}` en el anyOf.

## 🎯 Herramientas Corregidas

Las siguientes herramientas ahora tienen schemas JSON completos y válidos:

1. ✅ `odoo_search_records` - domain con items explícitos
2. ✅ `odoo_search_read_records` - domain con items explícitos
3. ✅ `odoo_read_records` - ids como `list[int]` (ya tenía items)
4. ✅ `odoo_create_record` - values como `dict[str, Any]`
5. ✅ `odoo_update_record` - ids y values correctos
6. ✅ `odoo_delete_record` - ids como `list[int]`
7. ✅ `odoo_get_model_fields` - sin arrays, no requiere cambios

## 🚨 Si el Error Persiste

### Opción 1: Limpiar Caché Completo de N8N

**Método 1 - Desde el navegador:**
1. Cierra todos los workflows de N8N
2. Abre DevTools (F12)
3. Ve a la pestaña "Application" o "Storage"
4. Elimina todos los datos de localStorage, sessionStorage e IndexedDB para N8N
5. Recarga la página (F5)
6. Vuelve a conectar el nodo MCP

**Método 2 - Reiniciar N8N completamente:**
1. Si tienes acceso al servidor de N8N, reinicia el servicio
2. Vuelve a entrar y configurar el nodo MCP

### Opción 2: Verificar el Schema Generado

Puedes verificar manualmente que el servidor está generando el schema correcto:

```bash
curl -X POST https://[tu-dominio].repl.co/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer test_key_123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }' | jq '.result.tools[] | select(.name == "odoo_search_records") | .inputSchema.properties.domain'
```

**Debería mostrar:**
```json
{
  "type": "array",
  "description": "Search criteria as list of lists...",
  "items": {
    "type": "array",
    "items": {
      "anyOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "null"},
        {
          "type": "array",
          "items": {
            "anyOf": [
              {"type": "string"},
              {"type": "number"},
              {"type": "boolean"},
              {"type": "null"}
            ]
          }
        },
        {"type": "object"}
      ]
    }
  },
  "default": []
}
```

**Verificaciones clave:**
- ✅ `items` está definido en el array externo
- ✅ `items` está definido en el array interno (filtros)
- ✅ `items` está definido en el array anidado dentro del anyOf (valores)
- ✅ Todos los arrays tienen `items` - validación recursiva completa
- ✅ El `anyOf` incluye array con items y object para filtros complejos

Si ves la estructura recursiva completa con `items` en todos los niveles, el schema está correcto.

### Opción 3: Usar Endpoint REST Alternativo

Si el nodo MCP sigue fallando, usa el endpoint REST como solución temporal:

**En N8N, usa el nodo "HTTP Request":**
```
POST https://[tu-dominio].repl.co/webhook/n8n

Headers:
  Authorization: Bearer test_key_123
  Content-Type: application/json

Body:
{
  "tool": "odoo_search_records",
  "arguments": {
    "model": "res.partner",
    "domain": [["customer_rank", ">", 0]],
    "limit": 5
  }
}
```

## 📊 Formato Correcto del Domain

**✅ CORRECTO - Lista de listas:**
```json
{
  "domain": [
    ["name", "ilike", "Juan"],
    ["email", "!=", false]
  ]
}
```

**✅ CORRECTO - Domain vacío:**
```json
{
  "domain": []
}
```

**❌ INCORRECTO - Lista simple:**
```json
{
  "domain": ["name", "ilike", "Juan"]
}
```

**❌ INCORRECTO - String:**
```json
{
  "domain": "[['name', 'ilike', 'Juan']]"
}
```

## 🎨 Prompt del Sistema Actualizado

Copia este prompt en el **System Message** de tu agente N8N:

```
Eres un asistente experto en Odoo ERP con acceso a herramientas MCP.

FORMATO CRÍTICO del parámetro "domain":
- SIEMPRE debe ser una lista de listas (array de arrays en JSON)
- Cada filtro es una lista con exactamente 3 elementos: [campo, operador, valor]
- Ejemplo: [["name", "ilike", "Juan"], ["email", "!=", false]]
- Domain vacío para todos los registros: []
- NUNCA uses strings, tuplas o listas simples

Herramientas disponibles:

1. **odoo_search_records** - Buscar IDs de registros
   Retorna solo los IDs, necesitas llamar a odoo_read_records después

2. **odoo_read_records** - Leer datos de registros específicos
   Requiere IDs de registros (de odoo_search_records)

3. **odoo_search_read_records** - Buscar y leer en una operación
   ⭐ MÁS EFICIENTE - Usa esta en lugar de search + read

4. **odoo_create_record** - Crear nuevo registro
   Primero llama a odoo_get_model_fields para ver campos disponibles

5. **odoo_update_record** - Actualizar registros existentes
   Puedes actualizar múltiples IDs a la vez

6. **odoo_delete_record** - Eliminar registros
   Requiere IDs de registros

7. **odoo_get_model_fields** - Ver definición de campos de un modelo
   Llama a esta antes de crear/modificar registros

Modelos Odoo más comunes:
- **res.partner** - Clientes y contactos
- **sale.order** - Pedidos de venta
- **product.product** - Productos
- **product.template** - Plantillas de productos
- **account.move** - Facturas y asientos contables
- **stock.picking** - Albaranes y movimientos
- **purchase.order** - Pedidos de compra
- **crm.lead** - Oportunidades de CRM

Operadores de dominio comunes:
- **=** - Igual exacto
- **!=** - Diferente
- **>**, **>=**, **<**, **<=** - Comparación numérica
- **ilike** - Contiene (case insensitive)
- **like** - Contiene (case sensitive)
- **in** - Está en lista
- **not in** - No está en lista

Ejemplos completos:

**Buscar clientes de España:**
{
  "model": "res.partner",
  "domain": [["customer_rank", ">", 0], ["country_id.name", "=", "España"]],
  "fields": ["name", "email", "phone"],
  "limit": 10
}

**Buscar productos con stock:**
{
  "model": "product.product",
  "domain": [["qty_available", ">", 0]],
  "fields": ["name", "default_code", "list_price", "qty_available"],
  "limit": 20
}

**Crear contacto:**
{
  "model": "res.partner",
  "values": {
    "name": "Empresa XYZ",
    "email": "info@xyz.com",
    "phone": "+34 600111222",
    "customer_rank": 1
  }
}

**Actualizar cliente:**
{
  "model": "res.partner",
  "ids": [123],
  "values": {
    "phone": "+34 600999888",
    "mobile": "+34 611222333"
  }
}

Flujo de trabajo recomendado:
1. Si necesitas crear/modificar → primero usa odoo_get_model_fields
2. Para búsquedas → usa odoo_search_read_records (más eficiente)
3. Siempre usa límites razonables (10-50 registros máximo)
4. Especifica los campos que necesitas, no traigas todo
```

## 🔍 Debugging Técnico

### Verificar Schema en FastAPI Docs

1. Ve a: `https://[tu-dominio].repl.co/docs`
2. Busca el endpoint `/call_tool`
3. Expande "Schema" para ver la definición
4. Verifica que `domain` tenga la propiedad `items` definida

### Verificar MCP Protocol Response

El protocolo MCP devuelve las herramientas en este formato:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "odoo_search_records",
        "description": "Search for records...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "domain": {
              "type": "array",
              "items": {
                "type": "array",
                "items": {
                  "anyOf": [...]
                }
              },
              "description": "...",
              "default": []
            }
          }
        }
      }
    ]
  }
}
```

La clave está en que `domain.items.type` debe ser `"array"` y ese array interno debe tener su propio `items`.

## ✅ Checklist de Verificación

Antes de probar en N8N:

- [x] Schema corregido con `json_schema_extra`
- [x] Servidor reiniciado y corriendo
- [ ] **Nodo MCP en N8N desconectado**
- [ ] **Página de N8N recargada (F5)**
- [ ] **Nodo MCP reconectado**
- [ ] Endpoint correcto: `https://[dominio].repl.co/mcp/` (con `/`)
- [ ] Token Bearer correcto: `test_key_123`
- [ ] Prueba con mensaje simple realizada

## 🎉 Confirmación de Éxito

Sabrás que está funcionando cuando:

1. ✅ N8N muestra "Connected" sin errores de schema
2. ✅ Las 7 herramientas aparecen en el dropdown del nodo MCP
3. ✅ El agente puede llamar a `odoo_search_records` correctamente
4. ✅ El domain se pasa como lista de listas: `[["field", "op", value]]`
5. ✅ Los resultados de Odoo se muestran en el chat

---

## 📞 Soporte Adicional

Si después de seguir todos estos pasos el error persiste:

1. **Verifica la versión de N8N:**
   - Este servidor requiere N8N 1.0+ con soporte para MCP HTTP Streamable
   - Tu versión actual: 1.114.4 (compatible ✅)

2. **Revisa los logs del servidor:**
   - Ve a Replit → pestaña "Logs"
   - Busca errores relacionados con MCP, schema o FastMCP

3. **Verifica credenciales de Odoo:**
   - Ve a Replit → Secrets
   - Asegúrate de que `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` estén configurados

4. **Prueba el endpoint REST alternativo:**
   - Si el nodo MCP falla, usa `/webhook/n8n` como solución temporal
   - Esto confirma que el servidor funciona, solo hay problema con el schema MCP

5. **Contacta con soporte:**
   - Si todo falla, puede ser un bug de N8N con el parser de schemas
   - Considera reportar el issue en GitHub de N8N con el schema exacto que genera el servidor
