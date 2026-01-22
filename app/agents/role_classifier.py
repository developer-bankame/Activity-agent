# app/agents/role_classifier.py
import logging
from google.adk import Agent
from google.genai import types
from app.tools.state_utils import set_state

logger = logging.getLogger(__name__)


def make_role_classifier(settings):
    def prepare_allowed_roles(tool_context):
        """
        Tool: calcula roles permitidos a partir de:
          - field_sub_to_roles (map con key "field||sub_field")
          - field_to_roles (map por field)
          - tax_roles (fallback)
        y lo guarda en state['allowed_roles'].
        """
        field = tool_context.state.get("field")
        sub_field = tool_context.state.get("sub_field")

        field_sub_to_roles = tool_context.state.get("field_sub_to_roles") or {}
        field_to_roles = tool_context.state.get("field_to_roles") or {}
        tax_roles = tool_context.state.get("tax_roles") or []

        allowed = None

        if field and sub_field:
            key = f"{field}||{sub_field}"
            if key in field_sub_to_roles:
                allowed = field_sub_to_roles.get(key)

        if allowed is None and field and field in field_to_roles:
            allowed = field_to_roles.get(field)

        if not allowed:
            allowed = tax_roles

        tool_context.state["allowed_roles"] = allowed
        logger.info("prepare_allowed_roles field=%s sub_field=%s allowed_roles=%s", field, sub_field, allowed)
        return {"status": "success", "allowed_roles_count": len(allowed)}

    return Agent(
        name="role_classifier",
        model=settings.MODEL,
        description="Classify 'role' conditioned on field/sub_field with a closed allowed-role list.",
        instruction="""
        TASK:
          Choose EXACTLY one 'role' from the allowed roles for this (field, sub_field).

        STEPS:
          1) Call `prepare_allowed_roles` once.
          2) Choose EXACTLY one role from `allowed_roles`.

        INPUT STATE:
          field: { field? }
          sub_field: { sub_field? }
          employer: { employer? }
          sector: { sector? }
          activity_declared: { activity_declared? }

          allowed_roles: { allowed_roles? }
          tax_roles: { tax_roles? }

        RULES (STRICT):
          - You MUST pick a role that is EXACTLY in `allowed_roles`.
          - Do NOT invent labels.
          - Prioritize activity_declared to infer the role; employer/sector are secondary signals.

        
          

          REGLAS EXPLÍCITAS (ROLE / CARGO)
        0) Debes devolver EXACTAMENTE 1 etiqueta que esté en `tax_roles`. Nunca inventes etiquetas.

        1) PRECEDENCIA (si hay varias señales, aplica en este orden):
          a) Empleado público (si employer o activity indica institución pública)
          b) Dueño (si declara propiedad/negocio propio)
          c) Socio (si declara sociedad/accionista/representante legal con copropiedad)
          d) Jornalero / eventual (si es temporal/por día/ocasional)
          e) Independiente estructurado vs Independiente informal (si trabaja por cuenta propia sin empleador claro)
          f) Empleado dependiente privado - GERENCIA / ADMINISTRATIVO / AUXILIAR (si tiene empleador privado o rol típico dependiente)
          g) Técnico / operativo (si la naturaleza es técnica/operativa y no encaja mejor como dependiente privado por jerarquía)
          h) No definido (si es insuficiente/contradictorio)

        2) Disparadores por keywords:
          - Empleado público: alcaldía, gobernación, ministerio, entidad pública, órgano judicial, registro civil, municipalidad, FFAA, policía.
          - Dueño: "dueño", "propietario", "mi negocio", "tengo mi tienda", "empresa propia", "emprendimiento".
          - Socio: "socio", "accionista", "copropietario", "representante legal" (con señales de participación).
          - Jornalero / eventual: "jornalero", "eventual", "temporal", "por día", "ocasional", "trabajos ocasionales".
          - Independiente estructurado: profesión + continuidad/estructura (oficina, consultoría formal, servicios formales, clientes, facturo).
          - Independiente informal: "vendo por mi cuenta", marketplace, ambulante, ingreso variable, sin estructura, “hago ventas”.
          - Privado - GERENCIA: gerente, jefe, director, encargado, supervisor, administrador general.
          - Privado - ADMINISTRATIVO: administración, tesorería, RRHH, contabilidad interna, asistente administrativo, analista, backoffice.
            (Esto incluye lo que antes llamabas “C10 Administrativo”.)
          - Privado - AUXILIAR: cajero, repositor, atención al cliente, recepcionista, auxiliar, ayudante, limpieza, personal de apoyo.
          - Técnico / operativo: técnico, mantenimiento, soporte TI, mecánica, instalación, operario, conductor (si describe función técnica/operativa).

        3) Reglas de desempate:
          - Si dice “gerente/jefe/supervisor/encargado” y NO es dueño → Privado - GERENCIA.
          - Si dice “administración/tesorería/RRHH/contabilidad/asistente/analista” → Privado - ADMINISTRATIVO.
          - Si dice “cajero/atención al cliente/reponedor/auxiliar/limpieza” → Privado - AUXILIAR.
          - Si no hay empleador y es una profesión (abogado/contador/auditor/médico/etc.) → Independiente estructurado, salvo que el texto indique informalidad.
          - Si es policía/FFAA/entidad pública → Empleado público (no “Técnico/operativo”).
          - Si solo dice “trabajo/empleado” sin detalles → No definido.


          

          EJEMPLOS (INPUT -> ROLE)

        1)
        employer: ""
        sector: "otros"
        activity_declared: "Tengo mi tienda, soy dueño"
        -> role: "Dueño"

        2)
        employer: ""
        sector: "otros"
        activity_declared: "Soy representante legal de una empresa"
        -> role: "Socio"

        3)
        employer: ""
        sector: "otros"
        activity_declared: "Consultor contable, trabajo con oficina y clientes"
        -> role: "Independiente estructurado"

        4)
        employer: ""
        sector: "otros"
        activity_declared: "Vendo por mi cuenta por redes, ingreso variable"
        -> role: "Independiente informal"

        5)
        employer: "NAGA GROUP"
        sector: "servicios"
        activity_declared: "Gerente de proyectos"
        -> role: "Empleado dependiente privado - GERENCIA"

        6)
        employer: "Industrias VENDAVAL"
        sector: "industria"
        activity_declared: "Analista administrativo"
        -> role: "Empleado dependiente privado - ADMINISTRATIVO"

        7)
        employer: "Fidalga"
        sector: "comercio"
        activity_declared: "Cajera / atención al cliente"
        -> role: "Empleado dependiente privado - AUXILIAR"

        8)
        employer: "Alcaldía Municipal"
        sector: "sector público"
        activity_declared: "Funcionario administrativo"
        -> role: "Empleado público"

        9)
        employer: "Edificio Central"
        sector: "otros"
        activity_declared: "Guardia de seguridad"
        -> role: "Empleado dependiente privado - AUXILIAR"

        10)
        employer: "Taller Rápido"
        sector: "otros"
        activity_declared: "Técnico de mantenimiento"
        -> role: "Técnico / operativo"

        11)
        employer: ""
        sector: "otros"
        activity_declared: "Jornalero por día en construcción"
        -> role: "Jornalero / eventual"

        12)
        employer: ""
        sector: "otros"
        activity_declared: "No declara / solo dice que trabaja"
        -> role: "No definido"

        13)
        employer: "Constructora Sur"
        sector: "otros"
        activity_declared: "Arquitecta de una obra"
        -> role: "Empleado dependiente privado - ADMINISTRATIVO"




        OUTPUT:
          Call set_state exactly once:
            set_state(key="role", value="<chosen_role>")

          Do NOT output free text.
        """,
        tools=[prepare_allowed_roles, set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
