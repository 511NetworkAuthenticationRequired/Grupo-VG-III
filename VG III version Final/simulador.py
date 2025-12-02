# simulador.py
# Simulador por consola del algoritmo de planificación SRTF + administración de memoria Best-Fit.
# Gestiona procesos, colas, particiones y genera métricas finales.

import sys
import csv
from collections import deque
from typing import Optional, List, Deque

# -------------------- Datos --------------------

class Proceso:
    # Representa un proceso del sistema:
    # contiene información de memoria, tiempos y estado para planificación SRTF.
    def __init__(self, id_proceso: int, tamano: int, t_arribo: int, t_irrupcion: int):
        self.id_proceso = id_proceso       # Identificador lógico.  
        self.tamano = tamano               # Tamaño requerido en memoria.
        self.t_arribo = t_arribo           # Tiempo de arribo al sistema.
        self.t_irrupcion = t_irrupcion     # CPU burst inicial.

        self.estado = "NUEVO"              # Estado del proceso dentro del ciclo de vida.
        self.t_restante = t_irrupcion      # CPU restante para SRTF.
        self.id_particion: Optional[int] = None  # Partición asignada.

        # Datos para métricas de rendimiento.
        self.t_fin = -1                    # Tiempo de fin.
        self.t_primera_ejecucion = -1      # Tiempo en que toma CPU por primera vez.
        self.t_llegada_listo = -1          # Tiempo en que ingresa a LISTO (usado en SRTF).

    @property
    def id_str(self) -> str:
        return f"P{self.id_proceso}"       # Representación estándar.


class Particion:
    # Representa una partición fija de memoria (estilo MFT).
    def __init__(self, id_particion: int, tamano: int, es_so: bool = False, base: int = 0):
        self.id_particion = id_particion   # Indice de partición.
        self.tamano = tamano               # Tamaño total de la partición.
        self.es_so = es_so                 # Si está reservada para el SO.
        self.base = base                   # Dirección base.
        self.proceso_asignado: Optional[Proceso] = None  # Proceso cargado en la partición.

    @property
    def esta_libre(self) -> bool:
        # Indica si la partición puede alojar un proceso (libre y no es SO).
        return self.proceso_asignado is None and not self.es_so

    @property
    def fragmentacion_interna(self) -> int:
        # Espacio desperdiciado dentro de la partición por Best-Fit.
        if self.proceso_asignado:
            return self.tamano - self.proceso_asignado.tamano
        return 0

    def asignar_proceso(self, proceso: Proceso) -> bool:
        # Intenta cargar un proceso si cabe. Actualiza referencias mutuas.
        if self.esta_libre and proceso.tamano <= self.tamano:
            self.proceso_asignado = proceso
            proceso.id_particion = self.id_particion
            return True
        return False

    def liberar_particion(self):
        # Libera la partición al terminar un proceso.
        if self.proceso_asignado:
            self.proceso_asignado.id_particion = None
        self.proceso_asignado = None


# -------------------- Simulador --------------------

