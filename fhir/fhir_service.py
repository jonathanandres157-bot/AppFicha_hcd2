"""
Capa de servicio: conecta Flask con el servidor FHIR.
Recibe los datos del formulario web y crea los recursos correspondientes.
"""

import requests as _requests_lib
import sys
import os
import copy
import uuid as _uuid
from datetime import datetime as _dt
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

_TZ_CHILE = ZoneInfo("America/Santiago")

sys.path.insert(0, os.path.dirname(__file__))
from fhir_mappings import (
    construir_paciente_fhir,
    construir_clinical_status,
    construir_verification_status,
    construir_via_administracion,
    construir_observation,
    construir_marital_status,
    construir_extension_pueblo_indigena,
    construir_extension_afrodescendiente,
    construir_extension_nivel_educacional,
    construir_extension_ultimo_curso,
    construir_extension_prevision,
    construir_extension_sexo,
    construir_extension_genero,
    construir_extension_nacionalidad,
    construir_identifier_rut,
    SEXO_A_GENDER_FHIR,
    ESTADO_MEDICAMENTO,
    ESTADO_TRATAMIENTO,
    CRITICIDAD_ALERGIA,
    TIPO_ALERGIA,
    TIPO_TRATAMIENTO,
    DIAGNOSTICOS, SUSTANCIAS_ALERGIAS,
    MANIFESTACIONES_ALERGICAS,
    MEDICAMENTOS_CLINICOS,
    TRATAMIENTOS_CLINICOS,
)
# ──────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────

BASE_URL = "https://fhirserver.hl7chile.cl/fhir/"

# Session persistente — reutiliza conexiones TCP (keep-alive + connection pooling)
_http = _requests_lib.Session()
_http.headers.update({
    "Accept":       "application/fhir+json",
    "Content-Type": "application/fhir+json",
})


# ──────────────────────────────────────────────────────────────
# UTILIDADES INTERNAS
# ──────────────────────────────────────────────────────────────

def _post(recurso, datos):
    try:
        r = _http.post(f"{BASE_URL}/{recurso}", json=datos, timeout=15)
        r.raise_for_status()
        return r.json()
    except _requests_lib.exceptions.HTTPError:
        print(f"[FHIR] ERROR HTTP {r.status_code} en {recurso}: {r.text}")
        return None
    except Exception as e:
        print(f"[FHIR] ERROR en {recurso}: {e}")
        return None


def _get(url, params=None):
    try:
        r = _http.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[FHIR] ERROR GET {url}: {e}")
        return None


def _put(url, datos):
    try:
        r = _http.put(url, json=datos, timeout=15)
        r.raise_for_status()
        return r.json()
    except _requests_lib.exceptions.HTTPError:
        print(f"[FHIR] ERROR HTTP {r.status_code} PUT {url}: {r.text}")
        return None
    except Exception as e:
        print(f"[FHIR] ERROR PUT {url}: {e}")
        return None


def _delete(url):
    try:
        r = _http.delete(url, timeout=15)
        return r.status_code in [200, 204]
    except Exception as e:
        print(f"[FHIR] ERROR DELETE {url}: {e}")
        return False


def _post_transaction(bundle):
    try:
        r = _http.post(BASE_URL, json=bundle, timeout=30)
        r.raise_for_status()
        return r.json()
    except _requests_lib.exceptions.HTTPError:
        print(f"[FHIR] ERROR HTTP {r.status_code} en transaction: {r.text}")
        return None
    except Exception as e:
        print(f"[FHIR] ERROR en transaction: {e}")
        return None

def _val_list(form, campo, indice):
    """Obtiene el valor de un campo de lista de forma segura."""
    lista = form.getlist(campo)
    return lista[indice].strip() if indice < len(lista) else ""


def _normalizar_datetime(fecha):
    """Agrega segundos y offset de Chile al datetime-local del formulario."""
    if not fecha or "T" not in fecha:
        return fecha
    fecha_parte, hora_parte = fecha.split("T", 1)
    for sep in ["+", "-"]:
        if sep in hora_parte:          
            idx = hora_parte.rfind(sep)
            tz  = hora_parte[idx:]
            hora_parte = hora_parte[:idx]
            if hora_parte.count(":") == 1:
                hora_parte += ":00"
            return f"{fecha_parte}T{hora_parte}{tz}"
    if hora_parte.endswith("Z"):
        hora_parte = (hora_parte[:-1] + (":00" if hora_parte[:-1].count(":") == 1 else "")) + "Z"
        return f"{fecha_parte}T{hora_parte}"
    if hora_parte.count(":") == 1:
        hora_parte += ":00"
    # Offset dinámico de Chile (maneja horario de verano e invierno)
    tz_raw = _dt.now(_TZ_CHILE).strftime("%z")          
    tz_str = f"{tz_raw[:3]}:{tz_raw[3:]}"               
    return f"{fecha_parte}T{hora_parte}{tz_str}"


def _coding_display(obj, *path):
    """Extrae el display de un CodeableConcept."""
    for k in path:
        obj = obj.get(k, {}) if isinstance(obj, dict) else {}
    if not obj:
        return None
    texto = obj.get("text")
    if texto:
        return texto
    codings = obj.get("coding", [])
    if codings:
        return codings[0].get("display") or codings[0].get("code")
    return None

def _entradas(bundle):
    if not bundle:
        return []
    return [e["resource"] for e in bundle.get("entry", [])]

def _cod(obj):
    """Extrae el primer code raw de un CodeableConcept (para traducir)."""
    for c in obj.get("coding", []):
        if c.get("code"):
            return c["code"]
    return ""

#horario
def _ahora_chile():
    """Timestamp actual en hora de Chile con offset correcto (maneja DST automáticamente)."""
    return _dt.now(_TZ_CHILE).isoformat(timespec='seconds')

def _fecha_corta(fecha_iso):
    """Convierte un timestamp ISO 8601 (cualquier zona) a hora de Chile legible."""
    try:
        dt = _dt.fromisoformat(fecha_iso.replace("Z", "+00:00"))
        return dt.astimezone(_TZ_CHILE).strftime("%d/%m %H:%M")
    except Exception:
        return fecha_iso[:10] if fecha_iso else "—"

def _parse_iso(s):
    """Convierte ISO 8601 con cualquier timezone a datetime aware para comparar correctamente."""
    if not s:
        return None
    try:
        return _dt.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

# ── Traducciones FHIR → Español (nivel módulo) ──────────────────────
_CERT_ES  = {"confirmed":"Confirmado","provisional":"Presuntivo",
             "differential":"Diferencial","unconfirmed":"Sin confirmar","refuted":"Descartado"}
_EST_C_ES = {"active":"Activa","resolved":"Resuelta","remission":"En remisión",
             "recurrence":"Recurrente","inactive":"Inactiva"}
_CRIT_ES  = {"high":"Alta","low":"Baja","unable-to-assess":"Sin determinar"}
_TIPO_ES  = {"allergy":"Alergia","intolerance":"Intolerancia"}
_EST_A_ES = {"active":"Activa","inactive":"Inactiva","resolved":"Resuelta"}
_EST_M_ES = {"active":"Activo","on-hold":"Suspendido","cancelled":"Cancelado","completed":"Finalizado"}
_EST_T_ES = {"active":"Activo","completed":"Finalizado","on-hold":"Suspendido",
             "revoked":"Cancelado","draft":"Borrador"}


# ──────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL — crear_paciente_completo
# ──────────────────────────────────────────────────────────────

