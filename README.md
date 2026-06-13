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

- Regla simplificada por prueba:
  - máximo **3 resultados por club** con puntos en cada prueba.
  - se aplica igual a individuales y a equipos/relevos.
  - el 4.º resultado del mismo club puntúa **0**.
  - **no corre** la puntuación al siguiente.
- Si LiveHeats trae `Club pointscore points`, la aplicación puede usar esos puntos como base antes de aplicar el máximo por club.
- En relevos/equipos la app puede agrupar filas duplicadas de deportistas del mismo equipo para no contar una alineación como varios resultados, pero la regla de puntuación es la misma.

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

## Versión v7 · detección automática de pruebas finalizadas

La app incorpora una detección automática para clasificaciones parciales:

- Si el archivo principal es **Clasificaciones finales de la categoría (CSV)**, se consideran puntuables las pruebas incluidas en ese archivo.
- Si además se sube **Detalle de resultados y puntajes (CSV)**, la app cruza las pruebas y excluye finales provisionales sin evidencia de resultado/marca/score.
- Si el archivo principal parece ser **Detalle de resultados** porque trae columna `Round/Ronda`, la app muestra un aviso. Para clasificaciones parciales, lo más seguro es usar siempre como principal el CSV de clasificaciones finales.

El selector manual sigue disponible como plan B cuando LiveHeats tenga finales provisionales ya creadas o datos incompletos.


## Versión v7

- Corrige la detección de pruebas individuales cuando el CSV no trae `Division_team`.
- Por defecto usa `place` para respetar posiciones oficiales y empates cuando no hay pointscore.
- Si se detecta categoría absoluta, el bloque inicial se crea como `General absoluto` para evitar sumar máster/juvenil sin querer.

## Versión v8 · regla simplificada por club

- El máximo de 3 se aplica a todos los tipos de prueba: individuales, relevos y equipos.
- Se elimina la diferencia práctica de puntuación entre individual y relevo/equipo.
- El informe de auditoría marca el ajuste como `CUARTO_RESULTADO_CLUB_PRUEBA`.
- La interfaz cambia el campo a: “Máximo de resultados por club en cada prueba”.