class Simulador:
    # Motor de simulación por consola:
    # - Lee CSV
    # - Permite edición manual previa
    # - Ejecuta planificación SRTF con desalojo
    # - Administra memoria con particiones fijas y Best-Fit
    def __init__(self, archivo_procesos: str):
        self.archivo_procesos = archivo_procesos
        self.reloj = 0                     # Reloj global de simulación.

        # Carga inicial de todos los procesos disponibles.
        self.todos_procesos: List[Proceso] = self._leer_csv(archivo_procesos)

        # Colas de estados (modelo por niveles: NUEVOS → L/S → LISTO → CPU → TERMINADOS).
        self.procesos_nuevos: Deque[Proceso] = deque()
        self.cola_listos: Deque[Proceso] = deque()
        self.cola_listos_suspendidos: Deque[Proceso] = deque()
        self.proceso_en_ejecucion: Optional[Proceso] = None
        self.procesos_terminados: List[Proceso] = []
        self.procesos_reporte: List[Proceso] = []

        # Particiones fijas de memoria (MFT). P0 = SO.
        self.particiones = [
            Particion(0, 100, es_so=True, base=0),
            Particion(1, 250, base=100),
            Particion(2, 150, base=350),
            Particion(3,  50, base=500),
        ]

    # ---------- Helper para ID automático ----------
    def _siguiente_id(self) -> int:
        # Devuelve el ID siguiente para opción “Agregar”.
        if not self.todos_procesos:
            return 1
        return max(p.id_proceso for p in self.todos_procesos) + 1

    # -------------------- CSV I/O --------------------

    def _leer_csv(self, path: str) -> List[Proceso]:
        # Implementa un lector completo de CSV similar al de lector_csv.py,
        # aceptando encabezados flexibles y múltiples alias de columnas.
        # Se utiliza aquí para la versión de consola.
        import unicodedata
        def norm(s: str) -> str:
            s = (s or "").strip()
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
            return s.replace("ñ","n").replace("Ñ","N").upper()

        procs: List[Proceso] = []
        ids_vistos = set()

        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                raw = list(csv.reader(f))
        except FileNotFoundError:
            print(f"Error: no existe {path}"); sys.exit(1)
        except Exception:
            print("ERROR: la estructura debe ser la solicitada!"); sys.exit(1)

        if not raw:
            return procs

        # Detecta encabezado o datos directos analizando la primera fila.
        first = raw[0]
        def is_int(x):
            try: int(str(x).strip()); return True
            except: return False
        first_is_data = len(first) >= 4 and all(is_int(c) for c in first[:4])

        id_idx = tam_idx = ta_idx = ti_idx = None

        if first_is_data:
            # CSV sin encabezado → columnas fijas.
            data_rows = raw
            id_idx, tam_idx, ta_idx, ti_idx = 0, 1, 2, 3
            start_line = 1
        else:
            # CSV con encabezado flexible → mapeo mediante normalización.
            headers = [norm(h) for h in first]
            IDN   = {"ID","IDP","PID"}
            TAMN  = {"TAMANO","TAMANIO","TAM","SIZE","TAMM"}
            TAN   = {"TA","ARRIBO","LLEGADA"}
            TIN   = {"TI","IRRUPCION","IRRUPCIONCPU","BURST","CPU","SERVICIO","DURACION"}

            for i,h in enumerate(headers):
                if id_idx is None and h in IDN:   id_idx = i
                elif tam_idx is None and h in TAMN: tam_idx = i
                elif ta_idx is None and h in TAN:  ta_idx = i
                elif ti_idx is None and h in TIN:  ti_idx = i

            if None in (id_idx, tam_idx, ta_idx, ti_idx) and len(first) >= 4:
                # Fallback por posición.
                id_idx, tam_idx, ta_idx, ti_idx = 0, 1, 2, 3

            data_rows = raw[1:]
            start_line = 2

        # Construcción de objetos Proceso.
        for off, row in enumerate(data_rows, start=start_line):
            def get(i):
                try:
                    return "" if i is None or i >= len(row) else str(row[i]).strip()
                except:
                    return ""
            sid, stam, sta, sti = get(id_idx), get(tam_idx), get(ta_idx), get(ti_idx)

            if not any([sid, stam, sta, sti]):
                continue

            try:
                pid = int(sid); tam = int(stam); ta = int(sta); ti = int(sti)
            except Exception:
                print(f"ERROR fila {off}: valores no enteros — fila ignorada.")
                continue

            motivos = []
            if pid <= 0: motivos.append("ID debe ser positivo")
            if pid in ids_vistos: motivos.append("ID duplicado")
            if tam <= 0: motivos.append("TAMANO debe ser > 0")
            if ta  <  0: motivos.append("TA no puede ser negativo")
            if ti  <= 0: motivos.append("TI debe ser > 0")
            if motivos:
                print(f"ERROR fila {off}: " + "; ".join(motivos) + " — fila ignorada.")
                continue

            ids_vistos.add(pid)
            procs.append(Proceso(pid, tam, ta, ti))

        return procs

    def _guardar_csv(self, path: str, procs: List[Proceso]):
        # Exporta la lista actual de procesos editable por el usuario.
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ID","TAMANO","TA","TI"])
            for p in procs:
                w.writerow([p.id_proceso, p.tamano, p.t_arribo, p.t_irrupcion])

    # -------------------- UI inicial --------------------

    def _render_tabla(self, procs: List[Proceso]):
        # Representación en consola de todos los procesos disponibles.
        print("")
        print("-----VISTA GENERAL DE LOS PROCESOS-----")
        print(f"{'IDP':<4} {'TAMAÑO':>7} {'TI':>4} {'TA':>4}")
        for p in sorted(procs, key=lambda x: x.id_proceso):
            print(f"{p.id_proceso:<4} {p.tamano:>7} {p.t_irrupcion:>4} {p.t_arribo:>4}")
        print("")

    def _menu_edicion(self):
        # Permite agregar/editar/eliminar procesos antes de iniciar la simulación.
        # Modifica self.todos_procesos y luego guarda el CSV.
        while True:
            self._render_tabla(self.todos_procesos)
            print("[1] Agregar  [2] Editar  [3] Eliminar  [4] Guardar y continuar")
            op = input("> ").strip()

            if op == "1":
                # Registrar un proceso nuevo con ID autogenerado.
                try:
                    pid = self._siguiente_id()
                    print(f"ID asignado automáticamente: {pid}")
                    tam = int(input("Tamaño(KB): "))
                    ta  = int(input("TA: "))
                    ti  = int(input("TI: "))
                    self.todos_procesos.append(Proceso(pid, tam, ta, ti))
                except Exception:
                    pass
                continue

            if op == "2":
                # Modificación de un proceso en la lista.
                try:
                    pid = int(input("ID a editar: "))
                    lst = [p for p in self.todos_procesos if p.id_proceso == pid]
                    if lst:
                        p = lst[0]
                        tam = int(input(f"Tamaño(KB) [{p.tamano}]: ") or p.tamano)
                        ta  = int(input(f"TA [{p.t_arribo}]: ") or p.t_arribo)
                        ti  = int(input(f"TI [{p.t_irrupcion}]: ") or p.t_irrupcion)
                        p.tamano, p.t_arribo, p.t_irrupcion = tam, ta, ti
                except Exception:
                    pass
                continue

            if op == "3":
                # Eliminación por ID.
                try:
                    pid = int(input("ID a eliminar: "))
                    self.todos_procesos = [p for p in self.todos_procesos if p.id_proceso != pid]
                except Exception:
                    pass
                continue

            if op == "4":
                # Guarda y abandona la etapa de edición.
                self._guardar_csv(self.archivo_procesos, self.todos_procesos)
                break

            print("Error: opción inválida. Ingrese 1, 2, 3 o 4.")
            continue

    # -------------------- Simulación --------------------

    def run(self):
        # Bucle principal de ejecución por consola: edición → preparación → ticks → reporte.
        print("Bienvenidos al sistema operativo de VG III!\n")
        self._menu_edicion()        # Ajuste previo de procesos.
        self._preparar_colas()      # Selección de los 10 procesos admitidos.

        print("──────────────────────── ESTADO INICIAL DE LA MEMORIA ────────────────────────")
        self._imprimir_estado_completo()

        try:
            # Ciclo temporal de simulación con límite anti-loop.
            while self.procesos_nuevos or self.cola_listos_suspendidos or self.cola_listos or self.proceso_en_ejecucion:
                self._tick()        # Avanza 1 t.u. con planificación + memoria.
                self.reloj += 1
                if self.reloj > 500:
                    print("Simulación detenida: Límite de tiempo excedido.")
                    break

            print("────────────────────────────── ESTADO FINAL ───────────────────────────────")
            self._imprimir_estado_completo(final=True)
            self._imprimir_reporte_final()
        except KeyboardInterrupt:
            print("\nSimulación interrumpida.")
            self._imprimir_reporte_final()


    def _preparar_colas(self):
        # Selecciona hasta 10 procesos con ID 1–10 ordenados por arribo e ID.
        # Inicializa su estado interno.
        candidatos = [p for p in self.todos_procesos if 1 <= p.id_proceso <= 10]
        candidatos.sort(key=lambda x: (x.t_arribo, x.id_proceso))
        seleccion = candidatos[:10]

        for p in seleccion:
            p.estado = "NUEVO"
            p.t_restante = p.t_irrupcion
            p.id_particion = None
            p.t_fin = -1
            p.t_primera_ejecucion = -1
            p.t_llegada_listo = -1

        self.procesos_nuevos = deque(seleccion)
        self.procesos_reporte = list(seleccion)

    def _tick(self):
        # Ejecuta la lógica completa de un instante temporal:
        # CPU → arribos → L/S → admisión Best-Fit → planificador SRTF → impresión de estado.
        eventos = []

        # 1) CPU: avance y terminación del proceso en ejecución.
        if self.proceso_en_ejecucion:
            cur = self.proceso_en_ejecucion
            cur.t_restante -= 1
            if cur.t_restante == 0:
                # Proceso finaliza.
                cur.estado = "TERMINADO"
                cur.t_fin = self.reloj + 1
                self.procesos_terminados.append(cur)
                self.proceso_en_ejecucion = None

                # Libera partición asociada.
                part = self.particiones[cur.id_particion]
                part.liberar_particion()
                eventos.append(f"Termina {cur.id_str} → libera P{part.id_particion}({part.tamano} KB)")

        # 2) Arribos a tiempo de reloj.
        arribados = []
        while self.procesos_nuevos and self.procesos_nuevos[0].t_arribo == self.reloj:
            arribados.append(self.procesos_nuevos.popleft())
        if arribados:
            eventos.append("Arriban " + ", ".join(p.id_str for p in arribados))

        # 3) Todos los arribados pasan a L/S (evaluación posterior de memoria).
        for p in arribados:
            if not self._cabe_en_alguna_particion(p):
                # Proceso demasiado grande para cualquier partición.
                p.estado = "L/S"
                self.cola_listos_suspendidos.append(p)
                eventos.append(f"{p.id_str}({p.tamano}K) no cabe (máx 250K)")
            else:
                # Proceso admisible pero aún en espera de Best-Fit.
                p.estado = "L/S"
                self.cola_listos_suspendidos.append(p)

        # 4) Admisión a memoria usando Best-Fit y respetando grado de multiprogramación = 5.
        while True:
            procesos_en_memoria = len(self.cola_listos) + (1 if self.proceso_en_ejecucion else 0)
            if procesos_en_memoria >= 5:
                break

            libres = [pp for pp in self.particiones if pp.esta_libre]
            if not libres:
                break

            # Selección del proceso que será admitido:
            #   • debe caber en alguna partición
            #   • se elige por menor t_restante (SRTF) y antigüedad en L/S
            sel_proc = None
            sel_part = None
            sel_idx = None
            sel_r = float("inf")

            for i, pr in enumerate(self.cola_listos_suspendidos):
                mp = self._encontrar_mejor_particion(pr, libres)
                if mp:
                    if (pr.t_restante < sel_r) or (pr.t_restante == sel_r and (sel_idx is None or i < sel_idx)):
                        sel_proc, sel_part, sel_idx, sel_r = pr, mp, i, pr.t_restante

            if sel_proc is None:
                break

            # Inserción a memoria → pasa a LISTO.
            self.cola_listos_suspendidos.remove(sel_proc)
            sel_part.asignar_proceso(sel_proc)
            sel_proc.estado = "LISTO"
            sel_proc.t_llegada_listo = self.reloj
            self.cola_listos.append(sel_proc)

            eventos.append(
                f"Admisión {sel_proc.id_str}({sel_proc.tamano}K) → P{sel_part.id_particion}"
                f"({sel_part.tamano}K) FI: {sel_part.fragmentacion_interna} KB"
            )

        # 5) Planificación SRTF sobre la cola LISTOS.
        corto = self._encontrar_proceso_srtf()

        if self.proceso_en_ejecucion is None:
            # CPU libre → inicia el más corto.
            if corto:
                self.proceso_en_ejecucion = self.cola_listos.popleft()
                self.proceso_en_ejecucion.estado = "EJECUCION"
                if self.proceso_en_ejecucion.t_primera_ejecucion == -1:
                    self.proceso_en_ejecucion.t_primera_ejecucion = self.reloj
                eventos.append(f"SRTF: Inicia {self.proceso_en_ejecucion.id_str} (Restante: {self.proceso_en_ejecucion.t_restante})")
        else:
            # CPU ocupada → evaluar desalojo.
            run = self.proceso_en_ejecucion
            if corto and (
                (corto.t_restante < run.t_restante) or
                (corto.t_restante == run.t_restante and corto.t_llegada_listo < run.t_llegada_listo)
            ):
                # Desalojo por SRTF.
                sal = run
                sal.estado = "LISTO"
                sal.t_llegada_listo = self.reloj
                self.cola_listos.append(sal)

                # Reordenamiento de LISTOS según (t_restante, llegada_listo, id)
                self.cola_listos = deque(sorted(
                    self.cola_listos, key=lambda p: (p.t_restante, p.t_llegada_listo, p.id_proceso)
                ))

                ent = self.cola_listos.popleft()
                ent.estado = "EJECUCION"
                if ent.t_primera_ejecucion == -1:
                    ent.t_primera_ejecucion = self.reloj
                self.proceso_en_ejecucion = ent
                eventos.append(f"SRTF: Desalojo → entra {ent.id_str}")

        # 6) Vista del estado actual en consola; pausa interactiva.
        if self.reloj == 0 or eventos:
            print(f"\n============================== INSTANTE t = {self.reloj} ==============================")
            if eventos:
                print("EVENTOS: " + "; ".join(eventos))
            self._imprimir_estado_completo()
            try:
                input("PRESIONE ENTER PARA CONTINUAR...")
            except EOFError:
                pass

    # -------------------- Helpers --------------------

    def _cabe_en_alguna_particion(self, proceso: Proceso) -> bool:
        # Verifica si el proceso podría entrar en al menos una partición (por tamaño).
        for p in self.particiones:
            if not p.es_so and proceso.tamano <= p.tamano:
                return True
        return False

    def _encontrar_mejor_particion(self, proceso: Proceso, particiones: List[Particion]) -> Optional[Particion]:
        # Implementación exacta del algoritmo Best-Fit entre las particiones libres.
        mejor, menor_fi = None, float("inf")
        for part in particiones:
            if part.esta_libre and proceso.tamano <= part.tamano:
                fi = part.tamano - proceso.tamano
                if fi < menor_fi or (fi == menor_fi and (mejor is None or part.tamano < mejor.tamano)):
                    menor_fi, mejor = fi, part
        return mejor

    def _encontrar_proceso_srtf(self) -> Optional[Proceso]:
        # Selecciona el proceso con menor t_restante (tie-break: llegada a LISTO, luego ID).
        if not self.cola_listos:
            return None
        self.cola_listos = deque(sorted(
            self.cola_listos,
            key=lambda p: (p.t_restante, p.t_llegada_listo, p.id_proceso)
        ))
        return self.cola_listos[0]

    # -------------------- Impresión --------------------

    def _imprimir_estado_completo(self, final: bool = False):
        # Muestra el estado de CPU, colas y particiones, útil para depuración y visual.
        print("ESTADOS DE LOS PROCESOS:")
        if self.proceso_en_ejecucion:
            print(f"- EJECUTÁNDOSE: {self.proceso_en_ejecucion.id_str} (Restante: {self.proceso_en_ejecucion.t_restante})")
        else:
            print("- EJECUTÁNDOSE: —")
        listos_ids = [p.id_str for p in self.cola_listos] or ["—"]
        print(f"- LISTOS: {', '.join(listos_ids)}")
        ls_ids = [p.id_str for p in self.cola_listos_suspendidos] or ["—"]
        print(f"- LISTOS Y SUSPENDIDOS: {', '.join(ls_ids)}")
        if not final:
            nuevos_ids = [p.id_str for p in self.procesos_nuevos] or ["—"]
            print(f"- SIN ARRIBAR: {', '.join(nuevos_ids)}")
        term_ids = [p.id_str for p in self.procesos_terminados] or ["—"]
        print(f"- TERMINADOS: {', '.join(term_ids)}")
        print("")
        print("TABLA DE PARTICIONES:")
        print(f"{'PARTICIÓN':<10} | {'DIR':>3} | {'CONTENIDO':<20} | {'TAMAÑO':<8} | {'FI / ESTADO':<15}")
        print("-" * 70)
        for p in self.particiones:
            pid = str(p.id_particion)
            dir_str = f"{p.base}"
            tamano_str = f"{p.tamano} KB"
            if p.es_so:
                contenido = "Sistema operativo"; estado = "FI: 0 KB"
            elif p.proceso_asignado:
                pr = p.proceso_asignado
                contenido = f"{pr.id_str} ({pr.tamano} KB)"
                estado = f"FI: {p.fragmentacion_interna} KB"
            else:
                contenido = "—"; estado = "Espacio Libre"
            print(f"{pid:<10} | {dir_str:>3} | {contenido:<20} | {tamano_str:<8} | {estado:<15}")

    def _imprimir_reporte_final(self):
        # Calcula y muestra métricas de rendimiento: W, R, T y throughput.
        print("\n──────────────────────────── INFORME ESTADÍSTICO ────────────────────────────")
        print("Retorno T = fin − arribo; Espera W = T − servicio; Respuesta R = 1ªCPU − arribo.\n")
        print(f"{'PID':<4} | {'Arribo':<6} | {'1ª CPU':<6} | {'Fin':<5} | {'Servicio':<8} | {'Espera W':<8} | {'Respuesta R':<11} | {'Retorno T':<9}")
        print("-" * 79)

        total_retorno = total_espera = total_respuesta = 0
        procesos_contados = 0

        # Orden para consistencia de salida.
        self.procesos_reporte.sort(key=lambda p: p.id_proceso)

        for p in self.procesos_reporte:
            if p.t_fin != -1:
                procesos_contados += 1
                T = p.t_fin - p.t_arribo
                W = T - p.t_irrupcion
                R = p.t_primera_ejecucion - p.t_arribo
                total_retorno += T; total_espera += W; total_respuesta += R

                print(f"{p.id_str:<4} | {p.t_arribo:<6} | {p.t_primera_ejecucion:<6} | {p.t_fin:<5} | {p.t_irrupcion:<8} | {W:<8} | {R:<11} | {T:<9}")

            # Procesos nunca admitidos por tamaño.
            elif p.estado == "L/S" and not self._cabe_en_alguna_particion(p):
                print(f"{p.id_str:<4} | {p.t_arribo:<6} | {'—':<6} | {'—':<5} | {p.t_irrupcion:<8} | {'—':<8} | {'—':<11} | {'—':<9} (No admitido: {p.tamano} KB)")

        print("\nPromedios (sobre procesos terminados):")
        if procesos_contados > 0:
            print(f"- Espera promedio  = {total_espera} / {procesos_contados} = {total_espera/procesos_contados:.2f}")
            print(f"- Respuesta prom.  = {total_respuesta} / {procesos_contados} = {total_respuesta/procesos_contados:.2f}")
            print(f"- Retorno promedio = {total_retorno} / {procesos_contados} = {total_retorno/procesos_contados:.2f}")
        else:
            print("- No finalizaron procesos.")

        print("\nRendimiento (throughput):")
        if self.reloj > 0:
            print(f"- {procesos_contados} terminados / {self.reloj} t.u. = {procesos_contados/self.reloj:.3f} trabajos/t.u.")
        else:
            print("- Sin avance.")
