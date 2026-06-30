<<'MD'
# Conteo de personas con WiFi CSI usando ESP32

Sistema para estimar ocupación de personas usando WiFi CSI con ESP32, aprendizaje automático, API en AWS y una página web en tiempo real.

## Características

- Captura de datos CSI desde ESP32.
- Procesamiento de datos CSI I/Q a amplitudes.
- Entrenamiento de modelo exacto: 0, 1, 2, 3, 4 y 5 personas.
- Entrenamiento de modelo por rangos:
  - R0: vacío, 0 personas.
  - R1: baja ocupación, 1 a 2 personas.
  - R2: media ocupación, 3 personas.
  - R3: alta ocupación, 4 a 5 personas.
- Predicción en vivo con doble modelo.
- Corrección del conteo exacto usando el rango.
- Envío de resultados a AWS.
- Página web con dos gráficos:
  - Conteo exacto ajustado.
  - Conteo por rangos.

## Estructura del proyecto

```text
wifi-csi-ocupacion-lab/
├── src/                 # Scripts Python
├── models/              # Modelos entrenados .pkl
├── web/                 # Página web
├── aws/                 # API Node.js para AWS
├── data/raw/            # CSV crudos, no incluidos
├── data/processed/      # Datos procesados, no incluidos
├── requirements.txt
├── .env.example
└── README.md


