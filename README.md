# 🧹 Limpiador de PDFs de Wuolah en Local

Una herramienta interactiva local para limpiar de manera quirúrgica anuncios, banners, marcas de agua y páginas promocionales de documentos PDF descargados de Wuolah, devolviendo un archivo limpio, optimizado y con el formato de página corregido.

> [!IMPORTANT]
> ### ⚠️ AVISO IMPORTANTE: ACTIVIDAD NO LUCRATIVA y FINES ACADÉMICOS
> Este proyecto ha sido desarrollado exclusivamente con **fines educativos, de aprendizaje personal e investigación**. 
> - **Actividad No Lucrativa**: Este software es **100% gratuito y de código abierto**. No se comercializa, no contiene anuncios, no recopila datos de usuario y no genera ningún tipo de beneficio económico.
> - **Responsabilidad**: Su uso está destinado al ámbito puramente personal y de estudio. El autor no se hace responsable del uso indebido que terceros puedan dar a esta herramienta. Respeta siempre los términos y condiciones de las plataformas correspondientes.

---

## ✨ Características Principales

*   **🖥️ Interfaz Web Moderna**: Panel de control interactivo local desarrollado en Flask y HTML5/CSS, con soporte para arrastrar y soltar archivos (*Drag & Drop*).
*   **🩺 Limpieza Quirúrgica de Alta Precisión**:
    *   Elimina páginas promocionales completas (como la primera portada y páginas de publicidad interna).
    *   Remueve marcas de agua (como el logotipo de Wuolah en la esquina inferior derecha).
    *   Tacha y limpia textos publicitarios recurrentes ("Reservados todos los derechos", "No se permite la explotación económica...", etc.).
*   **📐 Corrección de Relación de Aspecto ("Que se coma la esquina")**:
    *   Cuando detecta páginas con márgenes/bordes publicitarios laterales o superiores, realiza un recorte inteligente del contenido útil y lo **re-escala al 100%** de forma que mantenga las dimensiones originales y márgenes uniformes, eliminando los bordes sin deformar el texto.
*   **🔌 Integración Nativa con Linux**:
    *   **Zenity**: Permite abrir un selector de carpetas gráfico nativo del sistema para cambiar de directorio de trabajo.
    *   Apertura directa de la carpeta de salida desde el navegador mediante herramientas del sistema (`xdg-open`).
*   **📊 Estadísticas en Tiempo Real**: Muestra el total de archivos procesados, páginas eliminadas, marcas de agua removidas, textos tachados y espacio en disco (MB) ahorrado.
*   **📟 Consola en Vivo**: Transmisión de registros de eventos en tiempo real al navegador mediante *Server-Sent Events* (SSE).

---

## 🛠️ Requisitos del Sistema

Para ejecutar este proyecto, necesitarás tener instalado lo siguiente en tu máquina local:

1.  **Python 3.8 o superior**
2.  **Zenity** (opcional, necesario en Linux para usar el selector gráfico de carpetas desde la interfaz web):
    ```bash
    sudo apt install zenity
    ```

---

## 🚀 Guía de Instalación y Uso Rápido

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Limpiador_Wuolah.git
cd Limpiador_Wuolah
```

### 2. Crear y activar un entorno virtual (Recomendado)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar las dependencias necesarias
Instala Flask y PyMuPDF (la biblioteca de procesamiento PDF ultra-rápida):
```bash
pip install Flask PyMuPDF
```

### 4. Ejecutar la aplicación
Ejecuta el servidor local:
```bash
python app.py
```

La aplicación **se abrirá automáticamente** en tu navegador predeterminado en la dirección:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📂 ¿Cómo funciona la estructura de archivos?

*   `app.py`: Servidor web Flask. Controla las rutas de la API, gestiona los hilos de procesamiento en segundo plano, actualiza las estadísticas globales e implementa la transmisión SSE para la consola de logs.
*   `cleaner.py`: El motor de procesamiento PDF. Abre los archivos utilizando `PyMuPDF` (`fitz`), aplica las máscaras de redacción física sobre anuncios, marcas de agua, y realiza la corrección de escala/recorte en páginas con bordes publicitarios.
*   `templates/` y `static/`: Contienen el frontend dinámico y la interfaz web del dashboard.

---

## 📜 Licencia

Este proyecto está bajo la Licencia **MIT**. Puedes usarlo, modificarlo y distribuirlo libremente con fines educativos y de carácter no comercial.
