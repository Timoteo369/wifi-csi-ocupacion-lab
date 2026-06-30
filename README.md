# Conteo de personas con WiFi CSI usando ESP32

Sistema de estimación de ocupación de personas utilizando señales **WiFi CSI** capturadas con **ESP32**, modelos de **Machine Learning**, una **API en AWS** y una **página web en tiempo real** para visualizar los resultados.

El proyecto permite capturar datos CSI, procesarlos, entrenar modelos de clasificación y ejecutar una predicción en vivo usando un enfoque de **doble modelo**:

* Modelo de conteo exacto: predice 0, 1, 2, 3, 4 o 5 personas.
* Modelo por rangos: predice el nivel de ocupación R0, R1, R2 o R3.
* El resultado final ajusta el conteo exacto usando el rango estimado, reduciendo errores grandes.

---

## Tabla de contenido

* [Descripción general](#descripción-general)
* [Arquitectura del sistema](#arquitectura-del-sistema)
* [Características principales](#características-principales)
* [Estructura del repositorio](#estructura-del-repositorio)
* [Requisitos](#requisitos)
* [Configuración inicial](#configuración-inicial)
* [Variables de entorno](#variables-de-entorno)
* [Ejecución en vivo](#ejecución-en-vivo)
* [Despliegue en AWS](#despliegue-en-aws)
* [Página web](#página-web)
* [Captura de datos CSI](#captura-de-datos-csi)
* [Tratamiento de datos](#tratamiento-de-datos)
* [Entrenamiento de modelos](#entrenamiento-de-modelos)
* [Modelos incluidos](#modelos-incluidos)
* [Funcionamiento del doble modelo](#funcionamiento-del-doble-modelo)
* [API REST](#api-rest)
* [Solución de problemas](#solución-de-problemas)
* [Limitaciones del modelo](#limitaciones-del-modelo)
* [Notas importantes sobre Git LFS](#notas-importantes-sobre-git-lfs)
* [Autor](#autor)

---

## Descripción general

Este proyecto implementa un sistema experimental para estimar la cantidad de personas presentes en un ambiente usando variaciones de la señal WiFi.

Para ello se utiliza la información **CSI** (*Channel State Information*) obtenida con módulos ESP32. Los datos CSI permiten observar cómo cambia el canal inalámbrico cuando hay personas moviéndose dentro del ambiente.

El sistema fue probado en un laboratorio de cómputo con la siguiente configuración:

* 2 ESP32:

  * 1 ESP32 transmisor.
  * 1 ESP32 receptor conectado a una laptop.
* Canal WiFi: 1.
* Distancia aproximada entre TX y RX: 2.5 m.
* Altura aproximada de los ESP32: 75 cm.
* Ambiente: laboratorio de cómputo.
* Clases originales: 0, 1, 2, 3, 4 y 5 personas.
* Las personas usadas para el entrenamiento estuvieron principalmente caminando.

---

## Arquitectura del sistema

El flujo general es el siguiente:

```text
ESP32 TX  --->  ESP32 RX  --->  Laptop Ubuntu  --->  Modelo ML  --->  API AWS  --->  Página web
              CSI_DATA         Python              Predicción        Node.js       HTML/JS
```

El sistema trabaja así:

1. El ESP32 transmisor genera tráfico WiFi.
2. El ESP32 receptor captura paquetes CSI.
3. La laptop lee los datos seriales desde `/dev/ttyUSB0`.
4. Python procesa las muestras CSI.
5. Se extraen características estadísticas de la señal.
6. Se ejecutan dos modelos:

   * Modelo exacto.
   * Modelo por rangos.
7. El resultado se envía a una API alojada en AWS.
8. La página web consulta la API y muestra los resultados en tiempo real.

---

## Características principales

* Captura de datos CSI desde ESP32.
* Filtrado por MAC del transmisor.
* Filtrado por canal WiFi.
* Conversión de datos I/Q a amplitudes.
* Uso de 128 subportadoras.
* Ventanas de 120 paquetes CSI.
* Extracción de características estadísticas.
* Entrenamiento de modelo exacto para 0 a 5 personas.
* Entrenamiento de modelo por rangos.
* Predicción en vivo usando doble modelo.
* Corrección del conteo exacto mediante el rango estimado.
* Envío de resultados a AWS.
* API REST en Node.js.
* Página web con gráficos de puntos:

  * Conteo exacto ajustado.
  * Rango de ocupación.
* Uso de Git LFS para almacenar modelos grandes.

---

## Estructura del repositorio

```text
wifi-csi-ocupacion-lab/
├── aws/
│   └── server.js
│
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── processed/
│       └── .gitkeep
│
├── models/
│   ├── modelo_lab_canal1_final.pkl
│   └── modelo_lab_canal1_rangos_final.pkl
│
├── src/
│   ├── capturar_lab_csi.py
│   ├── tratar_datos_lab_canal1.py
│   ├── entrenar_lab_canal1.py
│   ├── entrenar_lab_canal1_rangos.py
│   ├── predecir_lab_canal1_rangos_aws.py
│   └── predecir_lab_canal1_doble_aws.py
│
├── web/
│   └── wifi-csi-lab.html
│
├── .env.example
├── .gitignore
├── .gitattributes
├── requirements.txt
└── README.md
```

---

## Requisitos

### Hardware

* 2 placas ESP32.
* Cable USB para conectar el ESP32 receptor a la laptop.
* Fuente de alimentación para el ESP32 transmisor.
* Laptop con Ubuntu.
* Servidor AWS EC2, opcional si se desea publicar la visualización web.

### Software en laptop

* Ubuntu 22.04, 24.04 o similar.
* Python 3.
* Git.
* Git LFS.
* Entorno virtual de Python.
* Firmware ESP-CSI cargado en los ESP32.

### Software en AWS

* Ubuntu Server.
* Node.js.
* Apache2.
* Módulos Apache:

  * proxy
  * proxy_http
  * headers

---

## Configuración inicial

Clonar el repositorio:

```bash
git clone https://github.com/Timoteo369/wifi-csi-ocupacion-lab.git
cd wifi-csi-ocupacion-lab
```

Descargar los modelos con Git LFS:

```bash
git lfs pull
```

Crear entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear archivo de configuración:

```bash
cp .env.example .env
nano .env
```

---

## Variables de entorno

El archivo `.env` contiene la configuración principal del sistema.

Ejemplo:

```text
API_URL=http://TU_IP_PUBLICA/ocupacion-lab-api/estado
API_TOKEN=TU_TOKEN

SERIAL_PORT=/dev/ttyUSB0
BAUDRATE=921600

MAC_TX_PERMITIDA=28:56:2f:4a:55:88
CANAL_ESPERADO=1

MODELO_EXACTO_PATH=models/modelo_lab_canal1_final.pkl
MODELO_RANGOS_PATH=models/modelo_lab_canal1_rangos_final.pkl
```

Descripción:

| Variable             | Descripción                                           |
| -------------------- | ----------------------------------------------------- |
| `API_URL`            | URL de la API donde se enviarán las predicciones.     |
| `API_TOKEN`          | Token privado para autenticar el envío de datos.      |
| `SERIAL_PORT`        | Puerto serial donde está conectado el ESP32 receptor. |
| `BAUDRATE`           | Velocidad de comunicación serial.                     |
| `MAC_TX_PERMITIDA`   | MAC del ESP32 transmisor permitido.                   |
| `CANAL_ESPERADO`     | Canal WiFi usado en la captura.                       |
| `MODELO_EXACTO_PATH` | Ruta del modelo exacto.                               |
| `MODELO_RANGOS_PATH` | Ruta del modelo por rangos.                           |

No subas el archivo `.env` real a GitHub. Este archivo está ignorado por `.gitignore`.

---

## Ejecución en vivo

Conectar el ESP32 receptor a la laptop y encender el ESP32 transmisor.

Activar el entorno virtual:

```bash
cd wifi-csi-ocupacion-lab
source venv/bin/activate
```

Ejecutar el sistema de doble modelo:

```bash
python3 src/predecir_lab_canal1_doble_aws.py
```

Si todo está correcto, se verá algo similar:

```text
======================================================
 PREDICCIÓN DOBLE MODELO + AWS
 Exacto 0-5 + Rangos R0-R3
======================================================
Cargando modelos...
Modelos cargados correctamente.

Abriendo puerto serial...
Puerto serial abierto. Esperando CSI_DATA...
```

Cuando reciba suficientes paquetes CSI, mostrará resultados como:

```text
RESULTADO EN VIVO - DOBLE MODELO
Conteo exacto raw:       4
Rango raw:               R3 | ALTA OCUPACIÓN: 4 a 5 personas
Conteo ajustado:         4
Conteo final suavizado:  4
Rango final suavizado:   R3 | ALTA OCUPACIÓN: 4 a 5 personas
AWS: datos enviados correctamente.
```

---

## Despliegue en AWS

### 1. Copiar la API

En AWS:

```bash
sudo mkdir -p /opt/ocupacion-lab-api
sudo cp aws/server.js /opt/ocupacion-lab-api/server.js
```

Si estás subiendo desde tu laptop, puedes usar `scp` o copiar el contenido manualmente.

---

### 2. Crear servicio systemd

Crear archivo:

```bash
sudo nano /etc/systemd/system/ocupacion-lab-api.service
```

Contenido:

```ini
[Unit]
Description=API WiFi CSI Laboratorio Canal 1
After=network.target

[Service]
WorkingDirectory=/opt/ocupacion-lab-api
ExecStart=/usr/bin/node /opt/ocupacion-lab-api/server.js
Restart=always
RestartSec=3
User=ubuntu
Environment=PORT=3010
Environment=API_TOKEN=CAMBIA_ESTE_TOKEN

[Install]
WantedBy=multi-user.target
```

Activar el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ocupacion-lab-api
sudo systemctl restart ocupacion-lab-api
sudo systemctl status ocupacion-lab-api --no-pager -l
```

Probar localmente en AWS:

```bash
curl http://127.0.0.1:3010/health
```

Debe responder:

```json
{
  "ok": true,
  "servicio": "ocupacion-lab-api",
  "puerto": "3010",
  "estado": "activo"
}
```

---

### 3. Configurar Apache como proxy

Activar módulos:

```bash
sudo a2enmod proxy proxy_http headers
```

Crear configuración:

```bash
sudo tee /etc/apache2/conf-available/ocupacion-lab-api.conf > /dev/null <<'CONF'
ProxyPass /ocupacion-lab-api/ http://127.0.0.1:3010/
ProxyPassReverse /ocupacion-lab-api/ http://127.0.0.1:3010/
CONF
```

Activar configuración:

```bash
sudo a2enconf ocupacion-lab-api
sudo apachectl configtest
sudo systemctl restart apache2
```

Probar públicamente:

```bash
curl http://TU_IP_PUBLICA/ocupacion-lab-api/health
```

---

## Página web

Copiar la página al servidor Apache:

```bash
sudo cp web/wifi-csi-lab.html /var/www/html/wifi-csi-lab.html
```

Abrir en el navegador:

```text
http://TU_IP_PUBLICA/wifi-csi-lab.html
```

La página muestra:

* Conteo final ajustado.
* Rango de ocupación.
* Confianza del modelo exacto.
* Confianza del modelo por rangos.
* RSSI promedio.
* CSI válidos.
* Gráfico de puntos para conteo exacto.
* Gráfico de puntos para rangos.
* Detalles técnicos de la predicción.

---

## Captura de datos CSI

Para capturar datos nuevos, usar:

```bash
python3 src/capturar_lab_csi.py \
  --personas 0 \
  --sesion 1 \
  --duracion 180 \
  --distancia 2.5 \
  --altura 75 \
  --nota "laboratorio vacio sesion 1"
```

Ejemplo para 3 personas:

```bash
python3 src/capturar_lab_csi.py \
  --personas 3 \
  --sesion 1 \
  --duracion 180 \
  --distancia 2.5 \
  --altura 75 \
  --nota "tres personas caminando"
```

Los CSV se deben guardar en:

```text
data/raw/
```

---

## Tratamiento de datos

Procesar los CSV:

```bash
python3 src/tratar_datos_lab_canal1.py
```

Este script:

* Lee los CSV crudos.
* Filtra por MAC.
* Filtra por canal.
* Convierte CSI I/Q a amplitudes.
* Usa 128 subportadoras.
* Genera ventanas de 120 paquetes.
* Extrae características estadísticas.
* Guarda el dataset procesado.

Salida esperada:

```text
data/processed/dataset_lab_canal1_128sc.npz
```

---

## Entrenamiento de modelos

### Modelo exacto

```bash
python3 src/entrenar_lab_canal1.py
```

Este modelo clasifica:

```text
0, 1, 2, 3, 4, 5 personas
```

---

### Modelo por rangos

```bash
python3 src/entrenar_lab_canal1_rangos.py
```

Este modelo clasifica:

```text
R0: 0 personas
R1: 1 a 2 personas
R2: 3 personas
R3: 4 a 5 personas
```

---

## Modelos incluidos

El repositorio incluye dos modelos entrenados:

```text
models/modelo_lab_canal1_final.pkl
models/modelo_lab_canal1_rangos_final.pkl
```

Estos archivos están almacenados con Git LFS porque son archivos grandes.

El modelo exacto predice la cantidad de personas de 0 a 5.

El modelo por rangos predice el nivel de ocupación.

---

## Funcionamiento del doble modelo

El sistema usa dos modelos en paralelo:

```text
Modelo exacto       → predice 0, 1, 2, 3, 4 o 5
Modelo por rangos   → predice R0, R1, R2 o R3
```

Luego se aplica una regla de ajuste:

```text
R0 → permite solo 0
R1 → permite 1 o 2
R2 → permite solo 3
R3 → permite 4 o 5
```

Ejemplo:

```text
Modelo exacto: 2 personas
Modelo rango: R3, alta ocupación
Resultado ajustado: 4 o 5 personas
```

Esto ayuda a reducir errores grandes cuando el modelo exacto se equivoca.

---

## API REST

La API tiene las siguientes rutas:

### Health check

```http
GET /health
```

Respuesta:

```json
{
  "ok": true,
  "servicio": "ocupacion-lab-api",
  "puerto": "3010",
  "estado": "activo"
}
```

---

### Consultar estado

```http
GET /estado
```

Devuelve la última predicción recibida.

---

### Enviar estado

```http
POST /estado
```

Requiere token:

```http
X-API-Token: TU_TOKEN
```

Ejemplo:

```bash
curl -X POST http://127.0.0.1:3010/estado \
  -H "Content-Type: application/json" \
  -H "X-API-Token: TU_TOKEN" \
  -d '{
    "conteo_exacto_raw": 2,
    "conteo_ajustado": 3,
    "conteo_final": 3,
    "rango_id": 2,
    "rango_nombre": "MEDIA OCUPACIÓN: 3 personas",
    "confianza_exacta": 41.8,
    "confianza_rango": 76.4,
    "rssi_promedio": -52.2,
    "csi_validos": 1200
  }'
```

---

## Solución de problemas

### El puerto serial está ocupado

```bash
sudo fuser -v /dev/ttyUSB0
sudo fuser -k /dev/ttyUSB0
```

---

### No aparece `CSI_DATA`

Revisar:

* El ESP32 RX está conectado a la laptop.
* El ESP32 TX está encendido.
* Ambos ESP32 están en el mismo canal.
* La MAC del TX coincide con `MAC_TX_PERMITIDA`.
* No está abierto `idf.py monitor`.
* No hay otro script usando `/dev/ttyUSB0`.

---

### Error `FileNotFoundError` con modelos

Verificar:

```bash
ls -lh models/
git lfs pull
```

---

### Error `EOFError` al cargar modelo

Significa que el modelo está vacío o corrupto. Descargar nuevamente con:

```bash
git lfs pull
```

O copiar nuevamente los modelos entrenados.

---

### Error 503 en Apache

Significa que Apache no puede conectarse a la API Node.js.

Revisar:

```bash
sudo systemctl status ocupacion-lab-api --no-pager -l
curl http://127.0.0.1:3010/health
sudo systemctl restart ocupacion-lab-api
sudo systemctl restart apache2
```

---

### La página no actualiza

Revisar:

```bash
curl http://TU_IP_PUBLICA/ocupacion-lab-api/estado
```

También presionar `Ctrl + F5` en el navegador para evitar caché.

---

## Limitaciones del modelo

Este modelo fue entrenado principalmente con personas caminando en un laboratorio de cómputo.

Puede fallar si:

* Las personas están sentadas.
* Las personas están completamente quietas.
* El ambiente cambia demasiado.
* Se cambia la distancia TX-RX.
* Se cambia la altura de los ESP32.
* Se cambia el canal WiFi.
* Hay demasiadas interferencias externas.
* Se usa en una habitación diferente sin reentrenar.

Para mejorar el modelo se recomienda capturar más datos con:

* Personas sentadas.
* Personas quietas.
* Personas caminando.
* Movimiento mixto.
* Diferentes posiciones dentro del ambiente.
* Más sesiones por cada número de personas.

---

## Notas importantes sobre Git LFS

Los modelos `.pkl` son archivos grandes. Por eso se almacenan con Git LFS.

Después de clonar el repositorio, ejecutar:

```bash
git lfs pull
```

Verificar modelos:

```bash
ls -lh models/
```

Si los modelos pesan pocos KB, entonces no se descargaron correctamente.

---

## Autor

Proyecto desarrollado por:

```text
Timoteo Quispe Merma
GitHub: Timoteo369
```

Repositorio:

```text
https://github.com/Timoteo369/wifi-csi-ocupacion-lab
```

---

## Estado del proyecto

Versión funcional experimental:

* Captura CSI: implementada.
* Procesamiento: implementado.
* Entrenamiento: implementado.
* Predicción en vivo: implementada.
* API AWS: implementada.
* Página web: implementada.
* Git LFS para modelos: configurado.

Este proyecto puede servir como base para investigaciones sobre ocupación de ambientes usando WiFi CSI y aprendizaje automático.

