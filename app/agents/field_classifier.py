# app/agents/field_classifier.py
from google.adk import Agent
from google.genai import types
from app.tools.state_utils import set_state


def make_field_classifier(settings):
    return Agent(
        name="field_classifier",
        model=settings.MODEL,
        description="Classify 'field' (rubro/industria) from employer/sector/activity_declared using a closed taxonomy.",
        instruction="""
        TASK:
          Choose EXACTLY one 'field' from the allowed taxonomy list.

        INPUT STATE:
          employer: { employer? }
          sector: { sector? }
          activity_declared: { activity_declared? }
          employer_norm: { employer_norm? }
          sector_norm: { sector_norm? }
          activity_declared_norm: { activity_declared_norm? }

          tax_fields: { tax_fields? }

        RULES (STRICT):
          - You MUST choose one value that is EXACTLY in `tax_fields`.
          - Do NOT invent new labels.
          - Heuristic:
              * If `sector_norm` matches a value in `tax_fields` and it is NOT "otros",
                then choose that as field.
              * Otherwise, infer using employer/activity_declared.

        EXAMPLES (INPUT -> OUTPUT):

        1)
        employer: "Fair Play"
        sector: "otros"
        activity_declared: "trabajo en la parte de contabilidad de comercio"
        -> field: "Comercio minorista"

        2)
        employer: "NAGA GROUP"
        sector: "servicios"
        activity_declared: "Atención al cliente"
        -> field: "Servicios comerciales"

        3)
        employer: ""
        sector: "industria"
        activity_declared: "Operario de planta"
        -> field: "Producción / manufactura"



        REGLAS EXPLÍCITAS (FIELD / RUBRO)
        0) Debes devolver EXACTAMENTE 1 etiqueta que esté en `tax_fields`. Nunca inventes etiquetas.

        1) Prioridad de señales (en este orden):
          a) activity_declared (lo que hace)
          b) employer (tipo de empresa/institución)
          c) sector (si es claro; si es “otros” o genérico, úsalo solo como apoyo)

        2) Si el texto es insuficiente o genérico ("trabajo", "empleado", "independiente" sin más), devuelve: "Indefinido".

        3) Disparadores rápidos por keywords:
          - "Sector público": alcaldía, gobernación, ministerio, entidad pública, órgano judicial, registro civil, municipalidad.
          - "Comercio minorista": tienda, retail, venta al detalle, ropa, zapatos, abarrotes, minimarket, supermercado, cajero, repositor.
          - "Distribución / mayorista": mayorista, distribuidor, por volumen, proveedor de comercios, importador, bodega mayorista.
          - "Servicios técnicos": técnico, soporte, instalación, mantenimiento, reparaciones, mecánica (servicio), soporte TI, cableado.
          - "Servicios profesionales": abogado, contador, auditor, consultor, ingeniero (servicio), agencia profesional, asesoría formal.
          - "Educación": profesor, docente, colegio, universidad, academia, tutor.
          - "Salud": médico, enfermería, farmacia, laboratorio, clínica, veterinaria.
          - "Transporte": chofer, taxi, conductor, delivery, mensajería, repartidor, transporte de carga.
          - "Producción / manufactura": fábrica, planta, operario, producción, manufactura, textil, panadería industrial, taller industrial.
          - "Administrativo / oficina": administración, backoffice, tesorería, RRHH, contabilidad interna, asistente administrativo, analista oficina.
          - "Gastronomía": restaurante, cafetería, bar, cocina, chef, mesero, catering, comida rápida.
          - "Construcción / obra": construcción, obra, albañil, contratista, maestro de obra, supervisor de obra, obra civil.
          - "Agro / ganadería": agricultura, ganadería, agropecuario, campo, finca, cosecha.
          - "Servicios personales": belleza, estética, peluquería, barbería, cuidado personal.
          - "Ocio / nocturno / eventos": eventos, entretenimiento, productora, fiestas, discoteca, nocturno, animación.
          - "Seguridad": guardia, vigilante, seguridad privada, escolta, FFAA, policía.
          - "Servicios financieros": banco, seguros, broker, financiero, crédito, cartera, asesor financiero.
          - "Estudiante": estudiante, universitario (si su actividad principal es estudiar).
          - "Servicios comerciales": asesor comercial, ejecutivo de ventas, ventas B2C/B2B, atención al cliente (cuando no es claramente retail).
          - "Publicidad, comunicacion y marketing": marketing, community manager, publicidad, campañas, comunicación, branding, redes sociales.
          - "Eventual": jornalero, temporal, por día, ocasional, “hago de todo”, ingreso esporádico.
          - "Mixto": declara dos o más trabajos NO relacionados sin uno dominante claro (ej: “taxista y músico”, “repartidor y vendedor”).

        4) Regla para casos con conflicto:
          - Si hay institución pública → "Sector público" (aunque la tarea sea técnica/administrativa).
          - Si es “policía/FFAA” → ("Seguridad").
          - Si el texto menciona explícitamente dos trabajos distintos → "Mixto" (salvo que uno sea claramente principal).

   
          

          EJEMPLOS (INPUT -> FIELD)

          1)
          employer: "Fidalga"
          sector: "otros"
          activity_declared: "Trabajo en tienda de ropa"
          -> field: "Comercio minorista"

          2)
          employer: "Distribuidora Andina"
          sector: "otros"
          activity_declared: "Soy mayorista, vendo por volumen a tiendas"
          -> field: "Distribución / mayorista"

          3)
          employer: "Industrias VENDAVAL"
          sector: "industria"
          activity_declared: "Operario de producción en planta"
          -> field: "Producción / manufactura"

          4)
          employer: "Taller Rápido"
          sector: "otros"
          activity_declared: "Técnico de mantenimiento y reparaciones"
          -> field: "Servicios técnicos"

          5)
          employer: ""
          sector: "otros"
          activity_declared: "Abogada, hago asesoría legal"
          -> field: "Servicios profesionales"

          6)
          employer: "Colegio Santa María"
          sector: "otros"
          activity_declared: "Docente de primaria"
          -> field: "Educación"

          7)
          employer: "Clínica Central"
          sector: "otros"
          activity_declared: "Enfermería"
          -> field: "Salud"

          8)
          employer: "Yango"
          sector: "otros"
          activity_declared: "Repartidor delivery"
          -> field: "Transporte"

          9)
          employer: "Restaurante El Buen Sabor"
          sector: "otros"
          activity_declared: "Cocinero"
          -> field: "Gastronomía"

          10)
          employer: "Constructora Sur"
          sector: "otros"
          activity_declared: "Albañil en obra"
          -> field: "Construcción / obra"

          11)
          employer: ""
          sector: "otros"
          activity_declared: "Taxista y músico los fines de semana"
          -> field: "Mixto"

          12)
          employer: ""
          sector: "otros"
          activity_declared: "No declara / solo dice que trabaja"
          -> field: "Indefinido"




        OUTPUT:
          Call set_state exactly once:
            set_state(key="field", value="<chosen_field>")

          Do NOT output free text.
        """,
        tools=[set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
