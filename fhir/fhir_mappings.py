"""
Tablas de mapeo entre los valores que ingresa el usuario
y los códigos/sistemas FHIR que necesita el servidor.


"""


# ══════════════════════════════════════════════════════════════
# 1. DATOS PERSONALES — Patient
# ══════════════════════════════════════════════════════════════

# ── Sexo biológico ────────────────────────────────────────────
# Fuente: https://hl7chile.cl/fhir/ig/clcore/CodeSystem/CSSexoListadoDeis
# Extensión: https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/SexoBiologico

SEXO_BIOLOGICO = {
    "Hombre":      {"code": "1",  "display": "Hombre"},
    "Mujer":       {"code": "2",  "display": "Mujer"},
    "Intersexual": {"code": "3",  "display": "Intersexual"},
    "No Informado":{"code": "93", "display": "No Informado"},
    "Desconocido": {"code": "99", "display": "Desconocido"},
}
SEXO_BIOLOGICO_SYSTEM = "https://hl7chile.cl/fhir/ig/clcore/CodeSystem/CSSexoListadoDeis"
SEXO_BIOLOGICO_URL    = "https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/SexoBiologico"

# Mapeo al campo gender estándar de FHIR R4 (campo obligatorio)
SEXO_A_GENDER_FHIR = {
    "Hombre":      "male",
    "Mujer":       "female",
    "Intersexual": "other",
    "No Informado":"unknown",
    "Desconocido": "unknown",
}


# ── Identidad de género ───────────────────────────────────────
# Fuente: https://hl7chile.cl/fhir/ig/clcore/CodeSystem/CSIdentidaddeGenero
# Extensión: https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/IdentidadDeGenero

IDENTIDAD_GENERO = {
    "Masculino":            {"code": "1", "display": "Masculino"},
    "Femenina":             {"code": "2", "display": "Femenina"},
    "Transgénero Masculino":{"code": "3", "display": "Transgénero Masculino"},
    "Transgénero Femenina": {"code": "4", "display": "Transgénero Femenina"},
    "No binarie":           {"code": "5", "display": "No binarie"},
    "Otra":                 {"code": "6", "display": "Otra"},
    "No Revelado":          {"code": "7", "display": "No Revelado"},
}
IDENTIDAD_GENERO_SYSTEM = "https://hl7chile.cl/fhir/ig/clcore/CodeSystem/CSIdentidaddeGenero"
IDENTIDAD_GENERO_URL    = "https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/IdentidadDeGenero"


# ── Nacionalidad ──────────────────────────────────────────────
# Fuente: ISO 3166-1 numérico
# Extensión: https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/CodigoPaises
# Solo países más frecuentes en Chile — agregar según necesidad

NACIONALIDAD = {
    "Chile":          {"code": "152", "display": "Chile"},
    "Argentina":      {"code": "032", "display": "Argentina"},
    "Bolivia":        {"code": "068", "display": "Bolivia"},
    "Brasil":         {"code": "076", "display": "Brasil"},
    "Colombia":       {"code": "170", "display": "Colombia"},
    "Cuba":           {"code": "192", "display": "Cuba"},
    "Ecuador":        {"code": "218", "display": "Ecuador"},
    "España":         {"code": "724", "display": "España"},
    "Estados Unidos": {"code": "840", "display": "Estados Unidos"},
    "Haití":          {"code": "332", "display": "Haití"},
    "México":         {"code": "484", "display": "México"},
    "Panamá":         {"code": "591", "display": "Panamá"},
    "Paraguay":       {"code": "600", "display": "Paraguay"},
    "Perú":           {"code": "604", "display": "Perú"},
    "República Dominicana": {"code": "214", "display": "República Dominicana"},
    "Uruguay":        {"code": "858", "display": "Uruguay"},
    "Venezuela":      {"code": "862", "display": "Venezuela"},
    "China":          {"code": "156", "display": "China"},
    "Corea del Sur":  {"code": "410", "display": "Corea del Sur"},
    "Filipinas":      {"code": "608", "display": "Filipinas"},
    "Otra":           {"code": "999", "display": "Otra"},
}
NACIONALIDAD_SYSTEM = "urn:iso:std:iso:3166"
NACIONALIDAD_URL    = "https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/CodigoPaises"

# Sistema y código del RUT (Registro Civil)
RUT_SYSTEM     = "http://regcivil.cl/Validacion/RUN"
RUT_TYPE_CODE  = "NNCHL"
RUT_TYPE_SYSTEM= "https://hl7chile.cl/fhir/ig/clcore/CodeSystem/CSCodigoDNI"


# ══════════════════════════════════════════════════════════════
# 2. CONDICIONES MÉDICAS — Condition
# ══════════════════════════════════════════════════════════════