def crear_paciente_completo(form):
    """
    Recibe request.form de Flask y crea todos los recursos FHIR
    en un único Bundle transaction atómico.
    Retorna (patient_id, nombre_completo) si fue exitoso, (None, None) si falló.
    """

    # ── Datos del paciente ──────────────────────────────────────
    datos_paciente = {
        "nombre":            form.get("nombre", "").strip(),
        "apellido":          form.get("apellido", "").strip(),
        "segundo_apellido":  form.get("segundo_apellido", "").strip(),
        "rut":               form.get("rut", "").strip(),
        "fecha_nacimiento":  form.get("fecha_nacimiento", "").strip(),
        "sexo_biologico":    form.get("sexo_biologico", "Hombre"),
        "identidad_genero":  form.get("identidad_genero", "Masculino"),
        "nacionalidad":      form.get("nacionalidad", "Chile"),
        "estado_civil":      form.get("estado_civil", "").strip(),
        "pueblo_indigena":   form.get("pueblo_indigena", "").strip(),
        "afrodescendiente":  form.get("afrodescendiente", "No"),
        "nivel_educacional": form.get("nivel_educacional", "").strip(),
        "ultimo_curso":      form.get("ultimo_curso", "").strip(),
        "prevision":         form.get("prevision", "").strip(),
        "telefono":          form.get("telefono", "").strip(),
    }

    recurso_paciente = construir_paciente_fhir(datos_paciente)
    nombre_completo  = f"{datos_paciente['nombre']} {datos_paciente['apellido']}".strip()

    # UUID temporal para referencias internas del bundle.
    # El servidor resuelve estas referencias y asigna IDs reales al procesar.
    patient_uuid = f"urn:uuid:{_uuid.uuid4()}"
    subject_ref  = {"reference": patient_uuid}

    entries = []

    # ── 1. Patient ─────────────────────────────────────────────
    entries.append({
        "fullUrl":  patient_uuid,
        "resource": recurso_paciente,
        "request":  {"method": "POST", "url": "Patient"},
    })

    # ── 2. Condiciones médicas ──────────────────────────────────
    for i, diag in enumerate(form.getlist("cond_diagnostico[]")):
        if not diag.strip():
            continue
        certeza = _val_list(form, "cond_certeza[]", i) or "Confirmado"
        estado  = _val_list(form, "cond_estado[]", i) or "Activa"
        fecha   = _val_list(form, "cond_fecha[]", i)

        _sno  = DIAGNOSTICOS.get(diag.strip())
        _code = {
            "coding": [{"system": "http://snomed.info/sct",
                        "code":    _sno["code"],
                        "display": _sno["display"]}],
            "text": diag.strip()
        } if _sno else {"text": diag.strip()}

        recurso = {
            "resourceType":       "Condition",
            "subject":            subject_ref,
            "code":               _code,
            "verificationStatus": construir_verification_status(certeza),
            "clinicalStatus":     construir_clinical_status(estado, tipo="condicion"),
        }
        if fecha:
            recurso["recordedDate"] = fecha

        entries.append({
            "fullUrl":  f"urn:uuid:{_uuid.uuid4()}",
            "resource": recurso,
            "request":  {"method": "POST", "url": "Condition"},
        })

    # ── 3. Alergias ─────────────────────────────────────────────
    for i, sust in enumerate(form.getlist("alergia_sustancia[]")):
        if not sust.strip():
            continue
        manif  = _val_list(form, "alergia_manifestacion[]", i)
        crit   = _val_list(form, "alergia_criticidad[]", i) or "Baja"
        tipo   = _val_list(form, "alergia_tipo[]", i) or "Alergia"
        estado = _val_list(form, "alergia_estado[]", i) or "Activa"
        fecha  = _val_list(form, "alergia_fecha[]", i)

        _ss = SUSTANCIAS_ALERGIAS.get(sust.strip())
        _cs = {
            "coding": [{"system": "http://snomed.info/sct",
                        "code":    _ss["code"],
                        "display": _ss["display"]}],
            "text": sust.strip()
        } if _ss else {"text": sust.strip()}

        recurso = {
            "resourceType":   "AllergyIntolerance",
            "patient":        subject_ref,
            "code":           _cs,
            "type":           TIPO_ALERGIA.get(tipo, "allergy"),
            "criticality":    CRITICIDAD_ALERGIA.get(crit, "low"),
            "clinicalStatus": construir_clinical_status(estado, tipo="alergia"),
        }
        if manif:
            _sm = MANIFESTACIONES_ALERGICAS.get(manif)
            _me = {
                "coding": [{"system": "http://snomed.info/sct",
                            "code":    _sm["code"],
                            "display": _sm["display"]}],
                "text": manif
            } if _sm else {"text": manif}
            recurso["reaction"] = [{"manifestation": [_me]}]
        if fecha:
            recurso["recordedDate"] = fecha

        entries.append({
            "fullUrl":  f"urn:uuid:{_uuid.uuid4()}",
            "resource": recurso,
            "request":  {"method": "POST", "url": "AllergyIntolerance"},
        })

    # ── 4. Medicamentos ─────────────────────────────────────────
    for i, nombre in enumerate(form.getlist("med_nombre[]")):
        if not nombre.strip():
            continue
        dosis_val  = _val_list(form, "med_dosis_val[]", i)
        dosis_unit = _val_list(form, "med_dosis_unit[]", i) or "mg"
        frecuencia = _val_list(form, "med_frecuencia[]", i) or "1"
        periodo    = _val_list(form, "med_periodo[]", i) or "8"
        per_unit   = _val_list(form, "med_periodo_unit[]", i) or "h"
        via        = _val_list(form, "med_via[]", i) or "Oral"
        estado     = _val_list(form, "med_estado[]", i) or "Activo"
        fecha      = _val_list(form, "med_fecha[]", i)

        dosage = {
            "text":  f"{dosis_val} {dosis_unit} cada {periodo}{per_unit} vía {via.lower()}",
            "route": construir_via_administracion(via),
        }
        try:
            dosage["timing"] = {"repeat": {
                "frequency":  int(frecuencia),
                "period":     float(periodo),
                "periodUnit": per_unit,
            }}
        except ValueError:
            pass
        try:
            dosage["doseAndRate"] = [{"doseQuantity": {
                "value":  float(dosis_val),
                "unit":   dosis_unit,
                "system": "http://unitsofmeasure.org",
                "code":   dosis_unit,
            }}]
        except ValueError:
            pass

        _sm = MEDICAMENTOS_CLINICOS.get(nombre.strip())
        _cm = {
            "coding": [{"system": "http://snomed.info/sct",
                        "code":    _sm["code"],
                        "display": nombre.strip()}],
            "text": nombre.strip()
        } if _sm else {"text": nombre.strip()}

        recurso = {
            "resourceType":              "MedicationRequest",
            "subject":                   subject_ref,
            "status":                    ESTADO_MEDICAMENTO.get(estado, "active"),
            "intent":                    "order",
            "medicationCodeableConcept": _cm,
            "dosageInstruction":         [dosage],
        }
        if fecha:
            recurso["authoredOn"] = fecha

        entries.append({
            "fullUrl":  f"urn:uuid:{_uuid.uuid4()}",
            "resource": recurso,
            "request":  {"method": "POST", "url": "MedicationRequest"},
        })

    # ── 5. Intervenciones ───────────────────────────────────────
    _act_map = {
        "active":          "in-progress",
        "on-hold":         "on-hold",
        "completed":       "completed",
        "revoked":         "cancelled",
        "draft":           "not-started",
        "entered-in-error":"entered-in-error",
    }
    for i, nom in enumerate(form.getlist("interv_nombre[]")):
        if not nom.strip():
            continue
        tipo   = _val_list(form, "interv_tipo[]", i) or "Otro"
        estado = _val_list(form, "interv_estado[]", i) or "Activo"
        inicio = _val_list(form, "interv_inicio[]", i)
        fin    = _val_list(form, "interv_fin[]", i)

        periodo = {}
        if inicio: periodo["start"] = inicio
        if fin:    periodo["end"]   = fin

        _tipo_data   = TIPO_TRATAMIENTO.get(tipo)
        _plan_status = ESTADO_TRATAMIENTO.get(estado, "active")
        _cat = {
            "coding": [{"system": "http://snomed.info/sct",
                        "code":    _tipo_data["code"],
                        "display": _tipo_data["display"]}],
            "text": tipo
        } if _tipo_data else {"text": tipo}

        recurso = {
            "resourceType": "CarePlan",
            "subject":      subject_ref,
            "status":       _plan_status,
            "intent":       "plan",
            "title":        nom.strip(),
            "category":     [_cat],
        }
        if periodo:
            recurso["period"] = periodo

        _trat_data = TRATAMIENTOS_CLINICOS.get(nom.strip())
        if _trat_data:
            recurso["activity"] = [{
                "detail": {
                    "code": {
                        "coding": [{"system": "http://snomed.info/sct",
                                    "code":    _trat_data["code"],
                                    "display": _trat_data["display"]}],
                        "text": nom.strip()
                    },
                    "status": _act_map.get(_plan_status, "unknown"),
                }
            }]

        entries.append({
            "fullUrl":  f"urn:uuid:{_uuid.uuid4()}",
            "resource": recurso,
            "request":  {"method": "POST", "url": "CarePlan"},
        })

    # ── 6. Observaciones ────────────────────────────────────────
    for i, tipo in enumerate(form.getlist("obs_tipo[]")):
        if not tipo:
            continue
        val   = _val_list(form, "obs_valor[]", i)
        val2  = _val_list(form, "obs_valor2[]", i)
        fecha = _val_list(form, "obs_fecha[]", i)

        if not val or not fecha:
            continue

        fecha = _normalizar_datetime(fecha)

        try:
            recurso = construir_observation(
                tipo_usuario = tipo,
                valor        = float(val),
                subject_url  = patient_uuid,   # ← UUID temporal, no Patient/ID
                fecha_hora   = fecha,
                valor2       = float(val2) if val2 else None,
            )
            entries.append({
                "fullUrl":  f"urn:uuid:{_uuid.uuid4()}",
                "resource": recurso,
                "request":  {"method": "POST", "url": "Observation"},
            })
        except Exception as e:
            print(f"[FHIR] ERROR preparando Observation '{tipo}': {e}")

    # ── Envío del Bundle transaction ────────────────────────────
    bundle = {
        "resourceType": "Bundle",
        "type":         "transaction",
        "entry":        entries,
    }

    print(f"[FHIR] Enviando Bundle transaction ({len(entries)} recursos)...")
    resp = _post_transaction(bundle)
    if not resp:
        return None, None

    # El servidor devuelve las entradas en el mismo orden que el request.
    # La primera siempre es el Patient → extraemos su ID del campo location.
    try:
        location   = resp["entry"][0]["response"]["location"]
        patient_id = location.split("/")[1]
        print(f"[FHIR] Bundle OK — Patient ID: {patient_id}, {len(entries)} recursos creados")
        return patient_id, nombre_completo
    except (KeyError, IndexError, AttributeError) as e:
        print(f"[FHIR] ERROR extrayendo Patient ID de la respuesta: {e}")
        print(f"[FHIR] Respuesta del servidor: {resp}")
        return None, None


