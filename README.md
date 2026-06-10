# RFESS · Clasificaciones desde LiveHeats

Aplicación en **Streamlit** para generar clasificaciones RFESS a partir de los informes CSV de **LiveHeats**.

## Qué hace

- Lee el archivo de LiveHeats **“Clasificaciones finales de la categoría (CSV)”**.
- Opcionalmente lee **“Detalle de resultados y puntajes (CSV)”**.
- Detecta categorías y sexos automáticamente.
- Permite construir clasificaciones con un **constructor visual**.
- Genera:
  - `clasificaciones_formato_rfess.csv`
  - `clasificaciones_publicacion.pdf`
  - `auditoria_puntuacion.csv`
  - `control_calidad.csv`

## Reglas RFESS aplicadas

- En pruebas **individuales**:
  - máximo **3 deportistas por club** con puntos.
  - el 4.º deportista del club puntúa **0**.
  - **no corre** la puntuación al siguiente.
- En pruebas de **equipo / relevo / club**:
  - el club puntúa normal.
- Si LiveHeats trae `Club pointscore points`, la aplicación puede usar esos puntos como base.

## Archivo obligatorio a subir

En LiveHeats, descarga este archivo:

**Informes → Clasificaciones finales de la categoría (CSV)**

Ese es el archivo principal de entrada para la app.

## Cómo abrir en local

### Opción 1 · Doble clic en Windows

- `ABRIR_APP_RFESS.bat`

### Opción 2 · Terminal

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Despliegue web privado

Esta carpeta está preparada para subirse a un repositorio de GitHub y desplegarse en **Streamlit Community Cloud**.

Archivo principal de despliegue:

```text
app.py
```

## Archivos incluidos

- `app.py` → interfaz web en castellano
- `rfess_engine_open.py` → motor de cálculo
- `rfess_pdf_open.py` → generador de PDF
- `requirements.txt` → dependencias
- `rfess_logo.jpg` → logo RFESS
- `examples/` → plantillas de apoyo

## Importante

La aplicación está pensada para que los usuarios **suban los CSV y descarguen el resultado**, sin necesidad de conservar datos de campeonatos dentro del proyecto.
