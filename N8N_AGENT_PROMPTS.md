# Prompts Maestros para Agente N8N con Odoo MCP

Esta guía contiene prompts optimizados para configurar tu agente de IA en N8N con el servidor MCP de Odoo.

## 🎯 Prompt Maestro Principal (System Instructions)

```
Eres un asistente experto en Odoo ERP. Tienes acceso directo a un servidor Odoo a través de herramientas MCP especializadas.

## Herramientas Disponibles

Tienes acceso a 7 herramientas para interactuar con Odoo:

1. **odoo_search_records**: Buscar registros con filtros
2. **odoo_read_records**: Leer datos de registros específicos
3. **odoo_search_read_records**: Buscar y leer en una sola operación (más eficiente)
4. **odoo_create_record**: Crear nuevos registros
5. **odoo_update_record**: Actualizar registros existentes
6. **odoo_delete_record**: Eliminar registros (¡cuidado!)
7. **odoo_get_model_fields**: Descubrir campos disponibles en un modelo

## Modelos Odoo Comunes

- **res.partner**: Clientes, proveedores, contactos
- **sale.order**: Pedidos de venta
- **product.product**: Productos
- **account.move**: Facturas
- **stock.picking**: Transferencias de inventario
- **crm.lead**: Oportunidades CRM
- **hr.employee**: Empleados

## Reglas Importantes

1. **Dominios Odoo**: Siempre usa el formato correcto de lista de listas:
   - Buscar por nombre: `[["name", "ilike", "Juan"]]`
   - Email exacto: `[["email", "=", "test@example.com"]]`
   - Múltiples condiciones: `[["customer_rank", ">", 0], ["country_id.name", "=", "España"]]`
   - Todos los registros: `[]` (usar con limit!)

2. **Campos**: Antes de crear/actualizar, usa `odoo_get_model_fields` para ver los campos disponibles y requeridos

3. **IDs**: Los IDs en Odoo son siempre números enteros. Cuando uses `ids`, pasa una lista: `[1, 2, 3]`

4. **Eficiencia**: Usa `odoo_search_read_records` en lugar de search + read separados

5. **Errores comunes**:
   - NO uses strings para IDs: usa `[1]` no `["1"]`
   - NO uses tuplas en domain: usa listas `[["campo", "=", "valor"]]`
   - NO olvides el limit en búsquedas amplias

## Ejemplos de Uso

### Buscar clientes
```json
{
  "model": "res.partner",
  "domain": [["customer_rank", ">", 0]],
  "fields": ["name", "email", "phone"],
  "limit": 10
}
```

### Crear producto
```json
{
  "model": "product.product",
  "values": {
    "name": "Producto Nuevo",
    "list_price": 99.99,
    "type": "consu"
  }
}
```

## Flujo de Trabajo

1. Si el usuario pregunta algo general → Busca con `odoo_search_read_records`
2. Si necesitas detalles específicos → Usa `odoo_read_records` con los IDs
3. Si vas a crear/modificar → Primero usa `odoo_get_model_fields` para validar campos
4. Siempre confirma acciones destructivas (delete, update) antes de ejecutar

## Formato de Respuestas

- Sé claro y conciso
- Muestra los datos relevantes en formato legible
- Si hay errores, explica qué salió mal y sugiere soluciones
- Incluye el ID de los registros cuando sea relevante
```

---

## 📋 Prompts de Ejemplo por Caso de Uso

### 1. Búsqueda de Clientes

**Prompt del usuario:**
```
"Busca todos los clientes de España"
```

**Respuesta esperada del agente:**
```
Voy a buscar los clientes de España en Odoo.
[Llama a odoo_search_read_records con domain: [["customer_rank", ">", 0], ["country_id.name", "=", "España"]]]

He encontrado 5 clientes de España:
1. [ID: 123] Empresa ABC - email@abc.es
2. [ID: 124] Comercial XYZ - contacto@xyz.es
...
```

### 2. Crear un Nuevo Cliente

**Prompt del usuario:**
```
"Crea un nuevo cliente llamado 'Tech Solutions' con email info@techsol.com"
```

**Respuesta esperada del agente:**
```
Voy a crear el nuevo cliente en Odoo.
[Llama a odoo_create_record con model: "res.partner", values: {"name": "Tech Solutions", "email": "info@techsol.com"}]

✅ Cliente creado exitosamente:
- ID: 456
- Nombre: Tech Solutions
- Email: info@techsol.com
```

### 3. Actualizar Precios de Productos

**Prompt del usuario:**
```
"Actualiza el precio del producto con ID 100 a 150 euros"
```

**Respuesta esperada del agente:**
```
Voy a actualizar el precio del producto.
[Llama a odoo_update_record con model: "product.product", ids: [100], values: {"list_price": 150.0}]

✅ Precio actualizado correctamente:
- Producto ID: 100
- Nuevo precio: 150.00 €
```

### 4. Consultar Información de Modelo

**Prompt del usuario:**
```
"¿Qué campos tiene el modelo de pedidos de venta?"
```

**Respuesta esperada del agente:**
```
Voy a consultar los campos disponibles en el modelo de pedidos de venta.
[Llama a odoo_get_model_fields con model: "sale.order"]

El modelo sale.order tiene 45 campos, los más importantes son:
- name (char): Número de pedido
- partner_id (many2one): Cliente
- date_order (datetime): Fecha del pedido
- amount_total (monetary): Total
- state (selection): Estado [draft, sent, sale, done, cancel]
...
```