# ──────────────────────────────────────────────────────────────
# FUNCIÓN — obtener_ficha_completa
# ──────────────────────────────────────────────────────────────
def obtener_ficha_completa(patient_id):
    # ── Consultas paralelas ────────────────────────────────
    _q = {
        "patient":      (f"{BASE_URL}/Patient/{patient_id}",       None),
        "conditions":   (f"{BASE_URL}/Condition",                  {"patient": patient_id}),
        "allergies":    (f"{BASE_URL}/AllergyIntolerance",          {"patient": patient_id}),
        "medications":  (f"{BASE_URL}/MedicationRequest",           {"patient": patient_id}),
        "treatments":   (f"{BASE_URL}/CarePlan",                    {"patient": patient_id}),
        "observations": (f"{BASE_URL}/Observation",                 {"patient": patient_id, "_count": 200}),
    }
    _res = {}
    with ThreadPoolExecutor(max_workers=6) as _ex:
        _ft = {_ex.submit(_get, url, params): key for key, (url, params) in _q.items()}
        for _f in as_completed(_ft):
            _res[_ft[_f]] = _f.result()

    raw = _res["patient"]
    if not raw:
        return None

    nombres  = raw.get("name", [])
    nombre   = apellido = ""
    if nombres:
        n = nombres[0]
        nombre   = " ".join(n.get("given", [])) or n.get("text", "")
        apellido = n.get("family", "")

    rut = "(no disponible)"
    for ident in raw.get("identifier", []):
        if "regcivil" in ident.get("system", "").lower() or "run" in ident.get("system", "").lower():
            rut = ident.get("value", "(no disponible)")
            break

    sexo = genero = nacionalidad = "(no disponible)"
    pueblo_indigena = afrodescendiente = nivel_educacional = prevision = "(no disponible)"
    ultimo_curso = None

    for ext in raw.get("extension", []):
        url = ext.get("url", "")
        if   "SexoBiologico"          in url: sexo            = _coding_display(ext.get("valueCodeableConcept", {})) or sexo
        elif "IdentidadDeGenero"       in url: genero          = _coding_display(ext.get("valueCodeableConcept", {})) or genero
        elif "CodigoPaises"            in url:
            cc = ext.get("valueCodeableConcept", {})
            nacionalidad = cc.get("text") or _coding_display(cc) or nacionalidad
        elif "PuebloAfrodescendiente"  in url: afrodescendiente = "Sí" if ext.get("valueBoolean") else "No"
        elif "PuebloIndigena"          in url: pueblo_indigena  = _coding_display(ext.get("valueCodeableConcept", {})) or pueblo_indigena
        elif "UltimoCursoAprobado"     in url: ultimo_curso     = ext.get("valueInteger")
        elif "NivelEducacional"        in url: nivel_educacional= _coding_display(ext.get("valueCodeableConcept", {})) or nivel_educacional
        elif "Prevision"               in url: prevision        = _coding_display(ext.get("valueCodeableConcept", {})) or prevision

    estado_civil = _coding_display(raw.get("maritalStatus", {})) or "(no disponible)"

    telefono = "(no disponible)"
    for tc in raw.get("telecom", []):
        if tc.get("system") == "phone" and tc.get("use") == "mobile":
            telefono = tc.get("value", "(no disponible)")
            break

    # Calcular edad
    from datetime import date as _date
    edad = "(no disponible)"
    fnac_str = raw.get("birthDate", "")
    if fnac_str:
        try:
            bd    = _date.fromisoformat(fnac_str)
            today = _date.today()
            edad  = str(today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))) + " años"
        except Exception:
            pass

    paciente = {
        "fhir_id": patient_id, "nombre": nombre, "apellido": apellido,
        "rut": rut, "fecha_nacimiento": raw.get("birthDate", "(no disponible)"),
        "edad": edad,
        "sexo_biologico": sexo, "identidad_genero": genero, "nacionalidad": nacionalidad,
        "estado_civil": estado_civil, "telefono": telefono,
        "pueblo_indigena": pueblo_indigena, "afrodescendiente": afrodescendiente,
        "nivel_educacional": nivel_educacional, "ultimo_curso": ultimo_curso,
        "prevision": prevision,
    }

    # ── Condiciones ───────────────────────────────────────
    condiciones = []
    for c in _entradas(_res["conditions"]):
        condiciones.append({
            "diagnostico": _coding_display(c.get("code", {})) or "(sin nombre)",
            "certeza":     _CERT_ES.get(_cod(c.get("verificationStatus", {})),
                        _coding_display(c.get("verificationStatus", {}))) or "(no disponible)",
            "estado":      _EST_C_ES.get(_cod(c.get("clinicalStatus", {})),
                        _coding_display(c.get("clinicalStatus", {}))) or "(no disponible)",
            "fecha":       c.get("onsetDateTime") or c.get("recordedDate", "(no disponible)"),
        })

    # ── Alergias ──────────────────────────────────────────
    alergias = []
    for a in _entradas(_res["allergies"]):
        manif = "(no disponible)"
        reacs = a.get("reaction", [])
        if reacs:
            manifs = reacs[0].get("manifestation", [])
            if manifs:
                manif = manifs[0].get("text") or _coding_display(manifs[0]) or manif
        alergias.append({
            "sustancia":     _coding_display(a.get("code", {})) or "(sin nombre)",
            "manifestacion": manif,
            "criticidad":    _CRIT_ES.get(a.get("criticality", ""), a.get("criticality", "(no disponible)")),
            "tipo":          _TIPO_ES.get(a.get("type", ""), a.get("type", "(no disponible)")),
            "estado":        _EST_A_ES.get(_cod(a.get("clinicalStatus", {})),
                            _coding_display(a.get("clinicalStatus", {}))) or "(no disponible)",
            "fecha":         a.get("onsetDateTime") or a.get("recordedDate", "(no disponible)"),
        })

    # ── Medicamentos ──────────────────────────────────────
    medicamentos = []
    for m in _entradas(_res["medications"]):
        dosages = m.get("dosageInstruction", [])
        dosis = frecuencia = via = "(no disponible)"
        if dosages:
            d = dosages[0]
            dr = d.get("doseAndRate", [])
            if dr:
                dq = dr[0].get("doseQuantity", {})
                dosis = f"{dq.get('value','')} {dq.get('unit','')}".strip()
            rep = d.get("timing", {}).get("repeat", {})
            if rep:
                frecuencia = f"c/{rep.get('period','')} {rep.get('periodUnit','')}"
            via = _coding_display(d.get("route", {})) or d.get("text", "(no disponible)")
        nombre_med = _coding_display(m.get("medicationCodeableConcept", {})) or "(sin nombre)"
        medicamentos.append({
            "nombre":    nombre_med,
            "dosis":     dosis,
            "frecuencia":frecuencia,
            "via":       via,
            "estado":    _EST_M_ES.get(m.get("status", ""), m.get("status", "(no disponible)")),
            "fecha":     m.get("authoredOn", "(no disponible)"),
        })

    # ── Tratamientos ──────────────────────────────────────
    tratamientos = []
    for t in _entradas(_res["treatments"]):
        cats = t.get("category", [])
        # tipo guardado en category[0].text 
        tipo_val = cats[0].get("text", "(no disponible)") if cats else "(no disponible)"
        tratamientos.append({
            "nombre": t.get("title") or t.get("description", "(sin nombre)"),
            "tipo":   tipo_val,
            "estado": _EST_T_ES.get(t.get("status", ""), t.get("status", "(no disponible)")),
            "inicio": t.get("period", {}).get("start", "(no disponible)"),
            "fin":    t.get("period", {}).get("end", ""),
        })

    # ── Observaciones — agrupar por tipo y calcular estadísticas (esto me lo diste al ultimo)──
    

    obs_raw = _entradas(_res["observations"])

    observaciones = []   # lista simple (backward compat)
    obs_por_tipo  = {}   # agrupado para el dashboard

    for o in obs_raw:
        tipo  = _coding_display(o.get("code", {})) or "(sin nombre)"
        fecha = o.get("effectiveDateTime") or o.get("issued", "")

        # Fecha corta legible
        
        dt_obj     = _dt.fromisoformat(fecha.replace("Z", "+00:00"))
        fecha_corta = _fecha_corta(fecha)

        # Extraer valor(es)
        es_presion = False
        valor = valor2 = None
        unidad = ""

        if "valueQuantity" in o:
            vq     = o["valueQuantity"]
            valor  = vq.get("value")
            unidad = vq.get("unit") or vq.get("code", "")
            valor_str = str(valor) if valor is not None else "(no disponible)"

        elif "component" in o:
            es_presion = True
            partes = []
            for comp in o["component"]:
                ct  = _coding_display(comp.get("code", {})) or ""
                vq  = comp.get("valueQuantity", {})
                val = vq.get("value")
                uni = vq.get("unit", "mmHg")
                unidad = uni
                # sistólica / diastólica por nombre del componente
                ct_low = ct.lower()
                if any(s in ct_low for s in ["systol","sistól","sistol"]):
                    valor = val
                elif any(s in ct_low for s in ["diastol","diastól"]):
                    valor2 = val
                partes.append(f"{ct}: {val} {uni}")
            valor_str = " | ".join(partes)

        else:
            valor_str = o.get("valueString", "(no disponible)")

        # Lista plana 
        observaciones.append({
            "tipo": tipo, "valor": valor_str,
            "unidad": unidad, "fecha": fecha,
        })

        # Agrupado para dashboard
        if tipo not in obs_por_tipo:
            obs_por_tipo[tipo] = {
                "entradas":  [],
                "unidad":    unidad,
                "es_presion":es_presion,
            }
        obs_por_tipo[tipo]["entradas"].append({
            "fecha":       fecha,
            "fecha_corta": fecha_corta,
            "valor":       valor,
            "valor2":      valor2,
        })

    # Calcular estadísticas por tipo
    obs_dashboard = {}
    for tipo, data in obs_por_tipo.items():
        entradas = sorted(data["entradas"], key=lambda x: x.get("fecha",""))
        vals  = [e["valor"]  for e in entradas if e["valor"]  is not None]
        vals2 = [e["valor2"] for e in entradas if e.get("valor2") is not None]

        def _stats(lst):
            if not lst: return None, None, None
            return round(min(lst),1), round(max(lst),1), round(sum(lst)/len(lst),1)

        mn, mx, av    = _stats(vals)
        mn2, mx2, av2 = _stats(vals2)

        obs_dashboard[tipo] = {
            "entradas":  entradas,
            "unidad":    data["unidad"],
            "es_presion":data["es_presion"],
            "total":     len(entradas),
            "ultimo":    vals[-1]  if vals  else None,
            "ultimo2":   vals2[-1] if vals2 else None,
            "minimo":  mn,  "maximo":  mx,  "promedio":  av,
            "minimo2": mn2, "maximo2": mx2, "promedio2": av2,
        }
    return {
        "paciente": paciente, "condiciones": condiciones, "alergias": alergias,
        "medicamentos": medicamentos, "tratamientos": tratamientos, "observaciones": observaciones,
        "obs_dashboard": obs_dashboard,
    }



# ──────────────────────────────────────────────────────────────
# FUNCIÓN — obtener_resumen_paciente
# ──────────────────────────────────────────────────────────────

def obtener_resumen_paciente(patient_id):
    """
    Obtiene nombre, apellido y RUT de un Patient en el servidor FHIR.
    Retorna un dict con los datos o None si no se encuentra.
    """
    raw = _get(f"{BASE_URL}/Patient/{patient_id}")
    if not raw:
        return None

    # Nombre
    nombres  = raw.get("name", [])
    nombre   = "(sin nombre)"
    apellido = ""
    if nombres:
        n        = nombres[0]
        given    = n.get("given", [])
        nombre   = " ".join(given) if given else n.get("text", "(sin nombre)")
        apellido = n.get("family", "")

    # RUT
    rut = "(no disponible)"
    for ident in raw.get("identifier", []):
        if "regcivil" in ident.get("system", "").lower() or \
           "run" in ident.get("system", "").lower():
            rut = ident.get("value", "(no disponible)")
            break

    return {
        "fhir_id":  patient_id,
        "nombre":   nombre,
        "apellido": apellido,
        "rut":      rut,
    }

# ──────────────────────────────────────────────────────────────
# FUNCIÓN — listar_pacientes
# ──────────────────────────────────────────────────────────────

def listar_pacientes():
    """Trae todos los pacientes del servidor FHIR directamente."""
    bundle = _get(f"{BASE_URL}/Patient", params={
        "_count": 200,
        "_sort": "family",
        "_elements": "id,name,identifier",   # solo los campos que necesitamos
    })
    if not bundle:
        return []

    pacientes = []
    for r in _entradas(bundle):
        nombres = r.get("name", [])
        nombre = apellido = ""
        if nombres:
            n        = nombres[0]
            nombre   = " ".join(n.get("given", [])) or n.get("text", "")
            apellido = n.get("family", "")

        rut = "(no disponible)"
        for ident in r.get("identifier", []):
            sys = ident.get("system", "").lower()
            if "regcivil" in sys or "run" in sys:
                rut = ident.get("value", "(no disponible)")
                break

        pacientes.append({
            "fhir_id":  r.get("id", ""),
            "nombre":   nombre,
            "apellido": apellido,
            "rut":      rut,
            "estado":   "activo",   # campo decorativo
        })

    return pacientes

def _obtener_bundle_ids_paciente(patient_id):
    """Obtiene los bundle_ids de atenciones del paciente desde DocumentReference."""
    bundle = _get(f"{BASE_URL}/DocumentReference", params={
        "patient": patient_id, "_count": 500, "_elements": "content",
    })
    ids = []
    for r in _entradas(bundle):
        content = r.get("content", [{}])
        url = content[0].get("attachment", {}).get("url", "") if content else ""
        if "/Bundle/" in url:
            ids.append(url.split("/Bundle/")[-1])
    return ids

##Eliminar paciente y todos los recursos relacionados
def _eliminar_recursos_clinicos(patient_id):
    total = 0

    # 1. DocumentReference primero (referencia al Bundle y al Encounter)
    bundle = _get(f"{BASE_URL}/DocumentReference",
                  params={"patient": patient_id, "_count": 1000})
    for entry in (bundle.get("entry", []) if bundle else []):
        rid = entry.get("resource", {}).get("id")
        if rid:
            ok = _delete(f"{BASE_URL}/DocumentReference/{rid}")
            if ok: total += 1
            print(f"[FHIR] DELETE DocumentReference/{rid} → {'OK' if ok else 'FALLO'}")

    # 2. Composition (referencia al Encounter y a los recursos clínicos)
    bundle = _get(f"{BASE_URL}/Composition",
                  params={"subject": f"Patient/{patient_id}", "_count": 1000})
    for entry in (bundle.get("entry", []) if bundle else []):
        rid = entry.get("resource", {}).get("id")
        if rid:
            ok = _delete(f"{BASE_URL}/Composition/{rid}")
            if ok: total += 1
            print(f"[FHIR] DELETE Composition/{rid} → {'OK' if ok else 'FALLO'}")

    # 3. Recursos clínicos ANTES que el Encounter porque lo referencian
    for recurso in ["Observation", "Condition", "AllergyIntolerance",
                    "MedicationRequest", "CarePlan"]:
        bundle = _get(f"{BASE_URL}/{recurso}",
                      params={"patient": patient_id, "_count": 1000})
        for entry in (bundle.get("entry", []) if bundle else []):
            rid = entry.get("resource", {}).get("id")
            if rid:
                ok = _delete(f"{BASE_URL}/{recurso}/{rid}")
                if ok: total += 1
                print(f"[FHIR] DELETE {recurso}/{rid} → {'OK' if ok else 'FALLO'}")

    # 4. Encounter al final, ahora que nada lo referencia
    bundle = _get(f"{BASE_URL}/Encounter",
                  params={"patient": patient_id, "_count": 1000})
    for entry in (bundle.get("entry", []) if bundle else []):
        rid = entry.get("resource", {}).get("id")
        if rid:
            ok = _delete(f"{BASE_URL}/Encounter/{rid}")
            if ok: total += 1
            print(f"[FHIR] DELETE Encounter/{rid} → {'OK' if ok else 'FALLO'}")

    return total


def _eliminar_bundles(bundle_ids):
    """
    Elimina Bundle documents por sus IDs directos.
    Los bundles no tienen parámetro de búsqueda por paciente en FHIR R4
    """
    total = 0
    for bid in (bundle_ids or []):
        if bid:
            ok = _delete(f"{BASE_URL}/Bundle/{bid}")
            if ok:
                total += 1
            print(f"[FHIR] DELETE Bundle/{bid} → {'OK' if ok else 'FALLO'}")
    return total


def resetear_paciente(patient_id):
    bundle_ids = _obtener_bundle_ids_paciente(patient_id)
    b = _eliminar_bundles(bundle_ids)
    c = _eliminar_recursos_clinicos(patient_id)
    print(f"[FHIR] Reseteo OK — {b} bundles + {c} recursos eliminados. Patient conservado.")
    return True


def eliminar_paciente(patient_id):
    bundle_ids = _obtener_bundle_ids_paciente(patient_id)
    b  = _eliminar_bundles(bundle_ids)
    c  = _eliminar_recursos_clinicos(patient_id)
    ok = _delete(f"{BASE_URL}/Patient/{patient_id}")
    print(f"[FHIR] DELETE Patient/{patient_id} → {'OK' if ok else 'FALLO'}")
    print(f"[FHIR] Eliminación completa — {b} bundles + {c} recursos + Patient.")
    return ok

