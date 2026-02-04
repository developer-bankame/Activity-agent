# Activity-agent

RUBROS = {
    R1: Comercio minorista
    R2: Distribucion / Mayorista
    R3: Servicios tecnicos
    R4: Servicios Profesionales
    R5: Educacion
    R6: Salud
    R7: Transporte
    R8: Produccion / Manufactura
    R9: Sector publico
    R10: Administrativo / oficina               *
    R11: Gastronomia
    R12: Construccion / obra
    R13: Agro / Ganaderia
    R14: Servicios personales
    R15: Ocio / nocturno / eventos
    R16: Eventual                               -
    R17: Mixto                                  ///
    R18: Seguridad                              ///
    R19: Servicios Financieros                  ///
    R20: Estudiante                             ///
    R21: Servicios Comerciales                  ///
    R22: Publicidad, comunicacion y marketing   ///
    R99: Indefinido
}

CARGOS = {
    C1: Dueño
    C2: Socio
    C3: Independiente estructurado
    C4: Independiente informal
    C5: Empleado dependiente privado -> GER     ///
    C6: Empleado dependiente privado -> ADM     ///
    C7: Empleado dependiente privada -> AUX     ///
    C8: Empleado publico
    C9: Tecnico / operativo
    C10: Jornalero / eventual                   -
    C99: No definido
}


# Probando localmente

# TERMINAL:
Levanta tu servidor localmente
python main.py

# Realizar pruebas locales:

curl -i -X POST "http://localhost:8015/agent/scan" \
  -H "Content-Type: application/json" \
  -d '{"client_id":4582,"trace_id":"local-e2e"}'

# Usar '.csv' para clasificar n cantidad de clientes:

Batch para activity cluster, modelo de scoring:
python main.py para inicializar el servidor, luego en una nueva terminal:
python scripts/run_batch.py --base-url http://localhost:8015 --workers 1 --timeout 180