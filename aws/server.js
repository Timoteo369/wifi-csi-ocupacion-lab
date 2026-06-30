const http = require("http");

const PORT = process.env.PORT || 3010;
const TOKEN = process.env.API_TOKEN || "CAMBIA_ESTE_TOKEN";

let estado = {
  ok: true,
  sistema: "WiFi CSI Laboratorio Canal 1",
  mensaje: "Esperando datos desde la laptop",
  actualizado: null,
  conteo_exacto_raw: null,
  conteo_ajustado: null,
  conteo_final: null,
  rango_id_raw: null,
  rango_nombre_raw: "Sin datos",
  rango_id: null,
  rango_nombre: "Sin datos",
  confianza_exacta: null,
  confianza_rango: null,
  confianza: null,
  rssi_promedio: null,
  csi_validos: 0,
  descartados_mac: 0,
  descartados_canal: 0,
  filas_invalidas: 0,
  regla_ajuste: null
};

function responder(res, status, data) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Token, Authorization"
  });
  res.end(JSON.stringify(data, null, 2));
}

function leerBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === "OPTIONS") {
    return responder(res, 200, { ok: true });
  }

  if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
    return responder(res, 200, {
      ok: true,
      servicio: "ocupacion-lab-api",
      puerto: PORT,
      estado: "activo"
    });
  }

  if (req.method === "GET" && url.pathname === "/estado") {
    return responder(res, 200, estado);
  }

  if (req.method === "POST" && url.pathname === "/estado") {
    try {
      const raw = await leerBody(req);
      const data = raw ? JSON.parse(raw) : {};

      const tokenHeader = req.headers["x-api-token"];
      const auth = req.headers["authorization"];
      const tokenAuth = auth && auth.startsWith("Bearer ") ? auth.slice(7) : null;
      const tokenBody = data.token;
      const token = tokenHeader || tokenAuth || tokenBody;

      if (token !== TOKEN) {
        return responder(res, 401, { ok: false, error: "Token inválido" });
      }

      delete data.token;

      estado = {
        ...estado,
        ...data,
        ok: true,
        mensaje: "Datos recibidos correctamente",
        actualizado: new Date().toISOString()
      };

      return responder(res, 200, { ok: true, recibido: estado });
    } catch (err) {
      return responder(res, 400, { ok: false, error: err.message });
    }
  }

  return responder(res, 404, { ok: false, error: "Ruta no encontrada" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`ocupacion-lab-api activo en http://127.0.0.1:${PORT}`);
});