def modificar_ficha_completa(patient_id, form):
    """Modifica la ficha en un único Bundle transaction (fetch paralelo + PUT/POST atómico)."""

    # ── 1. IDs de recursos existentes del formulario ──────
    cond_ids = [x for x in form.getlist("exist_cond_id[]")      if x]
    aler_ids = [x for x in form.getlist("exist_alergia_id[]")   if x]
    med_ids  = [x for x in form.getlist("exist_med_id[]")       if x]
    trat_ids = [x for x in form.getlist("exist_interv_id[]")    if x]

    # ── 2. Fetch paralelo de todos los recursos actuales ──
    tasks = {"patient": (f"{BASE_URL}/Patient/{patient_id}", None)}
    for cid in cond_ids:
        tasks[f"cond_{cid}"] = (f"{BASE_URL}/Condition/{cid}", None)
    for aid in aler_ids:
        tasks[f"aler_{aid}"] = (f"{BASE_URL}/AllergyIntolerance/{aid}", None)
    for mid in med_ids:
        tasks[f"med_{mid}"]  = (f"{BASE_URL}/MedicationRequest/{mid}", None)
    for tid in trat_ids:
        tasks[f"trat_{tid}"] = (f"{BASE_URL}/CarePlan/{tid}", None)

    fetched = {}
    with ThreadPoolExecutor(max_workers=min(len(tasks), 10)) as ex:
        fts = {ex.submit(_get, url, params): key for key, (url, params) in tasks.items()}
        for ft in as_completed(fts):
            fetched[fts[ft]] = ft.result()

    entries = []
    ref = {"reference": f"Patient/{patient_id}"}

    # ── 3. Patient ────────────────────────────────────────
    cur_p = fetched.get("patient")
    if cur_p:
        nombre           = form.get("nombre","").strip()
        apellido         = form.get("apellido","").strip()
        rut              = form.get("rut","").strip()
        fnac             = form.get("fecha_nacimiento","").strip()
        sexo             = form.get("sexo_biologico","")
        genero           = form.get("identidad_genero","")
        nacion           = form.get("nacionalidad","")
        estado_civil     = form.get("estado_civil","").strip()
        pueblo           = form.get("pueblo_indigena","").strip()
        afro_raw         = form.get("afrodescendiente","No")
        nivel_educ       = form.get("nivel_educacional","").strip()
        ultimo_curso_str = form.get("ultimo_curso","").strip()
        prevision        = form.get("prevision","").strip()
        telefono         = form.get("telefono","").strip()

        cur_p_original = copy.deepcopy(cur_p)

        cur_p["name"] = [{"use":"official","family":apellido,"given":nombre.split(),
                          "text":f"{nombre} {apellido}".strip()}]
        if fnac: cur_p["birthDate"] = fnac
        if rut:  cur_p["identifier"] = [construir_identifier_rut(rut)]

        exts = []
        if sexo:
            cur_p["gender"] = SEXO_A_GENDER_FHIR.get(sexo, "unknown")
            e = construir_extension_sexo(sexo)
            if e: exts.append(e)
        if genero:
            e = construir_extension_genero(genero)
            if e: exts.append(e)
        if nacion:
            e = construir_extension_nacionalidad(nacion)
            if e: exts.append(e)
        if pueblo:
            e = construir_extension_pueblo_indigena(pueblo)
            if e: exts.append(e)
        afro_val = afro_raw in ("Sí","sí","si","true","True","1")
        exts.append(construir_extension_afrodescendiente(afro_val))
        if nivel_educ:
            e = construir_extension_nivel_educacional(nivel_educ)
            if e: exts.append(e)
            if ultimo_curso_str:
                try: exts.append(construir_extension_ultimo_curso(int(ultimo_curso_str)))
                except (ValueError, TypeError): pass
        if prevision:
            e = construir_extension_prevision(prevision)
            if e: exts.append(e)
        if exts:
            cur_p["extension"] = exts
        if estado_civil:
            ms = construir_marital_status(estado_civil)
            if ms: cur_p["maritalStatus"] = ms
        if telefono:
            cur_p["telecom"] = [{"system":"phone","value":telefono,"use":"mobile"}]

        if cur_p != cur_p_original:
            entries.append({
                "fullUrl":  f"{BASE_URL}/Patient/{patient_id}",
                "resource": cur_p,
                "request":  {"method":"PUT","url":f"Patient/{patient_id}"},
            })
            print(f"[FHIR] Bundle PUT Patient/{patient_id}")
        else:
            print(f"[FHIR] SKIP Patient/{patient_id} (sin cambios)")

    # ── 4. Condiciones existentes ─────────────────────────
    for i, cid in enumerate(form.getlist("exist_cond_id[]")):
        if not cid: continue
        cur = fetched.get(f"cond_{cid}")
        if not cur: continue
        cur_original = copy.deepcopy(cur)

        diag    = _val_list(form,"exist_cond_diagnostico[]",i)
        certeza = _val_list(form,"exist_cond_certeza[]",i)
        estado  = _val_list(form,"exist_cond_estado[]",i)
        fecha   = _val_list(form,"exist_cond_fecha[]",i)

        if diag:
            _sno = DIAGNOSTICOS.get(diag)
            cur["code"] = {"coding":[{"system":"http://snomed.info/sct","code":_sno["code"],"display":_sno["display"]}],"text":diag} if _sno else {"text":diag}
        if certeza: cur["verificationStatus"] = construir_verification_status(certeza)
        if estado:  cur["clinicalStatus"]     = construir_clinical_status(estado,"condicion")
        if fecha:   cur["recordedDate"]       = fecha

        if cur != cur_original:
            entries.append({
                "fullUrl":  f"{BASE_URL}/Condition/{cid}",
                "resource": cur,
                "request":  {"method":"PUT","url":f"Condition/{cid}"},
            })
            print(f"[FHIR] Bundle PUT Condition/{cid}")
        else:
            print(f"[FHIR] SKIP Condition/{cid} (sin cambios)")

    # ── 5. Alergias existentes ────────────────────────────
    for i, aid in enumerate(form.getlist("exist_alergia_id[]")):
        if not aid: continue
        cur = fetched.get(f"aler_{aid}")
        if not cur: continue
        cur_original = copy.deepcopy(cur)

        sust   = _val_list(form,"exist_alergia_sustancia[]",i)
        manif  = _val_list(form,"exist_alergia_manifestacion[]",i)
        crit   = _val_list(form,"exist_alergia_criticidad[]",i)
        tipo   = _val_list(form,"exist_alergia_tipo[]",i)
        estado = _val_list(form,"exist_alergia_estado[]",i)

        if sust:
            _ss = SUSTANCIAS_ALERGIAS.get(sust)
            cur["code"] = {"coding":[{"system":"http://snomed.info/sct","code":_ss["code"],"display":_ss["display"]}],"text":sust} if _ss else {"text":sust}
        if crit:   cur["criticality"]    = CRITICIDAD_ALERGIA.get(crit,crit)
        if tipo:   cur["type"]           = TIPO_ALERGIA.get(tipo,tipo)
        if estado: cur["clinicalStatus"] = construir_clinical_status(estado,"alergia")
        if manif:
            _sm = MANIFESTACIONES_ALERGICAS.get(manif)
            _me = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":_sm["display"]}],"text":manif} if _sm else {"text":manif}
            cur["reaction"] = [{"manifestation":[_me]}]

        if cur != cur_original:
            entries.append({
                "fullUrl":  f"{BASE_URL}/AllergyIntolerance/{aid}",
                "resource": cur,
                "request":  {"method":"PUT","url":f"AllergyIntolerance/{aid}"},
            })
            print(f"[FHIR] Bundle PUT AllergyIntolerance/{aid}")
        else:
            print(f"[FHIR] SKIP AllergyIntolerance/{aid} (sin cambios)")

    # ── 6. Medicamentos existentes ────────────────────────
    for i, mid in enumerate(form.getlist("exist_med_id[]")):
        if not mid: continue
        cur = fetched.get(f"med_{mid}")
        if not cur: continue
        cur_original = copy.deepcopy(cur)

        nombre = _val_list(form,"exist_med_nombre[]",i)
        dv     = _val_list(form,"exist_med_dosis_val[]",i)
        du     = _val_list(form,"exist_med_dosis_unit[]",i)
        per    = _val_list(form,"exist_med_periodo[]",i)
        pu     = _val_list(form,"exist_med_periodo_unit[]",i)
        via    = _val_list(form,"exist_med_via[]",i)
        est    = _val_list(form,"exist_med_estado[]",i)
        fecha  = _val_list(form,"exist_med_fecha[]",i)

        if nombre:
            _sm = MEDICAMENTOS_CLINICOS.get(nombre)
            cur["medicationCodeableConcept"] = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":nombre}],"text":nombre} if _sm else {"text":nombre}
        if est:   cur["status"]     = ESTADO_MEDICAMENTO.get(est, cur.get("status","active"))
        if fecha: cur["authoredOn"] = fecha
        if cur.get("dosageInstruction"):
            d = cur["dosageInstruction"][0]
            if via: d["route"] = construir_via_administracion(via)
            if dv and du:
                try: d["doseAndRate"] = [{"doseQuantity":{"value":float(dv),"unit":du,"system":"http://unitsofmeasure.org","code":du}}]
                except ValueError: pass
            if per and pu:
                try: d["timing"] = {"repeat":{"frequency":1,"period":float(per),"periodUnit":pu}}
                except ValueError: pass
            cur["dosageInstruction"][0] = d

        if cur != cur_original:
            entries.append({
                "fullUrl":  f"{BASE_URL}/MedicationRequest/{mid}",
                "resource": cur,
                "request":  {"method":"PUT","url":f"MedicationRequest/{mid}"},
            })
            print(f"[FHIR] Bundle PUT MedicationRequest/{mid}")
        else:
            print(f"[FHIR] SKIP MedicationRequest/{mid} (sin cambios)")

    # ── 7. Intervenciones existentes ──────────────────────
    for i, tid in enumerate(form.getlist("exist_interv_id[]")):
        if not tid: continue
        cur = fetched.get(f"trat_{tid}")
        if not cur: continue
        cur_original = copy.deepcopy(cur)

        nom    = _val_list(form,"exist_interv_nombre[]",i)
        tipo   = _val_list(form,"exist_interv_tipo[]",i)
        estado = _val_list(form,"exist_interv_estado[]",i)
        inicio = _val_list(form,"exist_interv_inicio[]",i)
        fin    = _val_list(form,"exist_interv_fin[]",i)

        if nom:    cur["title"]  = nom
        if estado: cur["status"] = ESTADO_TRATAMIENTO.get(estado, cur.get("status","active"))
        if inicio: cur.setdefault("period",{})["start"] = inicio
        if fin:    cur.setdefault("period",{})["end"]   = fin
        if tipo or nom:
            tipo_actual = tipo or (cur.get("category",[{}])[0].get("text","Otro") if cur.get("category") else "Otro")
            cur["category"] = [{"text": tipo_actual}]

        if cur != cur_original:
            entries.append({
                "fullUrl":  f"{BASE_URL}/CarePlan/{tid}",
                "resource": cur,
                "request":  {"method":"PUT","url":f"CarePlan/{tid}"},
            })
            print(f"[FHIR] Bundle PUT CarePlan/{tid}")
        else:
            print(f"[FHIR] SKIP CarePlan/{tid} (sin cambios)")

    # ── 8. Nuevas condiciones ─────────────────────────────
    for i, diag in enumerate(form.getlist("new_cond_diagnostico[]")):
        if not diag.strip(): continue
        certeza = _val_list(form,"new_cond_certeza[]",i) or "Confirmado"
        estado  = _val_list(form,"new_cond_estado[]",i)  or "Activa"
        fecha   = _val_list(form,"new_cond_fecha[]",i)
        _sno    = DIAGNOSTICOS.get(diag.strip())
        _code   = {"coding":[{"system":"http://snomed.info/sct","code":_sno["code"],"display":_sno["display"]}],"text":diag.strip()} if _sno else {"text":diag.strip()}
        recurso = {"resourceType":"Condition","subject":ref,"code":_code,
                   "verificationStatus":construir_verification_status(certeza),
                   "clinicalStatus":construir_clinical_status(estado,"condicion")}
        if fecha: recurso["recordedDate"] = fecha
        entries.append({"fullUrl":f"urn:uuid:{_uuid.uuid4()}","resource":recurso,
                        "request":{"method":"POST","url":"Condition"}})

    # ── 9. Nuevas alergias ────────────────────────────────
    for i, sust in enumerate(form.getlist("new_alergia_sustancia[]")):
        if not sust.strip(): continue
        manif  = _val_list(form,"new_alergia_manifestacion[]",i)
        crit   = _val_list(form,"new_alergia_criticidad[]",i) or "Baja"
        tipo   = _val_list(form,"new_alergia_tipo[]",i)        or "Alergia"
        estado = _val_list(form,"new_alergia_estado[]",i)      or "Activa"
        fecha  = _val_list(form,"new_alergia_fecha[]",i)
        _ss    = SUSTANCIAS_ALERGIAS.get(sust.strip())
        _cs    = {"coding":[{"system":"http://snomed.info/sct","code":_ss["code"],"display":_ss["display"]}],"text":sust.strip()} if _ss else {"text":sust.strip()}
        recurso = {"resourceType":"AllergyIntolerance","patient":ref,"code":_cs,
                   "type":TIPO_ALERGIA.get(tipo,"allergy"),
                   "criticality":CRITICIDAD_ALERGIA.get(crit,"low"),
                   "clinicalStatus":construir_clinical_status(estado,"alergia")}
        if manif:
            _sm = MANIFESTACIONES_ALERGICAS.get(manif)
            _me = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":_sm["display"]}],"text":manif} if _sm else {"text":manif}
            recurso["reaction"] = [{"manifestation":[_me]}]
        if fecha: recurso["recordedDate"] = fecha
        entries.append({"fullUrl":f"urn:uuid:{_uuid.uuid4()}","resource":recurso,
                        "request":{"method":"POST","url":"AllergyIntolerance"}})

    # ── 10. Nuevos medicamentos ───────────────────────────
    for i, nombre in enumerate(form.getlist("new_med_nombre[]")):
        if not nombre.strip(): continue
        dv  = _val_list(form,"new_med_dosis_val[]",i)
        du  = _val_list(form,"new_med_dosis_unit[]",i)  or "mg"
        per = _val_list(form,"new_med_periodo[]",i)     or "8"
        pu  = _val_list(form,"new_med_periodo_unit[]",i) or "h"
        via = _val_list(form,"new_med_via[]",i)          or "Oral"
        est = _val_list(form,"new_med_estado[]",i)       or "Activo"
        fecha = _val_list(form,"new_med_fecha[]",i)
        _sm   = MEDICAMENTOS_CLINICOS.get(nombre.strip())
        _cm   = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":nombre.strip()}],"text":nombre.strip()} if _sm else {"text":nombre.strip()}
        dosage = {"text":f"{dv}{du} c/{per}{pu}","route":construir_via_administracion(via)}
        try: dosage["timing"]      = {"repeat":{"frequency":1,"period":float(per),"periodUnit":pu}}
        except ValueError: pass
        try: dosage["doseAndRate"] = [{"doseQuantity":{"value":float(dv),"unit":du,"system":"http://unitsofmeasure.org","code":du}}]
        except ValueError: pass
        recurso = {"resourceType":"MedicationRequest","subject":ref,
                   "status":ESTADO_MEDICAMENTO.get(est,"active"),"intent":"order",
                   "medicationCodeableConcept":_cm,"dosageInstruction":[dosage]}
        if fecha: recurso["authoredOn"] = fecha
        entries.append({"fullUrl":f"urn:uuid:{_uuid.uuid4()}","resource":recurso,
                        "request":{"method":"POST","url":"MedicationRequest"}})

    # ── 11. Nuevas intervenciones ─────────────────────────
    for i, nom in enumerate(form.getlist("new_interv_nombre[]")):
        if not nom.strip(): continue
        estado = _val_list(form,"new_interv_estado[]",i) or "Activo"
        tipo   = _val_list(form,"new_interv_tipo[]",i)   or "Otro"
        inicio = _val_list(form,"new_interv_inicio[]",i)
        fin    = _val_list(form,"new_interv_fin[]",i)
        periodo = {}
        if inicio: periodo["start"] = inicio
        if fin:    periodo["end"]   = fin
        recurso = {"resourceType":"CarePlan","subject":ref,
                   "status":ESTADO_TRATAMIENTO.get(estado,"active"),
                   "intent":"plan","title":nom.strip(),
                   "category":[{"text":tipo}]}
        if periodo: recurso["period"] = periodo
        entries.append({"fullUrl":f"urn:uuid:{_uuid.uuid4()}","resource":recurso,
                        "request":{"method":"POST","url":"CarePlan"}})

    # ── 12. Enviar todo en un solo Bundle transaction ─────
    if entries:
        resp = _post_transaction({"resourceType":"Bundle","type":"transaction","entry":entries})
        print(f"[FHIR] Bundle modificación → {len(entries)} ops {'OK' if resp else 'FALLO'}")
    else:
        print("[FHIR] Sin cambios detectados, no se envió Bundle")

    return True