# ── Estado de certeza (verificationStatus) ────────────────────
CERTEZA_CONDICION = {
    "Confirmado":    {"code": "confirmed",        "display": "Confirmed"},
    "Presuntivo":    {"code": "provisional",       "display": "Provisional"},
    "Diferencial":   {"code": "differential",      "display": "Differential"},
    "Sin confirmar": {"code": "unconfirmed",       "display": "Unconfirmed"},
    "Descartado":    {"code": "refuted",           "display": "Refuted"},
    "Error":         {"code": "entered-in-error",  "display": "Entered in Error"},
}
CERTEZA_SYSTEM = "http://terminology.hl7.org/CodeSystem/condition-ver-status"

# ── Estado de la condición (clinicalStatus) ───────────────────
ESTADO_CONDICION = {
    "Activa":        {"code": "active",      "display": "Active"},
    "Resuelta":      {"code": "resolved",    "display": "Resolved"},
    "En remisión":   {"code": "remission",   "display": "Remission"},
    "Recurrente":    {"code": "recurrence",  "display": "Recurrence"},
    "Recaída":       {"code": "relapse",     "display": "Relapse"},
    "Inactiva":      {"code": "inactive",    "display": "Inactive"},
}
ESTADO_CONDICION_SYSTEM = "http://terminology.hl7.org/CodeSystem/condition-clinical"


# ══════════════════════════════════════════════════════════════
# 3. ALERGIAS — AllergyIntolerance
# ══════════════════════════════════════════════════════════════

# ── Criticidad ────────────────────────────────────────────────
CRITICIDAD_ALERGIA = {
    "Alta":              "high",
    "Baja":              "low",
    "Sin determinar":    "unable-to-assess",
}

# ── Tipo de evento ────────────────────────────────────────────
TIPO_ALERGIA = {
    "Alergia":      "allergy",
    "Intolerancia": "intolerance",
}

# ── Estado del evento (clinicalStatus) ───────────────────────
ESTADO_ALERGIA = {
    "Activa":   {"code": "active",   "display": "Active"},
    "Inactiva": {"code": "inactive", "display": "Inactive"},
    "Resuelta": {"code": "resolved", "display": "Resolved"},
}
ESTADO_ALERGIA_SYSTEM = "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"

# ── Severidad de la reacción (por si se usa despues)──────────────────────────────────
SEVERIDAD_REACCION = {
    "Leve":     "mild",
    "Moderada": "moderate",
    "Severa":   "severe",
}


# ══════════════════════════════════════════════════════════════
# 4. MEDICAMENTOS — MedicationRequest
# ══════════════════════════════════════════════════════════════

# ── Vía de administración ─────────────────────────────────────
# Fuente: SNOMED CT
VIA_ADMINISTRACION = {
    "Oral":            {"code": "26643006",  "display": "Oral"},
    "Intravenosa":     {"code": "47625008",  "display": "Intravenous"},
    "Intramuscular":   {"code": "78421000",  "display": "Intramuscular"},
    "Subcutánea":      {"code": "34206005",  "display": "Subcutaneous"},
    "Tópica":          {"code": "6064005",   "display": "Topical"},
    "Inhalatoria":     {"code": "18679011000036101", "display": "Inhalation"},
    "Sublingual":      {"code": "37839007",  "display": "Sublingual"},
    "Rectal":          {"code": "37161004",  "display": "Rectal"},
    "Oftálmica":       {"code": "54485002",  "display": "Ophthalmic"},
    "Ótica":           {"code": "10547007",  "display": "Otic"},
}
VIA_SYSTEM = "http://snomed.info/sct"

# ── Estado del medicamento ────────────────────────────────────
ESTADO_MEDICAMENTO = {
    "Activo":      "active",
    "Suspendido":  "on-hold",
    "Cancelado":   "cancelled",
    "Finalizado":  "completed",
    "Borrador":    "draft",
    "Error":       "entered-in-error",
}

# ── Unidades de dosis ─────────────────────────────────────────
# Fuente: UCUM (http://unitsofmeasure.org)
UNIDAD_DOSIS = {
    "mg":   {"code": "mg",   "display": "mg"},
    "g":    {"code": "g",    "display": "g"},
    "mcg":  {"code": "ug",   "display": "mcg"},
    "ml":   {"code": "mL",   "display": "mL"},
    "UI":   {"code": "[IU]", "display": "UI"},
    "mEq":  {"code": "meq",  "display": "mEq"},
}

# ── Unidades de frecuencia (periodUnit) ───────────────────────
UNIDAD_FRECUENCIA = {
    "hora":    "h",
    "horas":   "h",
    "día":     "d",
    "días":    "d",
    "semana":  "wk",
    "semanas": "wk",
    "mes":     "mo",
    "meses":   "mo",
}


# ══════════════════════════════════════════════════════════════
# 5. TRATAMIENTOS / INTERVENCIONES — CarePlan
# ══════════════════════════════════════════════════════════════