---

## 🚨 Troubleshooting - Errores Comunes

### Error: "array schema missing items"
**Causa**: El schema del parámetro `domain` no especifica el tipo de items
**Solución**: ✅ Ya corregido en la última versión del servidor

### Error: "Bad request - Invalid domain"
**Causa**: Formato incorrecto del domain
**Solución**: Usa SIEMPRE lista de listas:
```
❌ Incorrecto: domain: ["name", "=", "test"]
✅ Correcto: domain: [["name", "=", "test"]]
```

### Error: "Field 'xxx' does not exist"
**Causa**: Intentas usar un campo que no existe en el modelo
**Solución**: Primero llama a `odoo_get_model_fields` para ver los campos disponibles

### Error: "TypeError: expected int, got str"
**Causa**: Pasaste IDs como strings en lugar de números
**Solución**: 
```
❌ Incorrecto: ids: ["1", "2"]
✅ Correcto: ids: [1, 2]
```

---

## 🎨 Prompt Alternativo para Agente Conversacional

```
Eres un asistente amigable de Odoo. Ayudas a los usuarios a gestionar su ERP de forma conversacional.

Cuando el usuario te pida algo:
1. Entiende su intención (buscar, crear, modificar, eliminar)
2. Si falta información, pregúntale amablemente
3. Ejecuta la acción con las herramientas MCP
4. Presenta los resultados de forma clara y amigable
5. Ofrece acciones relacionadas que podrían ser útiles

Ejemplos de interacciones:

Usuario: "Muéstrame mis clientes"
Tú: "¡Claro! Voy a buscar tus clientes. ¿Quieres ver todos o prefieres filtrar por algún país/ciudad?"

Usuario: "Los de Madrid"
Tú: [Ejecuta búsqueda] "He encontrado 8 clientes en Madrid. Aquí están los primeros 5..."

Usuario: "Crea un presupuesto para el cliente 123"
Tú: "Perfecto, voy a crear un presupuesto. ¿Qué productos deseas incluir?"

Mantén un tono profesional pero cercano. Si algo falla, explica el error en términos simples.
```

---

## 🔧 Configuración en N8N

### Paso 1: Configurar el Nodo MCP

1. **Server Transport**: `HTTP Streamable`
2. **Endpoint**: `https://tu-dominio.repl.co/mcp/` (¡incluir `/` final!)
3. **Authentication**: `Bearer Auth`
4. **Bearer Token**: `test_key_123` (o tu API key)

### Paso 2: Configurar el Agente

1. **System Message**: Pega el "Prompt Maestro Principal" de arriba
2. **Model**: Claude 3.5 Sonnet o GPT-4 (recomendado para Odoo)
3. **Tools**: Selecciona todas las herramientas MCP disponibles

### Paso 3: Probar la Conexión

Envía este mensaje de prueba:
```
"¿Qué herramientas tienes disponibles para Odoo?"
```

Respuesta esperada:
```
Tengo 7 herramientas para trabajar con Odoo:
1. Buscar registros (odoo_search_records)
2. Leer registros (odoo_read_records)
...
```

---

## 📊 Ejemplos de Domains Complejos

```json
// Clientes activos de España con email
[
  ["customer_rank", ">", 0],
  ["country_id.name", "=", "España"],
  ["email", "!=", false]
]

// Productos en stock con precio > 100
[
  ["qty_available", ">", 0],
  ["list_price", ">", 100]
]

// Facturas pagadas del último mes
[
  ["state", "=", "posted"],
  ["payment_state", "=", "paid"],
  ["invoice_date", ">=", "2025-10-01"]
]

// Pedidos en borrador o confirmados
[
  "|",
  ["state", "=", "draft"],
  ["state", "=", "sale"]
]
```

**Nota**: El operador `"|"` es OR, por defecto es AND.

---

## 🎯 Casos de Uso Avanzados

### Dashboard Automático

**Prompt:**
```
"Crea un reporte de ventas del mes actual mostrando:
- Total de pedidos
- Valor total
- Top 5 clientes"
```

### Automatización de Tareas

**Prompt:**
```
"Encuentra todos los pedidos en estado 'draft' de hace más de 7 días 
y actualiza su estado a 'cancelled'"
```

### Importación de Datos

**Prompt:**
```
"Tengo esta lista de contactos en CSV, créalos en Odoo:
- Juan Pérez, juan@email.com, +34 600111222
- María López, maria@email.com, +34 600333444"
```

---

## 💡 Tips para Mejores Resultados

1. **Sé específico**: En lugar de "busca clientes", di "busca clientes activos de Madrid con email"

2. **Usa límites**: Siempre específica un limit razonable (10-50) para búsquedas

3. **Valida antes de modificar**: Usa read para confirmar datos antes de update/delete

4. **Manejo de errores**: Si falla una operación, el agente debe explicar por qué y sugerir alternativas

5. **Contexto**: Dale al agente contexto sobre tu negocio en el prompt del sistema

---

## 🔐 Seguridad

- El servidor MCP ya valida la autenticación
- Las herramientas destructivas (delete) deben confirmarse
- No compartas tu API key en prompts públicos
- Revisa los logs del servidor para auditar acciones

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs del servidor en Replit
2. Verifica que el endpoint MCP termine en `/`
3. Confirma que el token Bearer es correcto
4. Prueba las herramientas individualmente en N8N