def obtener_ficha_para_edicion(patient_id):
    """
    Igual que obtener_ficha_completa pero con campos extra necesarios para editar:
      - fhir_id en cada recurso (para hacer PUT/PATCH al servidor)
      - dosis separada en dosis_val + dosis_unit
      - frecuencia separada en periodo + periodo_unit
      - estados traducidos al español
    No modifica el formato que usa la pantalla de ver ficha.
    """

    # ── Consultas paralelas ────────────────────────────────
    _q = {
        "patient":     (f"{BASE_URL}/Patient/{patient_id}",       None),
        "conditions":  (f"{BASE_URL}/Condition",                  {"patient": patient_id}),
        "allergies":   (f"{BASE_URL}/AllergyIntolerance",          {"patient": patient_id}),
        "medications": (f"{BASE_URL}/MedicationRequest",           {"patient": patient_id}),
        "treatments":  (f"{BASE_URL}/CarePlan",                    {"patient": patient_id}),
    }
    _res = {}
    with ThreadPoolExecutor(max_workers=5) as _ex:
        _ft = {_ex.submit(_get, url, params): key for key, (url, params) in _q.items()}
        for _f in as_completed(_ft):
            _res[_ft[_f]] = _f.result()

    raw = _res["patient"]
    if not raw:
        return None
    nombres  = raw.get("name", [])
    nombre = apellido = ""
    if nombres:
        n        = nombres[0]
        nombre   = " ".join(n.get("given", [])) or n.get("text", "")
        apellido = n.get("family", "")

    rut = "(no disponible)"
    for ident in raw.get("identifier", []):
        if "regcivil" in ident.get("system", "").lower() or "run" in ident.get("system", "").lower():
            rut = ident.get("value", "(no disponible)")
            break

    sexo = genero = nacionalidad = "(no disponible)"
    pueblo_indigena = afrodescendiente = nivel_educacional = prevision = "(no disponible)"
    ultimo_curso = None

    for ext in raw.get("extension", []):
        url = ext.get("url", "")
        if   "SexoBiologico"          in url: sexo            = _coding_display(ext.get("valueCodeableConcept", {})) or sexo
        elif "IdentidadDeGenero"       in url: genero          = _coding_display(ext.get("valueCodeableConcept", {})) or genero
        elif "CodigoPaises"            in url:
            cc = ext.get("valueCodeableConcept", {})
            nacionalidad = cc.get("text") or _coding_display(cc) or nacionalidad
        elif "PuebloAfrodescendiente"  in url: afrodescendiente = "Sí" if ext.get("valueBoolean") else "No"
        elif "PuebloIndigena"          in url: pueblo_indigena  = _coding_display(ext.get("valueCodeableConcept", {})) or pueblo_indigena
        elif "UltimoCursoAprobado"     in url: ultimo_curso     = ext.get("valueInteger")
        elif "NivelEducacional"        in url: nivel_educacional= _coding_display(ext.get("valueCodeableConcept", {})) or nivel_educacional
        elif "Prevision"               in url: prevision        = _coding_display(ext.get("valueCodeableConcept", {})) or prevision

    estado_civil = _coding_display(raw.get("maritalStatus", {})) or "(no disponible)"

    telefono = "(no disponible)"
    for tc in raw.get("telecom", []):
        if tc.get("system") == "phone" and tc.get("use") == "mobile":
            telefono = tc.get("value", "(no disponible)")
            break

    # Calcular edad
    from datetime import date as _date
    edad = "(no disponible)"
    fnac_str = raw.get("birthDate", "")
    if fnac_str:
        try:
            bd    = _date.fromisoformat(fnac_str)
            today = _date.today()
            edad  = str(today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))) + " años"
        except Exception:
            pass

    paciente = {
        "fhir_id":           patient_id,
        "nombre":            nombre,
        "apellido":          apellido,
        "rut":               rut,
        "fecha_nacimiento":  raw.get("birthDate", "(no disponible)"),
        "edad":              edad,
        "sexo_biologico":    sexo,
        "identidad_genero":  genero,
        "nacionalidad":      nacionalidad,
        "estado_civil":      estado_civil,
        "telefono":          telefono,
        "pueblo_indigena":   pueblo_indigena,
        "afrodescendiente":  afrodescendiente,
        "nivel_educacional": nivel_educacional,
        "ultimo_curso":      ultimo_curso if ultimo_curso is not None else "",
        "prevision":         prevision,
    }

    # ── Condiciones ───────────────────────────────────────
    condiciones = []
    for c in _entradas(_res["conditions"]):
        cod_certeza = ""
        for coding in c.get("verificationStatus", {}).get("coding", []):
            cod_certeza = coding.get("code", "")
            break
        cod_estado = ""
        for coding in c.get("clinicalStatus", {}).get("coding", []):
            cod_estado = coding.get("code", "")
            break
        condiciones.append({
            "fhir_id":     c.get("id", ""),
            "diagnostico": _coding_display(c.get("code", {})) or "(sin nombre)",
            # display legible para mostrar en pantalla
            "certeza":     _CERT_ES.get(cod_certeza, _coding_display(c.get("verificationStatus", {}))) or "(no disponible)",
            "estado":      _EST_C_ES.get(cod_estado,  _coding_display(c.get("clinicalStatus", {})))    or "(no disponible)",
            # código raw para preseleccionar el <select> en el form
            "certeza_code": cod_certeza,
            "estado_code":  cod_estado,
            "fecha":        c.get("onsetDateTime") or c.get("recordedDate", "(no disponible)"),
        })

    # ── Alergias ──────────────────────────────────────────
    alergias = []
    for a in _entradas(_res["allergies"]):
        manif = "(no disponible)"
        reacs = a.get("reaction", [])
        if reacs:
            manifs = reacs[0].get("manifestation", [])
            if manifs:
                manif = manifs[0].get("text") or _coding_display(manifs[0]) or manif

        cod_estado_a = ""
        for coding in a.get("clinicalStatus", {}).get("coding", []):
            cod_estado_a = coding.get("code", "")
            break

        alergias.append({
            "fhir_id":       a.get("id", ""),
            "sustancia":     _coding_display(a.get("code", {})) or "(sin nombre)",
            "manifestacion": manif,
            "criticidad":    _CRIT_ES.get(a.get("criticality", ""), a.get("criticality", "(no disponible)")),
            "tipo":          _TIPO_ES.get(a.get("type", ""),         a.get("type",         "(no disponible)")),
            "estado":        _EST_A_ES.get(cod_estado_a, cod_estado_a) or "(no disponible)",
            "estado_code":   cod_estado_a,
            "fecha":         a.get("onsetDateTime") or a.get("recordedDate", "(no disponible)"),
        })

    # ── Medicamentos ──────────────────────────────────────
    medicamentos = []
    for m in _entradas(_res["medications"]):
        dosis_val = dosis_unit = periodo = periodo_unit = via = ""
        dosages = m.get("dosageInstruction", [])
        if dosages:
            d  = dosages[0]
            dr = d.get("doseAndRate", [])
            if dr:
                dq         = dr[0].get("doseQuantity", {})
                dosis_val  = str(dq.get("value", ""))
                dosis_unit = dq.get("unit", "mg")
            rep = d.get("timing", {}).get("repeat", {})
            if rep:
                periodo      = str(rep.get("period", ""))
                periodo_unit = rep.get("periodUnit", "h")
            via = _coding_display(d.get("route", {})) or d.get("text", "")

        cod_estado_m = m.get("status", "")
        medicamentos.append({
            "fhir_id":      m.get("id", ""),
            "nombre":       _coding_display(m.get("medicationCodeableConcept", {})) or "(sin nombre)",
            # campos separados para los inputs del formulario
            "dosis_val":    dosis_val,
            "dosis_unit":   dosis_unit,
            "periodo":      periodo,
            "periodo_unit": periodo_unit,
            "via":          via,
            "estado":       _EST_M_ES.get(cod_estado_m, cod_estado_m) or "(no disponible)",
            "estado_code":  cod_estado_m,
            "fecha":        m.get("authoredOn", "(no disponible)"),
        })

    # ── Tratamientos (CarePlan) ───────────────────────────
    tratamientos = []
    for t in _entradas(_res["treatments"]):
        cats = t.get("category", [])
        cod_estado_t = t.get("status", "")
        # tipo está en category[0].text 
        tipo_val = cats[0].get("text", "(no disponible)") if cats else "(no disponible)"
        tratamientos.append({
            "fhir_id":     t.get("id", ""),
            "nombre":      t.get("title") or t.get("description", "(sin nombre)"),
            "tipo":        tipo_val,
            "estado":      _EST_T_ES.get(cod_estado_t, cod_estado_t) or "(no disponible)",
            "estado_code": cod_estado_t,
            "inicio":      t.get("period", {}).get("start", "(no disponible)"),
            "fin":         t.get("period", {}).get("end", ""),
        })

    return {
        "paciente":      paciente,
        "condiciones":   condiciones,
        "alergias":      alergias,
        "medicamentos":  medicamentos,
        "tratamientos":  tratamientos,
    }




