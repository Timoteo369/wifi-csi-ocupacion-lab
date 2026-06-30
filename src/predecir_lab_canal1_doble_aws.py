import os
import csv
import ast
import serial
import joblib
import requests
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from collections import deque, Counter

# ======================================================
# CONFIGURACIÓN BASE
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

PUERTO = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUDRATE = int(os.getenv("BAUDRATE", "921600"))

MAC_TX_PERMITIDA = os.getenv("MAC_TX_PERMITIDA", "28:56:2f:4a:55:88").lower()
CANAL_ESPERADO = os.getenv("CANAL_ESPERADO", "1")

API_URL = os.getenv("API_URL", "http://TU_IP_PUBLICA/ocupacion-lab-api/estado")
API_TOKEN = os.getenv("API_TOKEN", "CAMBIA_ESTE_TOKEN")

MODELO_EXACTO_PATH = Path(os.getenv(
    "MODELO_EXACTO_PATH",
    str(BASE_DIR / "models/modelo_lab_canal1_final.pkl")
))

MODELO_RANGOS_PATH = Path(os.getenv(
    "MODELO_RANGOS_PATH",
    str(BASE_DIR / "models/modelo_lab_canal1_rangos_final.pkl")
))

if not MODELO_EXACTO_PATH.is_absolute():
    MODELO_EXACTO_PATH = BASE_DIR / MODELO_EXACTO_PATH

if not MODELO_RANGOS_PATH.is_absolute():
    MODELO_RANGOS_PATH = BASE_DIR / MODELO_RANGOS_PATH

if not MODELO_EXACTO_PATH.is_absolute():
    MODELO_EXACTO_PATH = BASE_DIR / MODELO_EXACTO_PATH

if not MODELO_RANGOS_PATH.is_absolute():
    MODELO_RANGOS_PATH = BASE_DIR / MODELO_RANGOS_PATH

WINDOW_SIZE = 120
N_SUBCARRIERS = 128
PREDICT_EVERY = 120
SMOOTHING_WINDOWS = 5

RANGOS = {
    0: "VACÍO: 0 personas",
    1: "BAJA OCUPACIÓN: 1 a 2 personas",
    2: "MEDIA OCUPACIÓN: 3 personas",
    3: "ALTA OCUPACIÓN: 4 a 5 personas",
}

PERMITIDOS_POR_RANGO = {
    0: [0],
    1: [1, 2],
    2: [3],
    3: [4, 5],
}

REPRESENTANTE_RANGO = {
    0: 0,
    1: 1,
    2: 3,
    3: 4,
}


# ======================================================
# FUNCIONES CSI
# ======================================================

def extraer_csi(row):
    for celda in row:
        celda = str(celda).strip()
        if celda.startswith("[") and celda.endswith("]"):
            try:
                valores = ast.literal_eval(celda)
                if isinstance(valores, list) and len(valores) >= 64:
                    return valores
            except Exception:
                pass
    return None


def csi_a_amplitud(csi_raw):
    arr = np.array(csi_raw, dtype=np.float32)

    if len(arr) % 2 != 0:
        arr = arr[:-1]

    iq = arr.reshape(-1, 2)
    amp = np.sqrt(iq[:, 0] ** 2 + iq[:, 1] ** 2)

    if len(amp) >= N_SUBCARRIERS:
        amp = amp[:N_SUBCARRIERS]
    else:
        amp = np.pad(amp, (0, N_SUBCARRIERS - len(amp)), mode="edge")

    return amp.astype(np.float32)


def extraer_features_window(w_amp, w_rssi):
    w = np.log1p(w_amp)

    mean_sc = w.mean(axis=0)
    std_sc = w.std(axis=0)
    min_sc = w.min(axis=0)
    max_sc = w.max(axis=0)
    p25_sc = np.percentile(w, 25, axis=0)
    p75_sc = np.percentile(w, 75, axis=0)

    global_features = np.array([
        w.mean(),
        w.std(),
        w.min(),
        w.max(),
        np.median(w),
        np.percentile(w, 25),
        np.percentile(w, 75),
        np.mean(max_sc - min_sc),
        np.mean(std_sc),
        np.max(std_sc),
    ], dtype=np.float32)

    rssi_features = np.array([
        np.nanmean(w_rssi),
        np.nanstd(w_rssi),
        np.nanmin(w_rssi),
        np.nanmax(w_rssi),
    ], dtype=np.float32)

    features = np.concatenate([
        mean_sc,
        std_sc,
        min_sc,
        max_sc,
        p25_sc,
        p75_sc,
        global_features,
        rssi_features
    ]).astype(np.float32)

    return features.reshape(1, -1)


def modo(valores):
    c = Counter(valores)
    return c.most_common(1)[0][0]