# ── Tipo de tratamiento ───────────────────────────────────────
TIPO_TRATAMIENTO = {
    "Nutricional":    {"code": "229440001", "display": "Nutritional therapy"},
    "Rehabilitación": {"code": "52052004",  "display": "Rehabilitation"},
    "Quirúrgico":     {"code": "387713003", "display": "Surgical procedure"},
    "Psicológico":    {"code": "75516001",  "display": "Psychotherapy"},
    "Kinesiológico":  {"code": "91251008",  "display": "Physical therapy procedure"},
    "Educativo":      {"code": "409073007", "display": "Education"},
    "Otro":           {"code": "74964007",  "display": "Other"},
}
TIPO_TRATAMIENTO_SYSTEM = "http://snomed.info/sct"

# ── Estado del tratamiento ────────────────────────────────────
ESTADO_TRATAMIENTO = {
    "Borrador":    "draft",
    "Activo":      "active",
    "Suspendido":  "on-hold",
    "Finalizado":  "completed",
    "Cancelado":   "revoked",
    "Error":       "entered-in-error",
}


# ══════════════════════════════════════════════════════════════
# 6. OBSERVACIONES CLÍNICAS — Observation
# ══════════════════════════════════════════════════════════════

# ── Tipo de observación (con códigos LOINC y unidad estándar) ─
# Fuente: LOINC (http://loinc.org)
TIPO_OBSERVACION = {
    "Presión arterial": {
        "loinc":    "55284-4",
        "display":  "Blood pressure systolic and diastolic",
        "unidad":   None,          # sin unidad a nivel raíz (usa componentes)
        "tipo":     "componente",  # indica que tiene sistólica y diastólica
        "categoria":"vital-signs",
    },
    "Frecuencia cardíaca": {
        "loinc":    "8867-4",
        "display":  "Heart rate",
        "unidad":   {"value_unit": "beats/min", "ucum": "/min"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
    "Saturación de oxígeno": {
        "loinc":    "59408-5",
        "display":  "Oxygen saturation in Arterial blood by Pulse oximetry",
        "unidad":   {"value_unit": "%",         "ucum": "%"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
    "Temperatura corporal": {
        "loinc":    "8310-5",
        "display":  "Body temperature",
        "unidad":   {"value_unit": "Cel",       "ucum": "Cel"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
    "Frecuencia respiratoria": {
        "loinc":    "9279-1",
        "display":  "Respiratory rate",
        "unidad":   {"value_unit": "breaths/min","ucum": "/min"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
    "Glucosa en sangre": {
        "loinc":    "2339-0",
        "display":  "Glucose [Mass/volume] in Blood",
        "unidad":   {"value_unit": "mg/dL",     "ucum": "mg/dL"},
        "tipo":     "cantidad",
        "categoria":"laboratory",
    },
    "Peso": {
        "loinc":    "29463-7",
        "display":  "Body weight",
        "unidad":   {"value_unit": "kg",        "ucum": "kg"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
    "Talla": {
        "loinc":    "8302-2",
        "display":  "Body height",
        "unidad":   {"value_unit": "cm",        "ucum": "cm"},
        "tipo":     "cantidad",
        "categoria":"vital-signs",
    },
}

# ── Componentes de presión arterial (LOINC) ───────────────────
PRESION_ARTERIAL_COMPONENTES = {
    "sistolica": {
        "loinc":   "8480-6",
        "display": "Systolic blood pressure",
        "ucum":    "mm[Hg]",
        "unit":    "mmHg",
    },
    "diastolica": {
        "loinc":   "8462-4",
        "display": "Diastolic blood pressure",
        "ucum":    "mm[Hg]",
        "unit":    "mmHg",
    },
}

# ── Categorías de observación ─────────────────────────────────
CATEGORIA_OBSERVACION_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"
CATEGORIA_OBSERVACION = {
    "vital-signs": {"code": "vital-signs", "display": "Vital Signs"},
    "laboratory":  {"code": "laboratory",  "display": "Laboratory"},
}


# ══════════════════════════════════════════════════════════════
# FUNCIONES CONSTRUCTORAS
# Convierten el input del usuario en estructuras FHIR listas para enviar
# ══════════════════════════════════════════════════════════════

def construir_extension_sexo(sexo_usuario):
    datos = SEXO_BIOLOGICO.get(sexo_usuario)
    if not datos:
        raise ValueError(f"Sexo biológico no reconocido: '{sexo_usuario}'. "
                         f"Opciones: {list(SEXO_BIOLOGICO.keys())}")
    return {
        "url": SEXO_BIOLOGICO_URL,
        "valueCodeableConcept": {
            "coding": [{
                "system":  SEXO_BIOLOGICO_SYSTEM,
                "code":    datos["code"],
                "display": datos["display"],
            }]
        }
    }


def construir_extension_genero(genero_usuario):
    datos = IDENTIDAD_GENERO.get(genero_usuario)
    if not datos:
        raise ValueError(f"Identidad de género no reconocida: '{genero_usuario}'. "
                         f"Opciones: {list(IDENTIDAD_GENERO.keys())}")
    return {
        "url": IDENTIDAD_GENERO_URL,
        "valueCodeableConcept": {
            "coding": [{
                "system":  IDENTIDAD_GENERO_SYSTEM,
                "code":    datos["code"],
                "display": datos["display"],
            }]
        }
    }


def construir_extension_nacionalidad(pais_usuario):
    datos = NACIONALIDAD.get(pais_usuario)
    if not datos:
        raise ValueError(f"Nacionalidad no reconocida: '{pais_usuario}'. "
                         f"Opciones: {list(NACIONALIDAD.keys())}")
    return {
        "url": NACIONALIDAD_URL,
        "valueCodeableConcept": {
            "coding": [{
                "system":  NACIONALIDAD_SYSTEM,
                "code":    datos["code"],
                "display": datos["display"],
            }],
            "text": pais_usuario
        }
    }


def construir_identifier_rut(rut_usuario):
    return {
        "use": "official",
        "type": {
            "extension": [
                construir_extension_nacionalidad("Chile")
            ],
            "coding": [{
                "system":  RUT_TYPE_SYSTEM,
                "code":    RUT_TYPE_CODE,
                "display": "Chile"
            }]
        },
        "system": RUT_SYSTEM,
        "value":  rut_usuario
    }


def construir_codeable(texto, codigo, sistema, display=None):
    return {
        "coding": [{
            "system":  sistema,
            "code":    codigo,
            "display": display or texto,
        }],
        "text": texto
    }


def construir_clinical_status(estado_usuario, tipo="condicion"):
    if tipo == "alergia":
        datos  = ESTADO_ALERGIA.get(estado_usuario)
        sistema= ESTADO_ALERGIA_SYSTEM
    else:
        datos  = ESTADO_CONDICION.get(estado_usuario)
        sistema= ESTADO_CONDICION_SYSTEM

    if not datos:
        raise ValueError(f"Estado '{estado_usuario}' no reconocido para tipo '{tipo}'")

    return {
        "coding": [{
            "system":  sistema,
            "code":    datos["code"],
            "display": datos["display"],
        }]
    }


def construir_verification_status(certeza_usuario):
    datos = CERTEZA_CONDICION.get(certeza_usuario)
    if not datos:
        raise ValueError(f"Certeza no reconocida: '{certeza_usuario}'")
    return {
        "coding": [{
            "system":  CERTEZA_SYSTEM,
            "code":    datos["code"],
            "display": datos["display"],
        }]
    }


def construir_via_administracion(via_usuario):
    datos = VIA_ADMINISTRACION.get(via_usuario)
    if not datos:
        raise ValueError(f"Vía no reconocida: '{via_usuario}'")
    return {
        "coding": [{
            "system":  VIA_SYSTEM,
            "code":    datos["code"],
            "display": datos["display"],
        }],
        "text": via_usuario
    }


def construir_categoria_observacion(categoria_key):
    datos = CATEGORIA_OBSERVACION.get(categoria_key, {
        "code": categoria_key, "display": categoria_key
    })
    return [{
        "coding": [{
            "system":  CATEGORIA_OBSERVACION_SYSTEM,
            "code":    datos["code"],
            "display": datos["display"],
        }]
    }]


def construir_observation(tipo_usuario, valor, subject_url, fecha_hora, valor2=None):
    config = TIPO_OBSERVACION.get(tipo_usuario)
    if not config:
        raise ValueError(f"Tipo de observación no reconocido: '{tipo_usuario}'. "
                         f"Opciones: {list(TIPO_OBSERVACION.keys())}")

    obs = {
        "resourceType": "Observation",
        "status":   "final",
        "subject":  {"reference": subject_url},
        "category": construir_categoria_observacion(config["categoria"]),
        "code": {
            "coding": [{
                "system":  "http://loinc.org",
                "code":    config["loinc"],
                "display": config["display"],
            }],
            "text": tipo_usuario
        },
        "effectiveDateTime": fecha_hora,
    }

    if config["tipo"] == "componente":
        # Presión arterial: sistólica y diastólica
        if valor2 is None:
            raise ValueError("Para Presión arterial se necesitan dos valores: sistólica y diastólica")
        comp_s = PRESION_ARTERIAL_COMPONENTES["sistolica"]
        comp_d = PRESION_ARTERIAL_COMPONENTES["diastolica"]
        obs["component"] = [
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": comp_s["loinc"], "display": comp_s["display"]}],
                    "text": "Sistólica"
                },
                "valueQuantity": {"value": float(valor), "unit": comp_s["unit"], "system": "http://unitsofmeasure.org", "code": comp_s["ucum"]}
            },
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": comp_d["loinc"], "display": comp_d["display"]}],
                    "text": "Diastólica"
                },
                "valueQuantity": {"value": float(valor2), "unit": comp_d["unit"], "system": "http://unitsofmeasure.org", "code": comp_d["ucum"]}
            }
        ]
    else:
        # Observación simple con un solo valor
        unidad = config["unidad"]
        obs["valueQuantity"] = {
            "value":  float(valor),
            "unit":   unidad["value_unit"],
            "system": "http://unitsofmeasure.org",
            "code":   unidad["ucum"],
        }

    return obs


# ══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL: construir_paciente_fhir
# Recibe los datos tal como vienen del formulario y devuelve el
# recurso Patient FHIR completo listo para enviar.
# ══════════════════════════════════════════════════════════════

def construir_paciente_fhir(datos_formulario):
    nombre           = datos_formulario["nombre"]
    apellido         = datos_formulario["apellido"]
    segundo_apellido = datos_formulario.get("segundo_apellido", "")
    rut              = datos_formulario["rut"]
    fecha_nacimiento = datos_formulario["fecha_nacimiento"]
    sexo             = datos_formulario["sexo_biologico"]
    genero           = datos_formulario["identidad_genero"]
    nacionalidad     = datos_formulario["nacionalidad"]
    estado_civil     = datos_formulario.get("estado_civil", "")
    pueblo           = datos_formulario.get("pueblo_indigena", "")
    afro_raw         = datos_formulario.get("afrodescendiente", "No")
    nivel_educ       = datos_formulario.get("nivel_educacional", "")
    ultimo_curso     = datos_formulario.get("ultimo_curso", "")
    prevision        = datos_formulario.get("prevision", "")
    telefono         = datos_formulario.get("telefono", "")

    name_entry = {
        "use":    "official",
        "family": apellido,
        "given":  nombre.split(),
        "text":   f"{nombre} {apellido} {segundo_apellido}".strip(),
    }
    if segundo_apellido:
        name_entry["_family"] = {"extension": [{
            "url": "https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/SegundoApellido",
            "valueString": segundo_apellido,
        }]}

    # Construir lista de extensiones
    exts = [
        construir_extension_sexo(sexo),
        construir_extension_genero(genero),
        construir_extension_nacionalidad(nacionalidad),
    ]
    if pueblo:
        e = construir_extension_pueblo_indigena(pueblo)
        if e: exts.append(e)

    afro_val = afro_raw in ("Sí", "sí", "si", "true", "True", "1")
    exts.append(construir_extension_afrodescendiente(afro_val))

    if nivel_educ:
        e = construir_extension_nivel_educacional(nivel_educ)
        if e: exts.append(e)
        if ultimo_curso != "":
            try:
                exts.append(construir_extension_ultimo_curso(int(ultimo_curso)))
            except (ValueError, TypeError):
                pass

    if prevision:
        e = construir_extension_prevision(prevision)
        if e: exts.append(e)

    paciente = {
        "resourceType": "Patient",
        "meta": {"profile": ["https://hl7chile.cl/fhir/ig/clcore/StructureDefinition/CorePacienteCl"]},
        "extension":  [e for e in exts if e],
        "identifier": [construir_identifier_rut(rut)],
        "name":       [name_entry],
        "gender":     SEXO_A_GENDER_FHIR.get(sexo, "unknown"),
        "birthDate":  fecha_nacimiento,
        "active":     True,
    }

    ms = construir_marital_status(estado_civil) if estado_civil else None
    if ms:
        paciente["maritalStatus"] = ms

    if telefono:
        paciente["telecom"] = [{"system": "phone", "value": telefono, "use": "mobile"}]

    return paciente

# ══════════════════════════════════════════════════════════════
# DIAGNÓSTICOS CLÍNICOS — SNOMED CT
# ══════════════════════════════════════════════════════════════
DIAGNOSTICOS = {
    "Neumonía grave":                                    {"code": "233604007", "display": "Pneumonia"},
    "Infarto agudo al miocardio":                        {"code": "57054005",  "display": "Acute myocardial infarction"},
    "Accidente cerebrovascular (ACV)":                   {"code": "230690007", "display": "Cerebrovascular accident"},
    "Insuficiencia cardíaca descompensada":              {"code": "84114007",  "display": "Heart failure"},
    "Sepsis":                                            {"code": "91302008",  "display": "Sepsis"},
    "Insuficiencia respiratoria aguda":                  {"code": "65710008",  "display": "Acute respiratory failure"},
    "Diabetes mellitus descompensada":                   {"code": "44054006",  "display": "Type 2 diabetes mellitus"},
    "Cetoacidosis diabética":                            {"code": "34638004",  "display": "Diabetic ketoacidosis"},
    "Enfermedad renal crónica avanzada":                 {"code": "709044004", "display": "Chronic kidney disease"},
    "Apendicitis aguda":                                 {"code": "85828009",  "display": "Acute appendicitis"},
    "Pancreatitis aguda":                                {"code": "197456007", "display": "Acute pancreatitis"},
    "Trauma craneoencefálico":                           {"code": "127295002", "display": "Traumatic brain injury"},
    "Fractura de cadera":                                {"code": "57797005",  "display": "Fracture of hip"},
    "COVID-19 grave":                                    {"code": "840539006", "display": "COVID-19"},
    "Hemorragia digestiva alta":                         {"code": "37372002",  "display": "Upper gastrointestinal hemorrhage"},
    "Embolia pulmonar":                                  {"code": "59282003",  "display": "Pulmonary embolism"},
    "Shock séptico":                                     {"code": "76571007",  "display": "Septic shock"},
    "Meningitis bacteriana":                             {"code": "95883001",  "display": "Bacterial meningitis"},
    "Insuficiencia hepática aguda":                      {"code": "197270009", "display": "Acute liver failure"},
    "Síndrome de dificultad respiratoria aguda":         {"code": "67782005",  "display": "Respiratory distress syndrome"},
}

# ══════════════════════════════════════════════════════════════
# SUSTANCIAS ALERGÉNICAS — SNOMED CT
# ══════════════════════════════════════════════════════════════
SUSTANCIAS_ALERGIAS = {
    "Penicilina":        {"code": "764146007", "display": "Penicillin"},
    "Amoxicilina":       {"code": "372687004", "display": "Amoxicillin"},
    "Aspirina":          {"code": "387458008", "display": "Aspirin"},
    "Ibuprofeno":        {"code": "387207008", "display": "Ibuprofen"},
    "Ceftriaxona":       {"code": "372670001", "display": "Ceftriaxone"},
    "Vancomicina":       {"code": "372809001", "display": "Vancomycin"},
    "Metronidazol":      {"code": "372602008", "display": "Metronidazole"},
    "Morfina":           {"code": "373529000", "display": "Morphine"},
    "Codeína":           {"code": "387494007", "display": "Codeine"},
    "Sulfonamidas":      {"code": "387406002", "display": "Sulfonamide"},
    "AINEs":             {"code": "372665008", "display": "Non-steroidal anti-inflammatory agent"},
    "Contraste yodado":  {"code": "385420005", "display": "Iodinated contrast media"},
    "Látex":             {"code": "1003751004","display": "Latex"},
    "Maní / Cacahuete":  {"code": "762952008", "display": "Peanut"},
    "Mariscos":          {"code": "44027008",  "display": "Shellfish"},
    "Leche de vaca":     {"code": "3718001",   "display": "Cow milk protein"},
    "Huevo":             {"code": "102263004", "display": "Egg"},
    "Gluten / Trigo":    {"code": "412071004", "display": "Gluten"},
}

# ══════════════════════════════════════════════════════════════
# MANIFESTACIONES CLÍNICAS ALÉRGICAS — SNOMED CT
# ══════════════════════════════════════════════════════════════
MANIFESTACIONES_ALERGICAS = {
    "Urticaria":              {"code": "126485001", "display": "Urticaria"},
    "Anafilaxia":             {"code": "39579001",  "display": "Anaphylactic reaction"},
    "Angioedema":             {"code": "41291007",  "display": "Angioedema"},
    "Broncoespasmo":          {"code": "4386001",   "display": "Bronchospasm"},
    "Hipotensión":            {"code": "45007003",  "display": "Low blood pressure"},
    "Exantema / Rash":        {"code": "271807003", "display": "Skin eruption"},
    "Prurito":                {"code": "418290006", "display": "Itching"},
    "Náuseas y vómitos":      {"code": "422400008", "display": "Vomiting"},
    "Diarrea":                {"code": "62315008",  "display": "Diarrhea"},
    "Rinitis alérgica":       {"code": "70076002",  "display": "Rhinitis"},
    "Eritema":                {"code": "444827008", "display": "Erythema"},
    "Edema laríngeo":         {"code": "267036007", "display": "Edema of larynx"},
    "Conjuntivitis alérgica": {"code": "9826008",   "display": "Conjunctivitis"},
}

# ══════════════════════════════════════════════════════════════
# MEDICAMENTOS CLÍNICOS — SNOMED CT con dosis típicas
# ══════════════════════════════════════════════════════════════
MEDICAMENTOS_CLINICOS = {
    "Paracetamol":    {"code": "387517004", "dosis": 500,  "unit": "mg", "periodo": 6,  "periodo_unit": "h", "via": "Oral"},
    "Morfina":        {"code": "373529000", "dosis": 10,   "unit": "mg", "periodo": 4,  "periodo_unit": "h", "via": "Intravenosa"},
    "Tramadol":       {"code": "386858008", "dosis": 50,   "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Oral"},
    "Ibuprofeno":     {"code": "387207008", "dosis": 400,  "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Oral"},
    "Aspirina":       {"code": "387458008", "dosis": 100,  "unit": "mg", "periodo": 24, "periodo_unit": "h", "via": "Oral"},
    "Metformina":     {"code": "372567009", "dosis": 850,  "unit": "mg", "periodo": 12, "periodo_unit": "h", "via": "Oral"},
    "Insulina":       {"code": "67866001",  "dosis": 10,   "unit": "UI", "periodo": 24, "periodo_unit": "h", "via": "Subcutánea"},
    "Heparina":       {"code": "372877000", "dosis": 5000, "unit": "UI", "periodo": 8,  "periodo_unit": "h", "via": "Subcutánea"},
    "Warfarina":      {"code": "372756006", "dosis": 5,    "unit": "mg", "periodo": 24, "periodo_unit": "h", "via": "Oral"},
    "Atorvastatina":  {"code": "373444002", "dosis": 40,   "unit": "mg", "periodo": 24, "periodo_unit": "h", "via": "Oral"},
    "Omeprazol":      {"code": "372508001", "dosis": 20,   "unit": "mg", "periodo": 24, "periodo_unit": "h", "via": "Oral"},
    "Furosemida":     {"code": "387475002", "dosis": 40,   "unit": "mg", "periodo": 24, "periodo_unit": "h", "via": "Oral"},
    "Enalapril":      {"code": "372658000", "dosis": 10,   "unit": "mg", "periodo": 12, "periodo_unit": "h", "via": "Oral"},
    "Metoprolol":     {"code": "372826007", "dosis": 50,   "unit": "mg", "periodo": 12, "periodo_unit": "h", "via": "Oral"},
    "Ceftriaxona":    {"code": "372670001", "dosis": 1,    "unit": "g",  "periodo": 24, "periodo_unit": "h", "via": "Intravenosa"},
    "Vancomicina":    {"code": "372809001", "dosis": 1,    "unit": "g",  "periodo": 12, "periodo_unit": "h", "via": "Intravenosa"},
    "Amoxicilina":    {"code": "372687004", "dosis": 500,  "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Oral"},
    "Metronidazol":   {"code": "372602008", "dosis": 500,  "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Intravenosa"},
    "Salbutamol":     {"code": "372897005", "dosis": 2.5,  "unit": "mg", "periodo": 6,  "periodo_unit": "h", "via": "Inhalatoria"},
    "Dexametasona":   {"code": "372584003", "dosis": 8,    "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Intravenosa"},
    "Ondansetrón":    {"code": "372487007", "dosis": 8,    "unit": "mg", "periodo": 8,  "periodo_unit": "h", "via": "Intravenosa"},
    "Ciprofloxacino": {"code": "372840008", "dosis": 500,  "unit": "mg", "periodo": 12, "periodo_unit": "h", "via": "Oral"},
}

# ══════════════════════════════════════════════════════════════
# TRATAMIENTOS / INTERVENCIONES CLÍNICAS — SNOMED CT
# ══════════════════════════════════════════════════════════════
TRATAMIENTOS_CLINICOS = {
    "Oxigenoterapia suplementaria":    {"code": "57485005",  "display": "Oxygen therapy"},
    "Ventilación mecánica invasiva":   {"code": "40617009",  "display": "Mechanical ventilation"},
    "Hemodiálisis":                    {"code": "302497006", "display": "Hemodialysis"},
    "Diálisis peritoneal":             {"code": "71192002",  "display": "Peritoneal dialysis"},
    "Fisioterapia respiratoria":       {"code": "229070002", "display": "Physiotherapy"},
    "Rehabilitación cardíaca":         {"code": "182687005", "display": "Cardiac rehabilitation"},
    "Rehabilitación neurológica":      {"code": "52052004",  "display": "Rehabilitation"},
    "Fisioterapia musculoesquelética": {"code": "91251008",  "display": "Physical therapy procedure"},
    "Terapia nutricional":             {"code": "229440001", "display": "Nutritional therapy"},
    "Terapia ocupacional":             {"code": "229831001", "display": "Occupational therapy"},
    "Fonoaudiología":                  {"code": "3607001",   "display": "Speech therapy"},
    "Manejo del dolor":                {"code": "278414003", "display": "Pain management"},
    "Cuidado de heridas":              {"code": "225358003", "display": "Wound care"},
    "Soporte psicológico":             {"code": "75516001",  "display": "Psychotherapy"},
    "Rehabilitación post-quirúrgica":  {"code": "91251008",  "display": "Postoperative physiotherapy"},
}

#datos faltantes
# ══════════════════════════════════════════════════════════════
# DATOS EIS — Estado Civil, Pueblo Indígena, Educación, Previsión
# Fuente: DEIS-EIS Minsal
# ══════════════════════════════════════════════════════════════

ESTADO_CIVIL = {
    "Soltero":                {"code": "1",  "display": "Soltero"},
    "Casado":                 {"code": "2",  "display": "Casado"},
    "Viudo":                  {"code": "3",  "display": "Viudo"},
    "Divorciado":             {"code": "4",  "display": "Divorciado"},
    "Separado judicialmente": {"code": "5",  "display": "Separado judicialmente"},
    "Conviviente civil":      {"code": "6",  "display": "Conviviente civil"},
    "Desconocido":            {"code": "99", "display": "Desconocido"},
}
ESTADO_CIVIL_SYSTEM = "https://minsal.cl/fhir/ig/eis/CodeSystem/CSEstadoCivil"

PUEBLO_INDIGENA = {
    "Mapuche":              {"code": "1",  "display": "Mapuche"},
    "Aymara":               {"code": "2",  "display": "Aymara"},
    "Rapa Nui - Pascuense": {"code": "3",  "display": "Rapa Nui - Pascuense"},
    "Lickanantay":          {"code": "4",  "display": "Lickanantay"},
    "Quechua":              {"code": "5",  "display": "Quechua"},
    "Colla":                {"code": "6",  "display": "Colla"},
    "Diaguita":             {"code": "7",  "display": "Diaguita"},
    "Kawésqar":             {"code": "8",  "display": "Kawésqar"},
    "Yagán":                {"code": "9",  "display": "Yagán"},
    "Chango":               {"code": "10", "display": "Chango"},
    "Otro":                 {"code": "11", "display": "Otro"},
}
PUEBLO_INDIGENA_SYSTEM = "https://minsal.cl/fhir/ig/eis/CodeSystem/CSPueblosIndigenas"
PUEBLO_INDIGENA_URL    = "https://minsal.cl/fhir/ig/eis/StructureDefinition/PuebloIndigena"
AFRODESCENDIENTE_URL   = "https://minsal.cl/fhir/ig/eis/StructureDefinition/PuebloAfrodescendiente"

NIVEL_EDUCACIONAL = {
    "Preescolar":            {"code": "1",  "display": "Preescolar"},
    "Educación Diferencial": {"code": "2",  "display": "Educación Diferencial"},
    "Básica Primaria":       {"code": "3",  "display": "Básica Primaria"},
    "Media Secundaria":      {"code": "4",  "display": "Media Secundaria"},
    "Educación Superior":    {"code": "5",  "display": "Educación Superior"},
    "Sin Instrucción":       {"code": "6",  "display": "Sin Instrucción"},
    "No recuerda":           {"code": "97", "display": "No recuerda"},
    "No responde":           {"code": "98", "display": "No responde"},
}
NIVEL_EDUCACIONAL_SYSTEM = "https://minsal.cl/fhir/ig/eis/CodeSystem/CSNivelEducacional"
NIVEL_EDUCACIONAL_URL    = "https://minsal.cl/fhir/ig/eis/StructureDefinition/NivelEducacional"
ULTIMO_CURSO_URL         = "https://minsal.cl/fhir/ig/eis/StructureDefinition/UltimoCursoAprobado"

PREVISION = {
    "FONASA":      {"code": "1",  "display": "FONASA"},
    "ISAPRE":      {"code": "2",  "display": "ISAPRE"},
    "CAPREDENA":   {"code": "3",  "display": "CAPREDENA"},
    "DIPRECA":     {"code": "4",  "display": "DIPRECA"},
    "SISA":        {"code": "5",  "display": "SISA"},
    "Ninguna":     {"code": "96", "display": "Ninguna"},
    "Desconocido": {"code": "99", "display": "Desconocido"},
}
PREVISION_SYSTEM = "https://minsal.cl/fhir/ig/eis/CodeSystem/CSPrevision"
PREVISION_URL    = "https://minsal.cl/fhir/ig/eis/StructureDefinition/Prevision"


def construir_marital_status(estado_usuario):
    datos = ESTADO_CIVIL.get(estado_usuario)
    if not datos:
        return None
    return {
        "coding": [{"system": ESTADO_CIVIL_SYSTEM, "code": datos["code"], "display": datos["display"]}],
        "text": estado_usuario,
    }

def construir_extension_pueblo_indigena(pueblo_usuario):
    datos = PUEBLO_INDIGENA.get(pueblo_usuario)
    if not datos:
        return None
    return {
        "url": PUEBLO_INDIGENA_URL,
        "valueCodeableConcept": {
            "coding": [{"system": PUEBLO_INDIGENA_SYSTEM, "code": datos["code"], "display": datos["display"]}],
            "text": pueblo_usuario,
        },
    }

def construir_extension_afrodescendiente(valor_bool):
    return {"url": AFRODESCENDIENTE_URL, "valueBoolean": bool(valor_bool)}

def construir_extension_nivel_educacional(nivel_usuario):
    datos = NIVEL_EDUCACIONAL.get(nivel_usuario)
    if not datos:
        return None
    return {
        "url": NIVEL_EDUCACIONAL_URL,
        "valueCodeableConcept": {
            "coding": [{"system": NIVEL_EDUCACIONAL_SYSTEM, "code": datos["code"], "display": datos["display"]}],
            "text": nivel_usuario,
        },
    }

def construir_extension_ultimo_curso(curso_int):
    return {"url": ULTIMO_CURSO_URL, "valueInteger": int(curso_int)}

def construir_extension_prevision(prevision_usuario):
    datos = PREVISION.get(prevision_usuario)
    if not datos:
        return None
    return {
        "url": PREVISION_URL,
        "valueCodeableConcept": {
            "coding": [{"system": PREVISION_SYSTEM, "code": datos["code"], "display": datos["display"]}],
            "text": prevision_usuario,
        },
    }