# ══════════════════════════════════════════════════════════════
# ATENCIÓN CLÍNICA — Encounter, Composition, Bundle
# ══════════════════════════════════════════════════════════════

def obtener_encuentro_activo(patient_id, encounter_id=None):
    """
    Si se pasa encounter_id, hace GET directo (evita race condition post-creación).
    Si no, busca por patient + status=in-progress.
    """
    if encounter_id:
        enc = _get(f"{BASE_URL}/Encounter/{encounter_id}")
        if enc and enc.get("status") == "in-progress":
            participant = enc.get("participant", [])
            estudiante  = participant[0].get("individual", {}).get("display", "") if participant else ""
            return {
                "patient_id":   patient_id,
                "encounter_id": enc.get("id", ""),
                "inicio":       enc.get("period", {}).get("start", ""),
                "estudiante":   estudiante,
            }

    # Fallback: búsqueda por parámetros (para cuando no viene de una creación reciente)
    bundle = _get(f"{BASE_URL}/Encounter", params={
        "patient": patient_id,
        "status":  "in-progress",
        "_count":  1,
    })
    entradas = _entradas(bundle)
    if not entradas:
        return None
    enc = entradas[0]
    participant = enc.get("participant", [])
    estudiante  = participant[0].get("individual", {}).get("display", "") if participant else ""
    return {
        "patient_id":   patient_id,
        "encounter_id": enc.get("id", ""),
        "inicio":       enc.get("period", {}).get("start", ""),
        "estudiante":   estudiante,
    }


def iniciar_atencion(patient_id, patient_rut, estudiante):
    """Crea un Encounter in-progress en el servidor FHIR."""
    from datetime import datetime as _dt, timezone
    ahora = _ahora_chile()
    recurso = {
        "resourceType": "Encounter",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB", "display": "ambulatory"
        },
        "type": [{"text": "Atención Clínica PHANTOM-UV"}],
        "subject":     {"reference": f"Patient/{patient_id}"},
        "participant": [{"individual": {"display": estudiante}}],
        "period":      {"start": ahora},
    }
    resp = _post("Encounter", recurso)
    if resp:
        print(f"[FHIR] Encounter creado → ID: {resp['id']}")
        return resp["id"], ahora
    return None, None


def obtener_obs_phantom(patient_id, inicio=None):
    """Consulta observaciones PHANTOM filtrando desde el inicio del encuentro."""
    LOINC_NOTA = "34109-9"

    params = {"patient": patient_id, "_sort": "-date", "_count": "200"}
    if inicio:
        # Solo observaciones desde que inició la atención
        params["date"] = f"ge{inicio}"

    bundle   = _get(f"{BASE_URL}/Observation", params=params)
    obs_raw  = _entradas(bundle)

    # Filtrar notas clínicas propias del sistema
    obs_raw  = [o for o in obs_raw
                if not o.get("valueString")
                and not any(c.get("code") == LOINC_NOTA
                            for c in o.get("code",{}).get("coding",[]))]

    obs_dashboard = _obs_to_dashboard(obs_raw)
    all_ids = [e["fhir_id"]
               for data in obs_dashboard.values()
               for e in data["entradas"] if e.get("fhir_id")]
    return obs_dashboard, all_ids

def finalizar_atencion(patient_id, encounter_id, nota_texto, estudiante):
    """
    Cierra la atención:
      1. Crea nota clínica si la hay.
      2. Consulta todos los recursos ya en FHIR para este encuentro.
      3. Cierra el Encounter.
      4. Crea Composition + Bundle document.
      5. Crea DocumentReference como registro permanente del historial.
    """
    ahora = _ahora_chile()

    # ── 0. Nota clínica de cierre ─────────────────────────
    if nota_texto.strip():
        nota_fhir = {
            "resourceType": "Observation", "status": "final",
            "category": [{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"exam"}]}],
            "code": {"coding":[{"system":"http://loinc.org","code":"34109-9","display":"Note"}],"text":"Nota clínica"},
            "subject":         {"reference": f"Patient/{patient_id}"},
            "encounter":       {"reference": f"Encounter/{encounter_id}"},
            "effectiveDateTime": ahora,
            "valueString":     nota_texto,
        }
        _post("Observation", nota_fhir)

    # ── 1. Traer Encounter y recursos en paralelo ─────────
    enc_ref_str = f"Encounter/{encounter_id}"
    _q = {
        "encounter":   (f"{BASE_URL}/Encounter/{encounter_id}",    None),
        "conditions":  (f"{BASE_URL}/Condition",                   {"encounter": encounter_id, "_count": 500}),
        "medications": (f"{BASE_URL}/MedicationRequest",            {"encounter": encounter_id, "_count": 500}),
        "treatments":  (f"{BASE_URL}/CarePlan",                    {"encounter": encounter_id, "_count": 500}),
        "obs_enc":     (f"{BASE_URL}/Observation",                 {"encounter": encounter_id, "_count": 500}),
        "allergies":   (f"{BASE_URL}/AllergyIntolerance",          {"patient": patient_id, "_count": 500}),
        "obs_phantom": (f"{BASE_URL}/Observation",                 {"patient": patient_id, "_sort": "-date", "_count": 500}),
    }
    _fetched = {}
    with ThreadPoolExecutor(max_workers=7) as ex:
        fts = {ex.submit(_get, url, params): key for key, (url, params) in _q.items()}
        for ft in as_completed(fts):
            _fetched[fts[ft]] = ft.result()

    enc    = _fetched.get("encounter")
    inicio = enc.get("period", {}).get("start", ahora) if enc else ahora

    cond_ids  = [r.get("id") for r in _entradas(_fetched.get("conditions"))  if r.get("id")]
    med_ids   = [r.get("id") for r in _entradas(_fetched.get("medications")) if r.get("id")]
    treat_ids = [r.get("id") for r in _entradas(_fetched.get("treatments"))  if r.get("id")]

    # Alergias: filtrar por extensión de encuentro
    aler_ids = [
        a.get("id") for a in _entradas(_fetched.get("allergies"))
        if a.get("id") and any(
            ext.get("url","").endswith("encounter-reference") and
            ext.get("valueReference",{}).get("reference") == enc_ref_str
            for ext in a.get("extension", [])
        )
    ]

    # Observaciones del encuentro: separar notas de signos vitales manuales
    LOINC_NOTA = "34109-9"
    obs_enc_all = _entradas(_fetched.get("obs_enc"))
    nota_ids = [o.get("id") for o in obs_enc_all if o.get("valueString") and o.get("id")]

    # Observaciones PHANTOM: del paciente en el periodo, sin encounter ref y sin ser notas
    inicio_dt = _parse_iso(inicio)
    ahora_dt  = _parse_iso(ahora)

    obs_phantom_ids = [
        o.get("id") for o in _entradas(_fetched.get("obs_phantom"))
        if o.get("id")
        and not o.get("valueString")
        and not any(c.get("code") == LOINC_NOTA
                    for c in o.get("code", {}).get("coding", []))
        and o.get("encounter", {}).get("reference") != enc_ref_str
        and _parse_iso(o.get("effectiveDateTime")) is not None
        and inicio_dt is not None
        and inicio_dt <= _parse_iso(o.get("effectiveDateTime")) <= ahora_dt
    ]

    # ── 2. Cerrar Encounter ───────────────────────────────
    if enc:
        enc["status"] = "finished"
        enc.setdefault("period", {})["end"] = ahora
        _put(f"{BASE_URL}/Encounter/{encounter_id}", enc)

    # ── 3. Composition ────────────────────────────────────
    sections = []
    if cond_ids:        sections.append({"title":"Condiciones médicas",    "entry":[{"reference":f"Condition/{i}"}          for i in cond_ids]})
    if med_ids:         sections.append({"title":"Medicamentos",            "entry":[{"reference":f"MedicationRequest/{i}"}  for i in med_ids]})
    if aler_ids:        sections.append({"title":"Alergias",                "entry":[{"reference":f"AllergyIntolerance/{i}"} for i in aler_ids]})
    if treat_ids:       sections.append({"title":"Tratamientos",            "entry":[{"reference":f"CarePlan/{i}"}           for i in treat_ids]})
    if obs_phantom_ids: sections.append({"title":"Observaciones PHANTOM",   "entry":[{"reference":f"Observation/{i}"}        for i in obs_phantom_ids]})
    if nota_ids:        sections.append({"title":"Notas clínicas",          "entry":[{"reference":f"Observation/{i}"}        for i in nota_ids]})

    comp_resp = _post("Composition", {
        "resourceType": "Composition", "status": "final",
        "type":    {"coding":[{"system":"http://loinc.org","code":"34133-9","display":"Summarization of episode note"}],"text":"Resumen de atención"},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter":{"reference": f"Encounter/{encounter_id}"},
        "date":    ahora, "author": [{"display": estudiante}],
        "title":   "Resumen de Atención Clínica PHANTOM-UV",
        "section": sections,
    })
    comp_id = comp_resp["id"] if comp_resp else None

    # ── 4. Bundle document (snapshot inmutable) ───────────
    entries = []
    if comp_resp:
        entries.append({"fullUrl": f"{BASE_URL}/Composition/{comp_id}",   "resource": comp_resp})
        
    # ── Fetch paralelo de todos los recursos para el Bundle ───
    bundle_tasks = {
        "_enc":     f"{BASE_URL}/Encounter/{encounter_id}",
        "_patient": f"{BASE_URL}/Patient/{patient_id}",
    }
    ordered_pairs = []
    for rt, ids in [("Condition",        cond_ids),
                    ("MedicationRequest", med_ids),
                    ("AllergyIntolerance",aler_ids),
                    ("CarePlan",          treat_ids),
                    ("Observation",       obs_phantom_ids + nota_ids)]:
        for rid in ids:
            key = f"{rt}/{rid}"
            bundle_tasks[key] = f"{BASE_URL}/{key}"
            ordered_pairs.append((rt, rid, key))

    bundle_fetched = {}
    with ThreadPoolExecutor(max_workers=min(len(bundle_tasks), 12)) as ex:
        fts = {ex.submit(_get, url): key for key, url in bundle_tasks.items()}
        for ft in as_completed(fts):
            bundle_fetched[fts[ft]] = ft.result()

    # Enc y Patient primero, luego recursos clínicos en orden original
    enc_full  = bundle_fetched.get("_enc")
    patient_r = bundle_fetched.get("_patient")

    if enc_full:
        entries.append({"fullUrl": f"{BASE_URL}/Encounter/{encounter_id}",
                        "resource": enc_full})
    if patient_r:
        entries.append({"fullUrl": f"{BASE_URL}/Patient/{patient_id}",
                        "resource": patient_r})

    for rt, rid, key in ordered_pairs:
        r = bundle_fetched.get(key)
        if r:
            entries.append({"fullUrl": f"{BASE_URL}/{rt}/{rid}", "resource": r})

    bundle_resp = _post("Bundle", {
        "resourceType": "Bundle", "type": "document",
        "timestamp": ahora, "entry": entries,
    })
    bundle_id = bundle_resp["id"] if bundle_resp else None
    print(f"[FHIR] Bundle document → {'ID: '+bundle_id if bundle_id else 'FALLO'}")

    # ── 5. DocumentReference ──
    if bundle_id:
        doc_ref = {
            "resourceType": "DocumentReference",
            "status": "current",
            "type": {
                "coding": [{"system":"http://loinc.org","code":"34133-9","display":"Summarization of episode note"}],
                "text": "Resumen de atención"
            },
            "subject":     {"reference": f"Patient/{patient_id}"},
            "date":        ahora,
            "author":      [{"display": estudiante}],
            "description": f"Atención PHANTOM-UV — {estudiante}",
            "context": {
                "encounter": [{"reference": f"Encounter/{encounter_id}"}],
                "period":    {"start": inicio, "end": ahora},
            },
            "content": [{
                "attachment": {
                    "contentType": "application/fhir+json",
                    "url":   f"{BASE_URL}/Bundle/{bundle_id}",
                    "title": "Resumen de Atención Clínica PHANTOM-UV",
                }
            }],
        }
        docref_resp = _post("DocumentReference", doc_ref)
        print(f"[FHIR] DocumentReference → {'ID: '+docref_resp['id'] if docref_resp else 'FALLO'}")

    return {"encounter_id": encounter_id, "composition_id": comp_id,
            "bundle_id": bundle_id, "fin": ahora}

