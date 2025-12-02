import sys
from collections import deque
from typing import Optional, List, Deque

class Proceso:
    # Representa un proceso en el motor GUI:
    # contiene datos fijos (ID, tamaño, TA, TI) y campos dinámicos para SRTF y métricas.
    def __init__(self, id_proceso: int, tamano: int, t_arribo: int, t_irrupcion: int):
        # Inicializa los atributos fijos (ID, tamaño, tiempos TA y TI).
        self.id_proceso = id_proceso
        self.tamano = tamano
        self.t_arribo = t_arribo
        self.t_irrupcion = t_irrupcion

        # Inicializa los atributos de estado dinámico (se actualizan durante la simulación).
        self.estado = "NUEVO"                  # Estado lógico del proceso (NUEVO, L/S, LISTO, EJECUCION, TERMINADO).
        self.t_restante = t_irrupcion          # Tiempo de CPU restante (clave para SRTF).
        self.id_particion: Optional[int] = None  # Partición de memoria asignada (None si no tiene).

        # Tiempos para el reporte estadístico (se completan a medida que avanza la simulación).
        self.t_fin = -1                        # Tiempo en que finaliza (para retorno T).
        self.t_primera_ejecucion = -1          # Instante de primera entrada a CPU (para respuesta R).
        self.t_llegada_listo = -1              # Tiempo de entrada a cola LISTO (para desempates SRTF).

    @property
    def id_str(self) -> str:
        # Propiedad para obtener el ID en formato "P#".
        return f"P{self.id_proceso}"


class Particion:
    # Representa una partición de memoria fija (MFT) utilizada por Best-Fit y swap.
    def __init__(self, id_particion: int, tamano: int, es_so: bool = False, base: int = 0):
        # Inicializa los atributos de la partición (ID, tamaño, si es SO, dirección base).
        self.id_particion = id_particion
        self.tamano = tamano
        self.es_so = es_so
        self.base = base
        self.proceso_asignado: Optional[Proceso] = None  # Proceso actualmente cargado en esta partición.

    @property
    def esta_libre(self) -> bool:
        # Indica si la partición está disponible para cargar procesos de usuario.
        return self.proceso_asignado is None and not self.es_so

    @property
    def fragmentacion_interna(self) -> int:
        # Calcula la fragmentación interna (diferencia entre tamaño de partición y proceso).
        if self.proceso_asignado:
            return self.tamano - self.proceso_asignado.tamano
        return 0

    def asignar_proceso(self, proceso: Proceso) -> bool:
        # Intenta asignar un proceso a la partición si:
        # - está libre
        # - el tamaño del proceso cabe en la partición.
        if self.esta_libre and proceso.tamano <= self.tamano:
            self.proceso_asignado = proceso
            proceso.id_particion = self.id_particion
            return True
        return False

    def liberar_particion(self):
        # Libera la partición (se llama cuando el proceso termina o es swappeado).
        if self.proceso_asignado:
            self.proceso_asignado.id_particion = None
        self.proceso_asignado = None


