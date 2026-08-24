# 🎬 ClipScope — Diagnóstico de Clipping para Prospección

Aplicación web construida con **Streamlit** que analiza el desempeño cross-platform
de un prospecto (YouTube, TikTok, Instagram Reels y Facebook Video), detecta
oportunidades de venta mediante alertas automáticas y genera un **pitch de
ventas personalizado**, listo para exportar a Excel o PDF.

---

## 📁 Estructura del proyecto

```
clipscope/
├── app.py                          # App principal de Streamlit
├── requirements.txt                # Dependencias del servidor
├── .gitignore                      # Protege credenciales al subir a GitHub
├── README.md                       # Este archivo
├── .streamlit/
│   └── secrets.toml.example        # Plantilla de credenciales (no subir el real)
└── modules/
    ├── __init__.py
    ├── youtube_service.py          # Extracción vía YouTube Data API v3
    ├── apify_service.py            # Extracción vía Apify (TikTok/IG/FB)
    ├── analysis.py                 # Tabla comparativa, alertas y pitch
    ├── export_service.py           # Exportación a Excel y PDF
    └── ui_helpers.py                # Estilos y componentes visuales
```

---

## 🔑 1. Obtener las API Keys

### YouTube Data API v3
1. Entra a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea (o selecciona) un proyecto.
3. Ve a **APIs y servicios → Biblioteca** y activa **"YouTube Data API v3"**.
4. Ve a **APIs y servicios → Credenciales → Crear credenciales → Clave de API**.
5. Copia la clave generada.

> La cuota gratuita diaria (10,000 unidades) es suficiente para varias decenas de análisis por día.

### Apify Token
1. Crea una cuenta en [apify.com](https://apify.com) (tiene plan gratuito).
2. Ve a **Settings → Integrations** en tu consola de Apify.
3. Copia tu **Personal API Token**.
4. Revisa que los actores usados por la app (definidos en `modules/apify_service.py`)
   sigan activos en tu cuenta; los actores de terceros en Apify Store cambian con
   el tiempo, así que conviene verificarlos antes de la primera ejecución en producción.

---

## 💻 2. Probar localmente (opcional)

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar las claves localmente
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edita .streamlit/secrets.toml y pega tus claves reales

# 4. Ejecutar la app
streamlit run app.py
```

La app se abrirá en `http://localhost:8501`.

---

## ☁️ 3. Desplegar gratis en Streamlit Community Cloud

1. **Sube el proyecto a GitHub**
   - Crea un repositorio nuevo (puede ser privado o público).
   - Sube todos los archivos de este proyecto **excepto** `.streamlit/secrets.toml`
     (ya está protegido por `.gitignore`, así que solo se subirá `secrets.toml.example`).

   ```bash
   git init
   git add .
   git commit -m "ClipScope: primera versión"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```

2. **Conecta el repositorio a Streamlit Cloud**
   - Entra a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
   - Haz clic en **"New app"**.
   - Selecciona tu repositorio y la rama `main`.
   - En **"Main file path"** escribe: `app.py`.

3. **Configura las claves como Secrets**
   - En la pantalla de configuración de la app, abre **"Advanced settings" → "Secrets"**.
   - Pega el siguiente contenido (con tus claves reales):

     ```toml
     YOUTUBE_API_KEY = "AIza..."
     APIFY_TOKEN = "apify_api_..."
     ```

4. Haz clic en **"Deploy"**. En un par de minutos tendrás una URL pública
   (`https://tu-app.streamlit.app`) accesible desde cualquier navegador, sin instalar nada.

> Si más adelante cambias o rotas tus claves, puedes actualizarlas en cualquier
> momento desde **App → Settings → Secrets** sin tocar el código ni el repositorio.

---

## 🧩 Notas de arquitectura

- **Sidebar de API Keys:** si la app corre en Streamlit Cloud con `secrets.toml`
  configurado, los campos de la barra lateral se autocompletan; si no, el usuario
  puede pegar sus propias claves manualmente (útil para pruebas puntuales de otros usuarios).
- **Caché:** las consultas a YouTube y Apify se cachean 30 minutos (`st.cache_data`)
  para evitar reconsumir cuota/créditos al recargar la página.
- **Actores de Apify:** los IDs de actor están centralizados como constantes al
  inicio de `modules/apify_service.py` para poder reemplazarlos fácilmente si
  Apify Store actualiza o retira alguno.
- **Clasificación Shorts vs. largos en YouTube:** se basa en la duración exacta
  del video (`<= 60s` = Short), obtenida vía `videos.list` (parte `contentDetails`).

---

## ⚠️ Buenas prácticas de seguridad

- Nunca subas tu `.streamlit/secrets.toml` real a GitHub (ya está en `.gitignore`).
- Si compartes el repositorio públicamente, usa siempre el flujo de **Secrets**
  de Streamlit Cloud en lugar de escribir las claves directamente en el código.
- Considera restringir tu YouTube API Key por referer/IP desde Google Cloud Console
  una vez que la app esté en producción.