def listar_atenciones_paciente(patient_id):
    """Lista atenciones del paciente consultando DocumentReference en FHIR."""
    bundle = _get(f"{BASE_URL}/DocumentReference", params={
        "patient": patient_id,
        "_sort":   "-date",
        "_count":  200,
    })
    atenciones = []
    for r in _entradas(bundle):
        # bundle_id desde content[0].attachment.url
        content   = r.get("content", [{}])
        url       = content[0].get("attachment", {}).get("url", "") if content else ""
        bundle_id = url.split("/Bundle/")[-1] if "/Bundle/" in url else None

        # encounter_id desde context.encounter
        context   = r.get("context", {})
        enc_refs  = context.get("encounter", [{}])
        enc_str   = enc_refs[0].get("reference", "") if enc_refs else ""
        enc_id    = enc_str.split("/")[-1] if "/" in enc_str else enc_str

        period    = context.get("period", {})
        author    = r.get("author", [{}])

        atenciones.append({
            "docref_id":    r.get("id"),
            "encounter_id": enc_id,
            "bundle_id":    bundle_id,
            "estudiante":   author[0].get("display", "") if author else "",
            "inicio":       period.get("start", ""),
            "fin":          period.get("end", ""),
        })
    return atenciones

def _procesar_recurso_detalle(r):
    """Convierte un recurso FHIR a formato de display en español para detalle_atencion."""
    rt = r.get("resourceType", "")

    if rt == "Condition":
        cod_cert = _cod(r.get("verificationStatus", {}))
        cod_est  = _cod(r.get("clinicalStatus", {}))
        return [{"tipo":        "condition",
                 "diagnostico": _coding_display(r.get("code", {})) or "(sin nombre)",
                 "certeza":     _CERT_ES.get(cod_cert,  _coding_display(r.get("verificationStatus", {}))) or "(no disponible)",
                 "estado":      _EST_C_ES.get(cod_est,  _coding_display(r.get("clinicalStatus", {})))    or "(no disponible)",
                 "fecha":       r.get("recordedDate", "")}]

    elif rt == "MedicationRequest":
        dosages = r.get("dosageInstruction", [])
        dosis = via = ""
        if dosages:
            d  = dosages[0]
            dr = d.get("doseAndRate", [])
            if dr:
                dq    = dr[0].get("doseQuantity", {})
                dosis = f"{dq.get('value','')} {dq.get('unit','')}".strip()
            via = _coding_display(d.get("route", {})) or d.get("text", "")
        cod_est = r.get("status", "")
        return [{"tipo":    "medication",
                 "nombre":  _coding_display(r.get("medicationCodeableConcept", {})) or "(sin nombre)",
                 "dosis":   dosis,
                 "via":     via,
                 "estado":  _EST_M_ES.get(cod_est, cod_est) or "(no disponible)",
                 "fecha":   r.get("authoredOn", "")}]

    elif rt == "AllergyIntolerance":
        manif = "—"
        reacs = r.get("reaction", [])
        if reacs:
            manifs = reacs[0].get("manifestation", [])
            if manifs:
                manif = manifs[0].get("text") or _coding_display(manifs[0]) or manif
        return [{"tipo":       "allergy",
                 "sustancia":  _coding_display(r.get("code", {})) or "(sin nombre)",
                 "manif":      manif,
                 "criticidad": _CRIT_ES.get(r.get("criticality", ""), r.get("criticality", "(no disponible)")),
                 "tipo_al":    _TIPO_ES.get(r.get("type", ""),         r.get("type",        "(no disponible)"))}]

    elif rt == "CarePlan":
        cats    = r.get("category", [])
        cod_est = r.get("status", "")
        return [{"tipo":     "treatment",
                 "nombre":   r.get("title", "(sin nombre)"),
                 "tipo_tr":  cats[0].get("text", "") if cats else "",
                 "estado":   _EST_T_ES.get(cod_est, cod_est) or "(no disponible)",
                 "inicio":   r.get("period", {}).get("start", "")}]

    elif rt == "Observation":
        if r.get("valueString"):
            return [{"tipo":  "nota",
                     "texto": r.get("valueString", ""),
                     "fecha": _fecha_corta(r.get("effectiveDateTime", ""))}]
        elif "valueQuantity" in r:
            vq = r["valueQuantity"]
            return [{"tipo":   "obs",
                     "nombre": _coding_display(r.get("code", {})) or "(sin nombre)",
                     "valor":  f"{vq.get('value','')} {vq.get('unit','')}".strip(),
                     "fecha":  _fecha_corta(r.get("effectiveDateTime", ""))}]
        elif "component" in r:
            partes = []
            for c in r.get("component", []):
                ct = _coding_display(c.get("code", {})) or ""
                vq = c.get("valueQuantity", {})
                partes.append(f"{ct}: {vq.get('value','')} {vq.get('unit','')}")
            return [{"tipo":   "obs",
                     "nombre": _coding_display(r.get("code", {})) or "(sin nombre)",
                     "valor":  " | ".join(partes),
                     "fecha":  _fecha_corta(r.get("effectiveDateTime", ""))}]
    return []

def _obs_to_dashboard(obs_raw):
    """Convierte una lista de recursos Observation a formato obs_dashboard."""
    from datetime import datetime as _dt
    LOINC_NOTA = "34109-9"
    obs_por_tipo = {}

    for o in obs_raw:
        codings = o.get("code",{}).get("coding",[])
        if any(c.get("code") == LOINC_NOTA for c in codings): continue
        if o.get("valueString"): continue

        tipo  = _coding_display(o.get("code",{})) or "(sin nombre)"
        fecha = o.get("effectiveDateTime") or o.get("issued","")
        
        dt_obj      = _dt.fromisoformat(fecha.replace("Z","+00:00"))
        fecha_corta = _fecha_corta(fecha)
        

        es_presion = False
        valor = valor2 = None
        unidad = ""

        if "valueQuantity" in o:
            vq = o["valueQuantity"]; valor = vq.get("value"); unidad = vq.get("unit") or vq.get("code","")
        elif "component" in o:
            es_presion = True
            for comp in o["component"]:
                ct  = _coding_display(comp.get("code",{})) or ""
                vq  = comp.get("valueQuantity",{})
                val = vq.get("value"); uni = vq.get("unit","mmHg"); unidad = uni
                ct_low = ct.lower()
                if any(s in ct_low for s in ["systol","sistól","sistol"]): valor  = val
                elif any(s in ct_low for s in ["diastol","diastól"]):      valor2 = val

        if tipo not in obs_por_tipo:
            obs_por_tipo[tipo] = {"entradas":[], "unidad":unidad, "es_presion":es_presion}
        obs_por_tipo[tipo]["entradas"].append({
            "fhir_id": o.get("id"), "fecha": fecha,
            "fecha_corta": fecha_corta, "valor": valor, "valor2": valor2,
        })

    obs_dashboard = {}
    for tipo, data in obs_por_tipo.items():
        entradas = sorted(data["entradas"], key=lambda x: x.get("fecha",""))
        vals  = [e["valor"]  for e in entradas if e["valor"]  is not None]
        vals2 = [e["valor2"] for e in entradas if e.get("valor2") is not None]
        def _s(lst):
            if not lst: return None,None,None
            return round(min(lst),1), round(max(lst),1), round(sum(lst)/len(lst),1)
        mn,mx,av    = _s(vals)
        mn2,mx2,av2 = _s(vals2)
        obs_dashboard[tipo] = {
            "entradas":entradas,"unidad":data["unidad"],"es_presion":data["es_presion"],
            "total":len(entradas),
            "ultimo":vals[-1]  if vals  else None,
            "ultimo2":vals2[-1] if vals2 else None,
            "minimo":mn,"maximo":mx,"promedio":av,
            "minimo2":mn2,"maximo2":mx2,"promedio2":av2,
        }
    return obs_dashboard

