# Guía de Despliegue en Easypanel

## 📦 Desplegar MCP Odoo Server en Easypanel

Esta guía te ayudará a desplegar el servidor MCP en tu servidor usando Easypanel.

---

## 🚀 Paso 1: Crear el Servicio en Easypanel

1. **Login en Easypanel** → Ve a tu dashboard
2. **Crear nuevo servicio** → Click en "Create Service"
3. **Seleccionar tipo**: `App` (no Docker Compose)
4. **Nombre del servicio**: `odoo-mcp-server`

---

## 🐳 Paso 2: Configurar el Deployment

### Opción A: Deploy desde GitHub/Git

Si tienes el código en un repositorio Git:

1. **Source**: Git Repository
2. **Repository URL**: Tu URL del repositorio
3. **Branch**: `main` o tu rama principal
4. **Build Method**: `Dockerfile`

### Opción B: Deploy con Dockerfile directo

Usa este Dockerfile (ya está en el proyecto):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Puerto
EXPOSE 5000

# Comando de inicio
CMD ["python", "-m", "mcp_server_odoo"]
```

---

## ⚙️ Paso 3: Variables de Entorno

En Easypanel, configura estas variables de entorno:

### Variables Obligatorias

```bash
# Modo servidor
SERVER_MODE=http

# Odoo Credentials
ODOO_URL=https://tu-instancia-odoo.com
ODOO_DB=nombre_base_datos
ODOO_USERNAME=tu_usuario
ODOO_PASSWORD=tu_contraseña

# API Keys (para autenticación)
API_KEYS=test_key_123,production_key_456

# Secret key para JWT
SECRET_KEY=tu-secret-key-super-seguro-aqui

# URL pública del servidor (importante para OAuth)
SERVER_URL=https://tu-dominio.easypanel.host
```

### Variables Opcionales

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
ODOO_TIMEOUT=30
ODOO_MAX_RETRIES=3

# Cache (si tienes Redis)
REDIS_ENABLED=false
# REDIS_URL=redis://tu-redis:6379/0

# Rate limiting
RATE_LIMIT=60
```

---

## 🌐 Paso 4: Configurar Puerto y Dominio

1. **Puerto interno**: `5000` (el servidor escucha en este puerto)
2. **Puerto externo**: Deja que Easypanel asigne automáticamente
3. **Dominio personalizado**: 
   - Easypanel te dará un dominio tipo: `odoo-mcp.tu-servidor.easypanel.host`
   - O configura tu dominio personalizado: `mcp.tudominio.com`

### Health Check (opcional pero recomendado)

- **Path**: `/health`
- **Port**: `5000`
- **Interval**: `30s`

---

## 📊 Paso 5: Recursos Recomendados

```yaml
CPU: 0.5 cores (mínimo)
RAM: 512 MB (mínimo) - 1 GB (recomendado)
Disk: 1 GB
```

---

## ✅ Paso 6: Verificar el Despliegue

Una vez desplegado, verifica que funcione:

### 1. Health Check
```bash
curl https://tu-dominio.easypanel.host/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "service": "MCP Odoo Server",
  "version": "2.0.0"
}
```

### 2. Info del servidor
```bash
curl https://tu-dominio.easypanel.host/
```

### 3. Test de autenticación
```bash
curl -X POST https://tu-dominio.easypanel.host/mcp/ \
  -H "Authorization: Bearer test_key_123" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## 🔧 Configuración de Claude Desktop

Una vez desplegado en Easypanel, configura Claude Desktop así:

### Ubicación del archivo

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Configuración

```json
{
  "mcpServers": {
    "odoo-mcp": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://tu-dominio.easypanel.host/mcp/",
        "--header",
        "Authorization: Bearer test_key_123"
      ]
    }
  }
}
```

**⚠️ Importante**: 
- Reemplaza `tu-dominio.easypanel.host` con tu dominio real
- Reemplaza `test_key_123` con una de las API keys que configuraste
- Asegúrate de incluir `/mcp/` al final de la URL

---

## 🔒 Seguridad: Recomendaciones

1. **Genera API Keys seguras**:
   ```bash
   # Ejemplo de generar una clave aleatoria
   openssl rand -hex 32
   ```

2. **Usa HTTPS siempre** (Easypanel lo habilita automáticamente)

3. **Rota las claves periódicamente**:
   - Actualiza `API_KEYS` en variables de entorno
   - Reinicia el servicio

4. **Monitorea los logs**:
   - Easypanel te permite ver logs en tiempo real
   - Busca intentos de autenticación fallidos

---

## 🐛 Troubleshooting

### El servidor no inicia

```bash
# Ver logs en Easypanel
# Dashboard → Tu servicio → Logs

# Busca errores como:
- "ODOO_URL not configured" → Falta configurar variables
- "Connection refused" → Problema de conexión con Odoo
```

### Claude Desktop no conecta

1. **Verifica la URL**: Debe terminar en `/mcp/`
2. **Verifica autenticación**: API key correcta en el header
3. **Verifica HTTPS**: No uses HTTP, solo HTTPS
4. **Instala mcp-remote**: `npm install -g mcp-remote`

### Error 401 Unauthorized

- Verifica que el API key en Claude Desktop coincida con uno de `API_KEYS`
- Revisa que el header esté bien escrito: `Authorization: Bearer TU_KEY`

### Error 404 Not Found

- Asegúrate de usar `/mcp/` (con slash al final)
- Verifica que el servidor esté corriendo

---

## 📈 Monitoreo Continuo

En Easypanel puedes configurar:

1. **Alertas**: Si el servicio cae
2. **Métricas**: CPU, RAM, requests
3. **Logs**: Análisis en tiempo real
4. **Auto-restart**: Si el servicio falla

---

## 🔄 Actualizar el Servidor

Cuando hagas cambios al código:

### Si usas Git:
1. Push los cambios a tu repositorio
2. En Easypanel: Click en "Rebuild"
3. Espera el nuevo despliegue

### Si usas Dockerfile manual:
1. Actualiza el código en Easypanel
2. Rebuild el servicio

---

## ✅ Checklist Final

- [ ] Servicio creado en Easypanel
- [ ] Variables de entorno configuradas
- [ ] Dominio asignado (ej: `mcp.tudominio.com`)
- [ ] Health check funcionando (`/health` retorna 200)
- [ ] API keys generadas y seguras
- [ ] Claude Desktop configurado
- [ ] Test de conexión exitoso

---

## 🎯 Próximos Pasos

Una vez todo funcionando:

1. **Integra con ChatGPT**: Usa el OAuth flow (ver `CHATGPT_OAUTH_SETUP.md`)
2. **Integra con N8N**: Usa el endpoint MCP HTTP (ver `N8N_SETUP.md`)
3. **Monitorea uso**: Revisa logs regularmente
4. **Escala si es necesario**: Aumenta recursos en Easypanel

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs en Easypanel
2. Verifica las variables de entorno
3. Prueba los endpoints manualmente con `curl`
4. Consulta la documentación en `/docs` del servidor

¡Listo para producción! 🚀