def obtener_proba(modelo, X):
    if not hasattr(modelo, "predict_proba"):
        return None, None, None

    proba = modelo.predict_proba(X)[0]
    clases = modelo.classes_
    confianza = float(np.max(proba)) * 100

    return proba, clases, confianza


def ajustar_conteo_por_rango(pred_exacto, pred_rango, proba_exacto, clases_exacto):
    permitidos = PERMITIDOS_POR_RANGO[pred_rango]

    if pred_exacto in permitidos:
        return pred_exacto, "exacto_dentro_del_rango"

    if proba_exacto is not None and clases_exacto is not None:
        mejor_clase = None
        mejor_proba = -1

        for clase in permitidos:
            indices = np.where(clases_exacto == clase)[0]
            if len(indices) == 0:
                continue

            idx = indices[0]
            p = proba_exacto[idx]

            if p > mejor_proba:
                mejor_proba = p
                mejor_clase = clase

        if mejor_clase is not None:
            return int(mejor_clase), "ajustado_por_probabilidad_dentro_del_rango"

    return REPRESENTANTE_RANGO[pred_rango], "ajustado_por_representante_del_rango"


def enviar_aws(payload):
    try:
        r = requests.post(
            API_URL,
            json=payload,
            headers={"X-API-Token": API_TOKEN},
            timeout=3
        )

        if r.status_code == 200:
            print("AWS: datos enviados correctamente.")
        else:
            print(f"AWS: error {r.status_code} -> {r.text[:250]}")

    except Exception as e:
        print(f"AWS: no se pudo enviar -> {e}")


# ======================================================
# PROGRAMA PRINCIPAL
# ======================================================