def obtener_detalle_atencion(bundle_id=None, composition_id=None):
    """Lee el detalle desde el Bundle (inmutable) o Composition (fallback)."""
    if bundle_id:
        bundle = _get(f"{BASE_URL}/Bundle/{bundle_id}")
        if bundle and bundle.get("type") == "document":
            # Construir índice de recursos del Bundle
            index = {}
            for e in bundle.get("entry",[]):
                r = e.get("resource",{})
                if r.get("id"):
                    index[f"{r['resourceType']}/{r['id']}"] = r

            comp = next((r for r in index.values() if r.get("resourceType")=="Composition"), None)
            enc  = next((r for r in index.values() if r.get("resourceType")=="Encounter"),   None)
            if not comp: return None

            detalle = {
                "fecha":      comp.get("date","")[:16].replace("T"," "),
                "estudiante": comp.get("author",[{}])[0].get("display","") if comp.get("author") else "",
                "titulo":     comp.get("title",""),
                "inicio":     enc.get("period",{}).get("start","")[:16].replace("T"," ") if enc else "—",
                "fin":        enc.get("period",{}).get("end","")[:16].replace("T"," ")   if enc else "—",
                "sections":   {},
            }
            phantom_resources = []

            for section in comp.get("section",[]):
                titulo = section.get("title","")
                items  = []
                for entry_ref in section.get("entry",[]):
                    r = index.get(entry_ref.get("reference",""))
                    if not r: continue
                    if titulo == "Observaciones PHANTOM":
                        phantom_resources.append(r)   # acumular para dashboard
                    else:
                        items.extend(_procesar_recurso_detalle(r))
                if titulo != "Observaciones PHANTOM" and items:
                    detalle["sections"][titulo] = items

            if phantom_resources:
                detalle["obs_phantom_dashboard"] = _obs_to_dashboard(phantom_resources)
            return detalle

    # Fallback: leer desde Composition (recursos en vivo — pueden haber cambiado)
    if not composition_id: return None
    comp = _get(f"{BASE_URL}/Composition/{composition_id}")
    if not comp: return None
    enc_ref = comp.get("encounter",{}).get("reference","")
    enc     = _get(f"{BASE_URL}/{enc_ref}") if enc_ref else None
    detalle = {
        "fecha":      comp.get("date","")[:16].replace("T"," "),
        "estudiante": comp.get("author",[{}])[0].get("display","") if comp.get("author") else "",
        "titulo":     comp.get("title",""),
        "inicio":     enc.get("period",{}).get("start","")[:16].replace("T"," ") if enc else "—",
        "fin":        enc.get("period",{}).get("end","")[:16].replace("T"," ")   if enc else "—",
        "sections":   {},
    }
    phantom_resources = []

    for section in comp.get("section",[]):
        titulo = section.get("title","")
        items  = []
        for entry_ref in section.get("entry",[]):
            ref = entry_ref.get("reference","")
            r   = _get(f"{BASE_URL}/{ref}")
            if not r: continue
            if titulo == "Observaciones PHANTOM":
                phantom_resources.append(r)
            else:
                items.extend(_procesar_recurso_detalle(r))
        if titulo != "Observaciones PHANTOM" and items:
            detalle["sections"][titulo] = items

    if phantom_resources:
        detalle["obs_phantom_dashboard"] = _obs_to_dashboard(phantom_resources)
    return detalle


def construir_recurso_atencion(patient_id, encounter_id, tipo, form_data):
    """Construye el dict FHIR SIN postear al servidor. Retorna (fhir_dict, display_dict)."""
    ref     = {"reference": f"Patient/{patient_id}"}
    enc_ref = {"reference": f"Encounter/{encounter_id}"}
    fhir = display = None

    if tipo == "condition":
        diag = form_data.get("diag","").strip()
        if not diag: return None, None
        certeza = form_data.get("certeza","Confirmado")
        estado  = form_data.get("estado","Activa")
        fecha   = form_data.get("fecha","")
        _sno  = DIAGNOSTICOS.get(diag)
        _code = {"coding":[{"system":"http://snomed.info/sct","code":_sno["code"],"display":_sno["display"]}],"text":diag} if _sno else {"text":diag}
        fhir = {"resourceType":"Condition","subject":ref,"encounter":enc_ref,"code":_code,
                "verificationStatus":construir_verification_status(certeza),
                "clinicalStatus":construir_clinical_status(estado,"condicion")}
        if fecha: fhir["recordedDate"] = fecha
        display = {"diagnostico":diag,"certeza":certeza,"estado":estado,"fecha":fecha}

    elif tipo == "allergy":
        sust = form_data.get("sustancia","").strip()
        if not sust: return None, None
        manif  = form_data.get("manifestacion","")
        crit   = form_data.get("criticidad","Baja")
        tipo_a = form_data.get("tipo_alergia","Alergia")
        estado = form_data.get("estado","Activa")
        # Auto-setear fecha si no viene del formulario para poder filtrar después
        fecha  = form_data.get("fecha","") or _ahora_chile()
        _ss = SUSTANCIAS_ALERGIAS.get(sust)
        _cs = {"coding":[{"system":"http://snomed.info/sct","code":_ss["code"],"display":_ss["display"]}],"text":sust} if _ss else {"text":sust}
        fhir = {
            "resourceType": "AllergyIntolerance",
            "patient":      ref,
            "code":         _cs,
            "type":         TIPO_ALERGIA.get(tipo_a,"allergy"),
            "criticality":  CRITICIDAD_ALERGIA.get(crit,"low"),
            "clinicalStatus": construir_clinical_status(estado,"alergia"),
            "recordedDate": fecha,
            # Extensión propia para poder filtrar alergias por encuentro después
            "extension": [{
                "url": "https://phantom.uv.cl/fhir/StructureDefinition/encounter-reference",
                "valueReference": {"reference": f"Encounter/{encounter_id}"}
            }],
        }
        if manif:
            _sm = MANIFESTACIONES_ALERGICAS.get(manif)
            _me = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":_sm["display"]}],"text":manif} if _sm else {"text":manif}
            fhir["reaction"] = [{"manifestation":[_me]}]
        display = {"sustancia":sust,"criticidad":crit,"manifestacion":manif}

    elif tipo == "medication":
        nombre = form_data.get("nombre","").strip()
        if not nombre: return None, None
        dv  = form_data.get("dosis_val",""); du  = form_data.get("dosis_unit","mg")
        per = form_data.get("periodo","8");  pu  = form_data.get("periodo_unit","h")
        via = form_data.get("via","Oral");   est = form_data.get("estado","Activo")
        fecha = form_data.get("fecha","")
        _sm = MEDICAMENTOS_CLINICOS.get(nombre)
        _cm = {"coding":[{"system":"http://snomed.info/sct","code":_sm["code"],"display":nombre}],"text":nombre} if _sm else {"text":nombre}
        dosage = {"text":f"{dv}{du} c/{per}{pu}","route":construir_via_administracion(via)}
        try: dosage["timing"]      = {"repeat":{"frequency":1,"period":float(per),"periodUnit":pu}}
        except: pass
        try: dosage["doseAndRate"] = [{"doseQuantity":{"value":float(dv),"unit":du,"system":"http://unitsofmeasure.org","code":du}}]
        except: pass
        fhir = {"resourceType":"MedicationRequest","subject":ref,"encounter":enc_ref,
                "status":ESTADO_MEDICAMENTO.get(est,"active"),"intent":"order",
                "medicationCodeableConcept":_cm,"dosageInstruction":[dosage]}
        if fecha: fhir["authoredOn"] = fecha
        display = {"nombre":nombre,"dosis":f"{dv} {du}".strip(),"via":via,"estado":est}

    elif tipo == "treatment":
        nom    = form_data.get("nombre", "").strip()
        if not nom: return None, None
        tipo_t = form_data.get("tipo_tratamiento", "Otro")
        estado = form_data.get("estado", "Activo")
        inicio = form_data.get("inicio", "")
        fin    = form_data.get("fin",    "")
        periodo = {}
        if inicio: periodo["start"] = inicio
        if fin:    periodo["end"]   = fin

        _tipo_data  = TIPO_TRATAMIENTO.get(tipo_t)
        _cat        = {
            "coding": [{"system": "http://snomed.info/sct",
                        "code":    _tipo_data["code"],
                        "display": _tipo_data["display"]}],
            "text": tipo_t
        } if _tipo_data else {"text": tipo_t}

        _plan_status = ESTADO_TRATAMIENTO.get(estado, "active")
        fhir = {
            "resourceType": "CarePlan", "subject": ref, "encounter": enc_ref,
            "status":       _plan_status, "intent": "plan",
            "title":        nom, "category": [_cat],
        }
        if periodo: fhir["period"] = periodo

        _trat_data = TRATAMIENTOS_CLINICOS.get(nom)
        if _trat_data:
            _act_status = {
                "active":          "in-progress",
                "on-hold":         "on-hold",
                "completed":       "completed",
                "revoked":         "cancelled",
                "draft":           "not-started",
                "entered-in-error":"entered-in-error",
            }.get(_plan_status, "unknown")
            fhir["activity"] = [{
                "detail": {
                    "code": {
                        "coding": [{"system": "http://snomed.info/sct",
                                    "code":    _trat_data["code"],
                                    "display": _trat_data["display"]}],
                        "text": nom
                    },
                    "status": _act_status,
                }
            }]

        display = {"nombre": nom, "tipo": tipo_t, "estado": estado}

    elif tipo == "nota":
        texto = form_data.get("texto","").strip()
        if not texto: return None, None
        from datetime import datetime as _dt, timezone
        ahora = _ahora_chile()
        fhir = {"resourceType":"Observation","status":"final",
                "category":[{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"exam"}]}],
                "code":{"coding":[{"system":"http://loinc.org","code":"34109-9","display":"Note"}],"text":"Nota clínica"},
                "subject":ref,"encounter":enc_ref,"effectiveDateTime":ahora,"valueString":texto}
        display = {"texto":texto}

    return fhir, display

def registrar_recurso_atencion_fhir(tipo, fhir_resource):
    """POST inmediato de un recurso de atención al servidor FHIR."""
    tipo_map = {
        "condition":  "Condition",
        "allergy":    "AllergyIntolerance",
        "medication": "MedicationRequest",
        "treatment":  "CarePlan",
        "nota":       "Observation",
    }
    rt = tipo_map.get(tipo)
    if not rt or not fhir_resource:
        return None
    return _post(rt, fhir_resource)

def obtener_recursos_atencion(patient_id, encounter_id, inicio):
    """Trae en paralelo los recursos ya registrados en FHIR para este encuentro."""
    enc_ref_str = f"Encounter/{encounter_id}"

    # Las alergias no tienen search param ?encounter en FHIR R4 estándar,
    # se filtran client-side por la extensión que agregamos al crearlas.
    _q = {
        "conditions":    (f"{BASE_URL}/Condition",         {"encounter": encounter_id, "_count": 200}),
        "medications":   (f"{BASE_URL}/MedicationRequest",  {"encounter": encounter_id, "_count": 200}),
        "treatments":    (f"{BASE_URL}/CarePlan",           {"encounter": encounter_id, "_count": 200}),
        "obs_enc":       (f"{BASE_URL}/Observation",        {"encounter": encounter_id, "_count": 200}),
        "allergies_all": (f"{BASE_URL}/AllergyIntolerance", {"patient": patient_id,    "_count": 200}),
    }
    _res = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        fts = {ex.submit(_get, url, params): key for key, (url, params) in _q.items()}
        for ft in as_completed(fts):
            _res[fts[ft]] = ft.result()

    # Condiciones
    conditions = []
    for c in _entradas(_res.get("conditions")):
        conditions.append({
            "diagnostico": _coding_display(c.get("code", {})) or "(sin nombre)",
            "estado":      _EST_C_ES.get(_cod(c.get("clinicalStatus", {})), "Activa"),
        })

    # Alergias — filtro por extensión de encuentro
    allergies = []
    for a in _entradas(_res.get("allergies_all")):
        tiene_enc = any(
            ext.get("url","").endswith("encounter-reference") and
            ext.get("valueReference",{}).get("reference") == enc_ref_str
            for ext in a.get("extension", [])
        )
        if tiene_enc:
            allergies.append({
                "sustancia":  _coding_display(a.get("code", {})) or "(sin nombre)",
                "criticidad": _CRIT_ES.get(a.get("criticality",""), "Baja"),
            })

    # Medicamentos
    medications = []
    for m in _entradas(_res.get("medications")):
        dosis = ""
        dosages = m.get("dosageInstruction", [])
        if dosages:
            dr = dosages[0].get("doseAndRate", [])
            if dr:
                dq = dr[0].get("doseQuantity", {})
                dosis = f"{dq.get('value','')} {dq.get('unit','')}".strip()
        medications.append({
            "nombre": _coding_display(m.get("medicationCodeableConcept",{})) or "(sin nombre)",
            "dosis":  dosis,
        })

    # Tratamientos
    treatments = []
    for t in _entradas(_res.get("treatments")):
        treatments.append({
            "nombre": t.get("title","(sin nombre)"),
            "estado": _EST_T_ES.get(t.get("status",""), ""),
        })

    # Notas (Observations con valueString)
    notas = []
    for o in _entradas(_res.get("obs_enc")):
        if o.get("valueString"):
            notas.append({"texto": o["valueString"]})

    return {
        "conditions":  conditions,
        "allergies":   allergies,
        "medications": medications,
        "treatments":  treatments,
        "notas":       notas,
    }

    return fhir, display