class Simulador:
    # Motor de simulación usado por la GUI:
    # - Controla colas y estados de procesos
    # - Aplica SRTF con desalojo
    # - Maneja memoria con Best-Fit y política de swap
    # - Expone snapshots para la interfaz y un reporte final.
    def __init__(self, procesos: List[Proceso]):
        # Inicializa el reloj global y estructuras de estado.
        self.reloj = 0
        self.eventos_del_tick: List[str] = []  # Eventos registrados en el instante actual (para mostrar en GUI).

        self.todos_procesos: List[Proceso] = procesos

        # Colas lógicas del ciclo de vida.
        self.procesos_nuevos: Deque[Proceso] = deque()          # Procesos que aún no ingresaron al sistema (TA > t).
        self.cola_listos: Deque[Proceso] = deque()              # Procesos en memoria, listos para CPU.
        self.cola_listos_suspendidos: Deque[Proceso] = deque()  # Procesos en L/S (en disco, candidatos a admisión).
        self.proceso_en_ejecucion: Optional[Proceso] = None     # Proceso que actualmente ocupa la CPU.
        self.procesos_terminados: List[Proceso] = []            # Historial de procesos finalizados.
        self.procesos_reporte: List[Proceso] = []               # Conjunto sobre el que se calculan métricas.

        # Configuración de particiones fijas (MFT):
        # P0 → SO, P1–P3 → particiones de usuario.
        self.particiones = [
            Particion(0, 100, es_so=True, base=0),   # SO
            Particion(1, 250, base=100),             # Partición 1
            Particion(2, 150, base=350),             # Partición 2
            Particion(3,  50, base=500),             # Partición 3
        ]
        self._preparar_colas()
        
        self._guardar_estado_inicial()  # Ejecuta la lógica de arranque en t=0.

    def get_reloj(self) -> int:
        # Devuelve el tiempo actual de reloj de la simulación (t).
        return self.reloj

    def get_datos_gui(self) -> dict:
        # Construye un snapshot del estado del simulador para que la GUI lo pinte.
        # Incluye:
        # - reloj actual
        # - eventos del tick
        # - estado de colas
        # - estado de particiones
        # - tabla con procesos y progreso.

        def get_info_particion(p: Particion) -> dict:
            # Función auxiliar para serializar una partición hacia la GUI.
            if p.es_so:
                contenido = "Sistema operativo"; estado = "FI: 0 KB"
            elif p.proceso_asignado:
                pr = p.proceso_asignado
                contenido = f"{pr.id_str} ({pr.tamano} KB)"
                estado = f"FI: {p.fragmentacion_interna} KB"
            else:
                contenido = "—"; estado = "Espacio Libre"
            return {
                "id": str(p.id_particion),
                "base": str(p.base),
                "tamano": f"{p.tamano} KB",
                "contenido": contenido,
                "estado": estado,
            }

        # Representación del proceso en ejecución, si existe.
        if self.proceso_en_ejecucion:
            run = self.proceso_en_ejecucion
            ejecutando = f"{run.id_str} (Restante: {run.t_restante})"
        else:
            ejecutando = "—"

        # Copia de la lista de eventos de este tick (evita referencias compartidas).
        eventos = list(getattr(self, "eventos_del_tick", []))

        # Construcción de la tabla de procesos con su estado y progreso porcentual.
        tabla_procesos = []
        for p in self.procesos_reporte:
            estado = p.estado
            # Mapeo de estados lógicos a etiquetas utilizadas por la GUI.
            if p in self.procesos_terminados or p.estado == "TERMINADO":
                estado = "Terminado"
            elif p is self.proceso_en_ejecucion:
                estado = "Ejecutando"
            elif p in self.cola_listos:
                estado = "Listo"
            elif p in self.cola_listos_suspendidos:
                estado = "ListoSuspendido"
            elif p in self.procesos_nuevos:
                estado = "Nuevo"

            # Cálculo de porcentaje de ejecución (0–100 %).
            progreso = 0.0
            if p.t_irrupcion > 0:
                if p in self.procesos_terminados or p.estado == "TERMINADO":
                    progreso = 100.0
                else:
                    ejecutado = max(0, p.t_irrupcion - p.t_restante)
                    progreso = max(0.0, min(100.0, (ejecutado / p.t_irrupcion) * 100.0))

            tabla_procesos.append({
                "pid": p.id_str,
                "ta": p.t_arribo,
                "ti": p.t_irrupcion,
                "mem": p.tamano,
                "estado": estado,
                "progreso": progreso,
            })

        # Estructura final devuelta a la GUI.
        return {
            "reloj": self.reloj,
            "eventos": eventos,
            "ejecutando": ejecutando,
            "listos": [p.id_str for p in self.cola_listos],
            "listos_suspendidos": [p.id_str for p in self.cola_listos_suspendidos],
            "nuevos": [p.id_str for p in self.procesos_nuevos],
            "terminados": [p.id_str for p in self.procesos_terminados],
            "particiones": [get_info_particion(p) for p in self.particiones],
            "tabla_procesos": tabla_procesos,
        }

    
    def get_reporte_final(self) -> dict:
        # Calcula y empaqueta las métricas finales:
        # - Por proceso: T, W, R
        # - Promedios globales
        # - Throughput (trabajos/t.u.).
        reporte_procesos = []
        total_retorno = total_espera = total_respuesta = 0
        procesos_contados = 0
        
        # Orden por PID para una salida consistente.
        self.procesos_reporte.sort(key=lambda p: p.id_proceso)
        
        for p in self.procesos_reporte:
            if p.t_fin != -1:
                # Cálculo de métricas para procesos terminados.
                procesos_contados += 1
                T = p.t_fin - p.t_arribo                     # Retorno.
                W = T - p.t_irrupcion                        # Espera.
                R = p.t_primera_ejecucion - p.t_arribo       # Respuesta.
                total_retorno += T
                total_espera += W
                total_respuesta += R
                reporte_procesos.append({
                    "pid": p.id_str,
                    "arribo": p.t_arribo,
                    "primera_cpu": p.t_primera_ejecucion,
                    "fin": p.t_fin,
                    "servicio": p.t_irrupcion,
                    "espera": W,
                    "respuesta": R,
                    "retorno": T
                })
            elif p.estado == "L/S" and not self._cabe_en_alguna_particion(p):
                # Procesos que nunca pudieron ser admitidos por tamaño.
                reporte_procesos.append({
                    "pid": p.id_str,
                    "arribo": p.t_arribo,
                    "primera_cpu": "—",
                    "fin": "—",
                    "servicio": p.t_irrupcion,
                    "espera": "—",
                    "respuesta": "—",
                    "retorno": f"No admitido ({p.tamano} KB)"
                })
        
        # Cálculo de promedios a partir de las sumas acumuladas.
        promedios = {}
        if procesos_contados > 0:
            promedios = {
                "espera": f"{total_espera / procesos_contados:.2f}",
                "respuesta": f"{total_respuesta / procesos_contados:.2f}",
                "retorno": f"{total_retorno / procesos_contados:.2f}",
            }
        
        # Cálculo de rendimiento (throughput = procesos terminados / tiempo transcurrido).
        throughput = "0.000"
        if self.reloj > 0:
            throughput = f"{procesos_contados / self.reloj:.3f}"

        return {
            "procesos": reporte_procesos,
            "promedios": promedios,
            "throughput": throughput,
            "procesos_contados": procesos_contados,
            "tiempo_final": self.reloj
        }

    def _preparar_colas(self):
        # Selecciona hasta 10 procesos, ordenados por (TA, ID),
        # y los inicializa como NUEVOS para comenzar la simulación.
        candidatos = sorted(self.todos_procesos, key=lambda x: (x.t_arribo, x.id_proceso))
        seleccion = candidatos[:10]

        for p in seleccion:
            # Reset de campos dinámicos para la simulación.
            p.estado = "NUEVO"
            p.t_restante = p.t_irrupcion
            p.id_particion = None
            p.t_fin = -1
            p.t_primera_ejecucion = -1
            p.t_llegada_listo = -1

        self.procesos_nuevos = deque(seleccion)
        self.procesos_reporte = list(seleccion)

    def _guardar_estado_inicial(self):
        # Ejecuta la lógica inicial del instante t=0:
        # - detecta arribos con TA=0
        # - los pasa a L/S (si GDM lo permite)
        # - intenta admisión a memoria
        # - ejecuta la primera decisión del planificador.
        eventos = []
        arribados = []

        # Mueve los procesos con TA=0 desde NUEVOS a L/S.
        while self.procesos_nuevos and self.procesos_nuevos[0].t_arribo == 0:
            arribados.append(self.procesos_nuevos.popleft())
        if arribados:
            eventos.append("Arriban " + ", ".join(p.id_str for p in arribados))
        
        # Para cada proceso arribado en t=0 se verifica si puede caber en alguna partición.
        for p in arribados:
            if not self._cabe_en_alguna_particion(p):
                # No cabe en ninguna partición: solo podrá figurar como "no admitido".
                p.estado = "L/S"
                self.cola_listos_suspendidos.append(p)
                eventos.append(f"{p.id_str}({p.tamano}K) no cabe (máx 250K)")
            else:
                # Entra a L/S, pendiente de admisión.
                p.estado = "L/S"
                self.cola_listos_suspendidos.append(p)
        
        # Se intenta admitir procesos desde L/S a memoria (LISTO).
        self._intentar_admision(eventos)
        # Se aplica el planificador SRTF para decidir qué entra a CPU.
        self._ejecutar_planificador(eventos)
        # Se almacenan los eventos generados en t=0.
        self.eventos_del_tick = eventos

    def tick(self):
        # Ejecuta la lógica de un avance de tiempo (un "tick" de simulación) para la GUI.
        eventos = []
        self.eventos_del_tick = []  # Limpia eventos anteriores.

        # 1. CPU: avanza 1 unidad de tiempo y verifica terminación del proceso en ejecución.
        if self.proceso_en_ejecucion:
            cur = self.proceso_en_ejecucion
            cur.t_restante -= 1
            if cur.t_restante == 0:
                # El proceso termina en este tick.
                cur.estado = "TERMINADO"
                cur.t_fin = self.reloj + 1 
                self.procesos_terminados.append(cur)
                self.proceso_en_ejecucion = None

                # Libera partición y registra evento.
                part = self.particiones[cur.id_particion]
                part.liberar_particion()
                eventos.append(f"Termina {cur.id_str} → libera P{part.id_particion}({part.tamano} KB)")

        # 2. Llegadas al sistema considerando GDM del sistema (GDM=5).
        arribados_a_ls = []

        # GDM actual = procesos en listos + L/S + el que está ejecutando.
        gdm_actual = len(self.cola_listos) + len(self.cola_listos_suspendidos) + (1 if self.proceso_en_ejecucion else 0)

        # Identifica procesos que deberían arribar exactamente en este t
        # para poder reportar quiénes quedan afuera por GDM lleno.
        recien_arriban_ids = [p.id_str for p in list(self.procesos_nuevos) if p.t_arribo == self.reloj]

        # Mientras haya GDM disponible y arriben procesos en este tick, pasan a L/S.
        while self.procesos_nuevos and self.procesos_nuevos[0].t_arribo == self.reloj and gdm_actual < 5:
            p = self.procesos_nuevos.popleft()
            arribados_a_ls.append(p)
            gdm_actual += 1

        # Procesos que arriban en t pero NO entran por GDM lleno: permanecen en NUEVOS.
        movidos_ids = {p.id_str for p in arribados_a_ls}
        rechazados_ids = [pid for pid in recien_arriban_ids if pid not in movidos_ids]
        if arribados_a_ls:
            eventos.append("Arriban (al sistema): " + ", ".join(p.id_str for p in arribados_a_ls))
        if rechazados_ids:
            eventos.append("Arriban (GDM Lleno, quedan en Nuevos): " + ", ".join(rechazados_ids))

        # Completa GDM con atrasados (TA < t) que aún estaban en NUEVOS.
        while self.procesos_nuevos and self.procesos_nuevos[0].t_arribo < self.reloj and gdm_actual < 5:
            p = self.procesos_nuevos.popleft()
            arribados_a_ls.append(p)
            gdm_actual += 1

        # Todos los efectivamente admitidos al sistema se marcan como L/S.
        for p in arribados_a_ls:
            p.estado = "L/S"
            self.cola_listos_suspendidos.append(p)

        # 3. Admisión/Swap: movimientos L/S → LISTO (Best-Fit + swap con GDM en memoria = 3).
        self._intentar_admision(eventos)
        
        # 4. Planificador de CPU SRTF (con posible desalojo).
        self._ejecutar_planificador(eventos)

        # Guarda los eventos del tick para que la GUI los muestre.
        self.eventos_del_tick = eventos

    def _intentar_admision(self, eventos: List[str]):
        # Implementa:
        # - Admisión normal: si GDM en memoria < 3 y hay particiones libres → Best-Fit.
        # - Swap: si GDM en memoria = 3, se busca víctima para desalojar si el candidato es más corto.
        while True:
            # Ordena L/S por SRTF puro (menor t_restante, tie-break por ID).
            self.cola_listos_suspendidos = deque(sorted(
                self.cola_listos_suspendidos,
                key=lambda p: (p.t_restante, p.id_proceso) 
            ))

            hubo_cambio = False
            
            for candidato in list(self.cola_listos_suspendidos):
                procesos_en_memoria = len(self.cola_listos) + (1 if self.proceso_en_ejecucion else 0)
                libres = [pp for pp in self.particiones if pp.esta_libre]
                
                if procesos_en_memoria < 3 and libres:
                    # Admisión normal: hay lugar en memoria principal.
                    mejor_part = self._encontrar_mejor_particion(candidato, libres)
                    if mejor_part:
                        # Se asigna la mejor partición al candidato (Best-Fit) y pasa a LISTO.
                        self.cola_listos_suspendidos.remove(candidato)
                        mejor_part.asignar_proceso(candidato)
                        candidato.estado = "LISTO"
                        candidato.t_llegada_listo = self.reloj
                        self.cola_listos.append(candidato)
                        eventos.append(
                            f"Admisión {candidato.id_str}({candidato.tamano}K) → "
                            f"P{mejor_part.id_particion}({mejor_part.tamano}K) FI: {mejor_part.fragmentacion_interna} KB"
                        )
                        hubo_cambio = True
                        break 
                
                elif procesos_en_memoria == 3:
                    # Se evalúa un swap: se busca víctima entre los procesos en memoria.
                    posibles_victimas = list(self.cola_listos)
                    if self.proceso_en_ejecucion:
                        posibles_victimas.append(self.proceso_en_ejecucion)
                    
                    victimas_validas = []
                    for v in posibles_victimas:
                        part = self.particiones[v.id_particion]
                        if part.tamano >= candidato.tamano:
                            victimas_validas.append(v)
                    
                    if victimas_validas:
                        # La víctima es la de mayor t_restante (SRTF inverso).
                        victima = max(victimas_validas, key=lambda p: (p.t_restante, p.id_proceso))
                        
                        if candidato.t_restante < victima.t_restante:
                            # Swap efectivo: el candidato es “mejor” (más corto) que la víctima.
                            part_victima = self.particiones[victima.id_particion]
                            
                            # Saca a la víctima de memoria (CPU o LISTO → L/S) y libera partición.
                            if victima == self.proceso_en_ejecucion:
                                self.proceso_en_ejecucion = None
                            else:
                                self.cola_listos.remove(victima)
                            victima.estado = "L/S"
                            victima.id_particion = None
                            part_victima.liberar_particion()
                            self.cola_listos_suspendidos.append(victima)
                            
                            # Candidato entra en la partición liberada.
                            self.cola_listos_suspendidos.remove(candidato)
                            part_victima.asignar_proceso(candidato)
                            candidato.estado = "LISTO"
                            candidato.t_llegada_listo = self.reloj
                            self.cola_listos.append(candidato)
                            
                            eventos.append(
                                f"Swap: Sale {victima.id_str}(R:{victima.t_restante}) ↔ "
                                f"Entra {candidato.id_str}(R:{candidato.t_restante}) en P{part_victima.id_particion}"
                            )
                            hubo_cambio = True
                            break
            
            # Si no se logró ninguna admisión/swap en este ciclo, se termina.
            if not hubo_cambio:
                break

    def _ejecutar_planificador(self, eventos: List[str]):
        # Aplica la política SRTF:
        # - Selecciona el proceso con menor t_restante para ejecutar
        # - Decide si debe haber desalojo en función del candidato frente al proceso actual.
        corto = self._encontrar_proceso_srtf()

        if self.proceso_en_ejecucion is None:
            # CPU libre: se toma el más corto de la cola LISTOS.
            if corto:
                self.proceso_en_ejecucion = self.cola_listos.popleft()
                self.proceso_en_ejecucion.estado = "EJECUCION"
                if self.proceso_en_ejecucion.t_primera_ejecucion == -1:
                    self.proceso_en_ejecucion.t_primera_ejecucion = self.reloj
                eventos.append(
                    f"SRTF: Inicia {self.proceso_en_ejecucion.id_str} "
                    f"(Restante: {self.proceso_en_ejecucion.t_restante})"
                )
        else:
            # CPU ocupada: se verifica si el candidato debe desalojar al proceso en ejecución.
            run = self.proceso_en_ejecucion
            if corto and (
                (corto.t_restante < run.t_restante) or
                (corto.t_restante == run.t_restante and corto.t_llegada_listo < run.t_llegada_listo)
            ):
                # Desalojo: el proceso actual pasa a LISTO y entra el más corto.
                sal = run
                sal.estado = "LISTO"
                sal.t_llegada_listo = self.reloj
                self.cola_listos.append(sal)

                # Reordena la cola en función de (t_restante, llegada_listo, id).
                self.cola_listos = deque(sorted(
                    self.cola_listos, key=lambda p: (p.t_restante, p.t_llegada_listo, p.id_proceso)
                ))
                
                ent = self.cola_listos.popleft()
                ent.estado = "EJECUCION"
                if ent.t_primera_ejecucion == -1:
                    ent.t_primera_ejecucion = self.reloj
                self.proceso_en_ejecucion = ent
                eventos.append(
                    f"SRTF: Desalojo ({sal.id_str}) → entra {ent.id_str} "
                    f"(Restante: {ent.t_restante})"
                )

    def _cabe_en_alguna_particion(self, proceso: Proceso) -> bool:
        # Determina si existe alguna partición de usuario donde el proceso pueda caber por tamaño.
        for p in self.particiones:
            if not p.es_so and proceso.tamano <= p.tamano:
                return True
        return False

    def _encontrar_mejor_particion(self, proceso: Proceso, particiones: List[Particion]) -> Optional[Particion]:
        # Aplica Best-Fit sobre una lista de particiones libres:
        # selecciona la que deja la menor fragmentación interna.
        mejor, menor_fi = None, float("inf")
        for part in particiones:
            if part.esta_libre and proceso.tamano <= part.tamano:
                fi = part.tamano - proceso.tamano
                if fi < menor_fi or (fi == menor_fi and (mejor is None or part.tamano < mejor.tamano)):
                    menor_fi, mejor = fi, part
        return mejor

    def _encontrar_proceso_srtf(self) -> Optional[Proceso]:
        # Ordena la cola LISTOS según SRTF:
        # menor t_restante, luego menor t_llegada_listo, luego menor ID.
        # Devuelve el proceso "candidato" (no lo saca de la cola).
        if not self.cola_listos:
            return None
        self.cola_listos = deque(sorted(
            self.cola_listos,
            key=lambda p: (p.t_restante, p.t_llegada_listo, p.id_proceso)
        ))
        return self.cola_listos[0]
    
    def is_running(self) -> bool:
        # Indica si la simulación todavía puede seguir avanzando:
        # - Hay algo ejecutando o listo
        # - o existe algún proceso en L/S o NUEVOS que sea admisible en memoria.
        if self.proceso_en_ejecucion:
            return True
        if self.cola_listos:
            return True

        # Determina el tamaño máximo de partición de usuario.
        max_part = max((p.tamano for p in self.particiones if not p.es_so), default=0)
        if max_part == 0: 
            return False

        # Hay procesos en L/S que podrían admitirse en memoria.
        hay_admisible_en_ls = any(pr.tamano <= max_part for pr in self.cola_listos_suspendidos)
        if hay_admisible_en_ls:
            return True
        
        # Hay procesos en NUEVOS que en algún momento podrían entrar.
        hay_admisible_en_nuevos = any(pr.tamano <= max_part for pr in self.procesos_nuevos)
        if hay_admisible_en_nuevos:
            return True

        # Ningún proceso más puede ejecutarse ni ser admitido.
        return False