def main():
    print("======================================================")
    print(" PREDICCIÓN DOBLE MODELO + AWS")
    print(" Exacto 0-5 + Rangos R0-R3")
    print("======================================================")
    print(f"Proyecto:       {BASE_DIR}")
    print(f"Puerto serial:  {PUERTO}")
    print(f"Baudrate:       {BAUDRATE}")
    print(f"MAC TX:         {MAC_TX_PERMITIDA}")
    print(f"Canal esperado: {CANAL_ESPERADO}")
    print(f"API AWS:        {API_URL}")
    print(f"Modelo exacto:  {MODELO_EXACTO_PATH}")
    print(f"Modelo rangos:  {MODELO_RANGOS_PATH}")
    print("======================================================")

    if not MODELO_EXACTO_PATH.exists():
        raise FileNotFoundError(f"No existe el modelo exacto: {MODELO_EXACTO_PATH}")

    if not MODELO_RANGOS_PATH.exists():
        raise FileNotFoundError(f"No existe el modelo por rangos: {MODELO_RANGOS_PATH}")

    if API_URL.startswith("http://TU_IP_PUBLICA"):
        print("ADVERTENCIA: API_URL todavía tiene el valor de ejemplo.")
        print("Edita el archivo .env antes de usar AWS real.")

    if API_TOKEN == "CAMBIA_ESTE_TOKEN":
        print("ADVERTENCIA: API_TOKEN todavía tiene el valor de ejemplo.")
        print("Edita el archivo .env antes de usar AWS real.")

    print()
    print("Cargando modelos...")
    modelo_exacto = joblib.load(MODELO_EXACTO_PATH)
    modelo_rangos = joblib.load(MODELO_RANGOS_PATH)
    print("Modelos cargados correctamente.")

    print()
    print("Abriendo puerto serial...")
    ser = serial.Serial(PUERTO, BAUDRATE, timeout=1)
    ser.reset_input_buffer()
    print("Puerto serial abierto. Esperando CSI_DATA...")
    print("Presiona Ctrl+C para detener.")
    print("======================================================")

    buffer_amp = deque(maxlen=WINDOW_SIZE)
    buffer_rssi = deque(maxlen=WINDOW_SIZE)

    historial_conteo = deque(maxlen=SMOOTHING_WINDOWS)
    historial_rango = deque(maxlen=SMOOTHING_WINDOWS)

    contador_validos = 0
    contador_descartados_mac = 0
    contador_descartados_canal = 0
    contador_invalidos = 0
    contador_lineas = 0

    try:
        while True:
            raw = ser.readline()
            linea = raw.decode("utf-8", errors="ignore").strip()

            if not linea:
                continue

            contador_lineas += 1

            if not linea.startswith("CSI_DATA"):
                continue

            try:
                row = next(csv.reader([linea]))
            except Exception:
                contador_invalidos += 1
                continue

            if len(row) < 17:
                contador_invalidos += 1
                continue

            mac = row[2].strip().lower()
            canal = row[16].strip()

            if mac != MAC_TX_PERMITIDA:
                contador_descartados_mac += 1
                continue

            if canal != CANAL_ESPERADO:
                contador_descartados_canal += 1
                continue

            csi_raw = extraer_csi(row)

            if csi_raw is None:
                contador_invalidos += 1
                continue

            try:
                amp = csi_a_amplitud(csi_raw)
            except Exception:
                contador_invalidos += 1
                continue

            try:
                rssi = float(row[3])
            except Exception:
                rssi = np.nan

            buffer_amp.append(amp)
            buffer_rssi.append(rssi)
            contador_validos += 1

            if contador_validos % 500 == 0:
                print(f"CSI válidos acumulados: {contador_validos} | Buffer: {len(buffer_amp)}/{WINDOW_SIZE}")

            if len(buffer_amp) == WINDOW_SIZE and contador_validos % PREDICT_EVERY == 0:
                w_amp = np.vstack(buffer_amp).astype(np.float32)
                w_rssi = np.array(buffer_rssi, dtype=np.float32)

                X = extraer_features_window(w_amp, w_rssi)

                pred_exacto_raw = int(modelo_exacto.predict(X)[0])
                pred_rango_raw = int(modelo_rangos.predict(X)[0])

                proba_exacto, clases_exacto, confianza_exacto = obtener_proba(modelo_exacto, X)
                proba_rango, clases_rango, confianza_rango = obtener_proba(modelo_rangos, X)

                conteo_ajustado, regla_ajuste = ajustar_conteo_por_rango(
                    pred_exacto_raw,
                    pred_rango_raw,
                    proba_exacto,
                    clases_exacto
                )

                historial_conteo.append(conteo_ajustado)
                historial_rango.append(pred_rango_raw)

                conteo_suavizado = modo(historial_conteo)
                rango_suavizado = modo(historial_rango)

                payload = {
                    "sistema": "WiFi CSI Laboratorio Canal 1 - Doble Modelo",

                    "conteo_exacto_raw": int(pred_exacto_raw),
                    "conteo_ajustado": int(conteo_ajustado),
                    "conteo_final": int(conteo_suavizado),

                    "rango_id_raw": int(pred_rango_raw),
                    "rango_nombre_raw": RANGOS[pred_rango_raw],
                    "rango_id": int(rango_suavizado),
                    "rango_nombre": RANGOS[rango_suavizado],

                    "pred_actual_id": int(pred_rango_raw),
                    "pred_actual_nombre": RANGOS[pred_rango_raw],

                    "confianza_exacta": confianza_exacto,
                    "confianza_rango": confianza_rango,
                    "confianza": confianza_rango,

                    "regla_ajuste": regla_ajuste,

                    "rssi_promedio": float(np.nanmean(w_rssi)),
                    "csi_validos": int(contador_validos),
                    "descartados_mac": int(contador_descartados_mac),
                    "descartados_canal": int(contador_descartados_canal),
                    "filas_invalidas": int(contador_invalidos),

                    "window_size": WINDOW_SIZE,
                    "n_subcarriers": N_SUBCARRIERS,
                    "mac_tx": MAC_TX_PERMITIDA,
                    "canal": CANAL_ESPERADO,
                    "modelo_exacto": "ExtraTrees exacto laboratorio canal 1",
                    "modelo_rangos": "ExtraTrees rangos laboratorio canal 1"
                }

                print()
                print("======================================================")
                print(" RESULTADO EN VIVO - DOBLE MODELO")
                print("======================================================")
                print(f"Conteo exacto raw:       {pred_exacto_raw}")
                print(f"Rango raw:               R{pred_rango_raw} | {RANGOS[pred_rango_raw]}")
                print(f"Conteo ajustado:         {conteo_ajustado}")
                print(f"Conteo final suavizado:  {conteo_suavizado}")
                print(f"Rango final suavizado:   R{rango_suavizado} | {RANGOS[rango_suavizado]}")
                print(f"Regla ajuste:            {regla_ajuste}")

                if confianza_exacto is not None:
                    print(f"Confianza exacta:        {confianza_exacto:.2f}%")

                if confianza_rango is not None:
                    print(f"Confianza rango:         {confianza_rango:.2f}%")

                print(f"RSSI promedio:           {np.nanmean(w_rssi):.2f} dBm")
                print(f"CSI válidos:             {contador_validos}")
                print(f"Descartados MAC:         {contador_descartados_mac}")
                print(f"Descartados canal:       {contador_descartados_canal}")
                print(f"Filas inválidas:         {contador_invalidos}")
                print("======================================================")

                enviar_aws(payload)

    except KeyboardInterrupt:
        print()
        print("Predicción detenida por el usuario.")

    finally:
        ser.close()
        print("Puerto serial cerrado.")


if __name__ == "__main__":
    main()
