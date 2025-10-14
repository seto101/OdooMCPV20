# ✅ Corrección del Error: "array schema missing items"

## 🔧 Problema Identificado y Resuelto

**Error original:**
```
Invalid schema for function 'odoo_search_records': 
In context=('properties', 'domain', 'items'), array schema missing items.
```

**Causa raíz:**
- El parámetro `domain` estaba definido como `list[list[Any]]` (array anidado con tipos genéricos)
- Pydantic/FastMCP generaba un schema JSON donde el array interno no tenía la propiedad `items` correctamente definida
- N8N requiere que todos los arrays en JSON Schema tengan la propiedad `items` especificada

**Solución aplicada:**
- ✅ Cambié el tipo de `domain` de `list[list[Any]]` a `list` (tipo genérico)
- ✅ Esto genera un schema JSON más simple y válido: `{"type": "array"}` sin restricciones en items
- ✅ N8N acepta este schema porque es sintácticamente correcto según JSON Schema

## 📋 Cómo Verificar la Corrección

### Paso 1: Reiniciar Conexión en N8N

1. **Desconectar el nodo MCP:**
   - Ve a tu workflow en N8N
   - Haz clic en el nodo "MCP"
   - Desconéctalo y vuelve a conectarlo

2. **Volver a configurar:**
   - Server Transport: `HTTP Streamable`
   - Endpoint: `https://tu-dominio.repl.co/mcp/` (¡incluir `/` final!)
   - Authentication: `Bearer Auth`
   - Bearer Token: `test_key_123`

### Paso 2: Probar la Herramienta

En tu agente de N8N, envía este mensaje de prueba:

```
Busca los primeros 3 clientes activos
```

**Resultado esperado:**
- ✅ El agente debe llamar a `odoo_search_records` sin errores
- ✅ Debe pasar correctamente el parámetro domain: `[["customer_rank", ">", 0]]`
- ✅ Debe mostrar los resultados

### Paso 3: Probar con Domain Complejo

Prueba con un filtro más específico:

```
Busca clientes de España con email
```

**El agente debe generar:**
```json
{
  "model": "res.partner",
  "domain": [
    ["customer_rank", ">", 0],
    ["country_id.name", "=", "España"],
    ["email", "!=", false]
  ],
  "limit": 10
}
```

## 🎯 Herramientas Corregidas

Las siguientes herramientas ahora tienen schemas JSON válidos:

1. ✅ `odoo_search_records` - domain como `list`
2. ✅ `odoo_search_read_records` - domain como `list`
3. ✅ `odoo_read_records` - ids como `list[int]`
4. ✅ `odoo_create_record` - values como `dict[str, Any]`
5. ✅ `odoo_update_record` - ids y values con tipos correctos
6. ✅ `odoo_delete_record` - ids como `list[int]`
7. ✅ `odoo_get_model_fields` - sin cambios necesarios

## 🚨 Si el Error Persiste

Si después de reiniciar N8N aún ves el error:

### Opción 1: Limpiar Caché de N8N

1. Detén el workflow
2. Desconecta el nodo MCP
3. Guarda el workflow
4. Recarga la página de N8N (F5)
5. Vuelve a conectar el nodo MCP

### Opción 2: Verificar Versión de N8N

El error puede ocurrir en versiones antiguas de N8N. Tu versión es:
- **N8N**: 1.114.4 (Self Hosted)

Considera actualizar a la última versión si el problema persiste.

### Opción 3: Usar Endpoint REST Alternativo

Si el nodo MCP sigue fallando, usa el endpoint REST como alternativa temporal:

**En lugar del nodo MCP, usa "HTTP Request":**
```
POST https://tu-dominio.repl.co/webhook/n8n

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

**❌ INCORRECTO - Lista simple:**
```json
{
  "domain": ["name", "ilike", "Juan"]
}
```

**❌ INCORRECTO - Tuplas (Python):**
```python
domain = [("name", "ilike", "Juan")]  # Solo en código Python, no en JSON
```

## 🔍 Debugging

Para verificar que el servidor está generando el schema correcto:

1. **Verifica que el servidor esté corriendo:**
   ```bash
   curl https://tu-dominio.repl.co/
   ```
   
   Debería responder:
   ```json
   {
     "name": "Odoo MCP Server",
     "version": "2.0.0",
     "status": "running"
   }
   ```

2. **Verifica el health check:**
   ```bash
   curl https://tu-dominio.repl.co/health
   ```

3. **Revisa los logs del servidor:**
   - Ve a Replit
   - Abre la pestaña "Logs"
   - Busca errores relacionados con MCP o schema

## 📝 Prompt del Sistema Actualizado

Usa este prompt en el System Message de tu agente N8N:

```
Eres un asistente experto en Odoo ERP. Tienes acceso a herramientas MCP para interactuar con Odoo.

IMPORTANTE: Al usar herramientas de búsqueda (odoo_search_records, odoo_search_read_records):
- El parámetro "domain" DEBE ser una lista de listas (array de arrays)
- Cada filtro es una lista con 3 elementos: [campo, operador, valor]
- Ejemplo correcto: [["name", "ilike", "Juan"], ["email", "!=", false]]
- NUNCA uses tuplas o listas simples

Ejemplos de uso:

1. Buscar clientes:
{
  "model": "res.partner",
  "domain": [["customer_rank", ">", 0]],
  "limit": 10
}

2. Buscar productos en stock:
{
  "model": "product.product",
  "domain": [["qty_available", ">", 0]],
  "fields": ["name", "list_price"],
  "limit": 20
}

3. Crear contacto:
{
  "model": "res.partner",
  "values": {
    "name": "Empresa XYZ",
    "email": "info@xyz.com",
    "phone": "+34 600111222"
  }
}
```

## ✅ Checklist de Verificación

Antes de probar en N8N, verifica:

- [ ] Servidor MCP corriendo en Replit (puerto 5000)
- [ ] Credenciales de Odoo configuradas en Secrets
- [ ] Endpoint MCP: `https://[tu-dominio].repl.co/mcp/` (con `/` final)
- [ ] Token Bearer correcto: `test_key_123`
- [ ] Nodo MCP en N8N configurado con "HTTP Streamable"
- [ ] Workflow guardado y recargado después de cambios

## 🎉 Confirmación de Éxito

Sabrás que está funcionando cuando:

1. ✅ El nodo MCP en N8N muestra las 7 herramientas disponibles
2. ✅ El agente puede llamar a `odoo_search_records` sin errores
3. ✅ Los resultados de Odoo se muestran correctamente
4. ✅ El domain se pasa correctamente como lista de listas

---

## 📞 Soporte Adicional

Si después de seguir todos estos pasos el error persiste:

1. Copia el mensaje de error completo de N8N
2. Revisa los logs del servidor en Replit
3. Verifica que la versión de N8N sea compatible con MCP HTTP Streamable
4. Considera usar el endpoint REST alternativo como solución temporal
