# Módulo de lectura y validación de CSV de procesos.
# Expone leer_csv_procesos(path) que devuelve (lista_de_Proceso, mensaje_de_error).
import csv
import sys
import unicodedata
from typing import List, Tuple, Iterable

from simulador_motor import Proceso  # Clase de dominio usada para instanciar procesos.

def _norm(s: str) -> str:
    # Normaliza una cadena para comparar encabezados:
    # - quita espacios
    # - elimina acentos
    # - reemplaza ñ/Ñ por n/N
    # - convierte a mayúsculas
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.replace("ñ", "n").replace("Ñ", "N").upper()

def _parsear_csv_data(raw: List[List[str]]) -> Tuple[List[Proceso], str]:
    # Recibe todas las filas crudas del CSV y:
    # - detecta encabezados o datos
    # - identifica columnas ID, tamaño, TA, TI
    # - valida filas
    # - construye objetos Proceso válidos
    # Devuelve (lista_procesos_validos, mensaje_de_error/advertencia).
    procs: List[Proceso] = []
    ids_vistos = set()
    errores = []
    
    if not raw:
        # Archivo vacío: no hay nada que parsear.
        return [], "Archivo CSV vacío."

    first = raw[0]

    def is_int(x):
        # Determina si un valor puede convertirse a entero.
        try:
            int(str(x).strip())
            return True
        except:
            return False

    # Heurística: si la primera fila tiene al menos 4 columnas enteras,
    # se interpreta como fila de datos (sin encabezado).
    first_is_data = len(first) >= 4 and all(is_int(c) for c in first[:4])

    id_idx = tam_idx = ta_idx = ti_idx = None

    # Determinación de índices de columnas (por posición o por nombre).
    if first_is_data:
        # No hay encabezado, se asume orden fijo: ID, TAM, TA, TI.
        data_rows = raw
        id_idx, tam_idx, ta_idx, ti_idx = 0, 1, 2, 3
        start_line = 1
    else:
        # Hay encabezado: se normalizan nombres para admitir sinónimos.
        headers = [_norm(h) for h in first]
        # Conjuntos de nombres aceptados para cada campo.
        IDN   = {"ID", "IDP", "PID"}
        TAMN  = {"TAMANO", "TAMANIO", "TAM", "SIZE", "TAMM"}
        TAN   = {"TA", "ARRIBO", "LLEGADA"}
        TIN   = {"TI", "IRRUPCION", "IRRUPCIONCPU", "BURST", "CPU", "SERVICIO", "DURACION"}

        # Se busca cada encabezado en los conjuntos anteriores.
        for i, h in enumerate(headers):
            if id_idx is None and h in IDN:
                id_idx = i
            elif tam_idx is None and h in TAMN:
                tam_idx = i
            elif ta_idx is None and h in TAN:
                ta_idx = i
            elif ti_idx is None and h in TIN:
                ti_idx = i
        
        # Si no se pudieron mapear bien pero hay al menos 4 columnas,
        # se recurre al orden por defecto (primera fila como encabezado).
        if None in (id_idx, tam_idx, ta_idx, ti_idx) and len(first) >= 4:
            id_idx, tam_idx, ta_idx, ti_idx = 0, 1, 2, 3
            
        data_rows = raw[1:]
        start_line = 2

    # Recorre filas de datos y aplica validaciones de formato y dominio.
    for off, row in enumerate(data_rows, start=start_line):
        def get(i):
            # Obtiene el valor de la columna i de forma segura.
            # Devuelve cadena vacía si el índice es inválido.
            try:
                return "" if i is None or i >= len(row) else str(row[i]).strip()
            except:
                return ""

        sid, stam, sta, sti = get(id_idx), get(tam_idx), get(ta_idx), get(ti_idx)

        # Si la fila es completamente vacía, se ignora (permite espacios de separación).
        if not any([sid, stam, sta, sti]):
            continue

        try:
            # Parseo a enteros de los campos básicos del proceso.
            pid = int(sid)
            tam = int(stam)
            ta = int(sta)
            ti = int(sti)
        except Exception:
            errores.append(f"ERROR fila {off}: valores no son enteros — fila ignorada.")
            continue

        # Validaciones de dominio sobre los datos del proceso.
        motivos = []
        if pid <= 0:
            motivos.append("ID debe ser positivo")
        if pid in ids_vistos:
            motivos.append("ID duplicado")
        if tam <= 0:
            motivos.append("TAMANO debe ser > 0")
        if ta < 0:
            motivos.append("TA no puede ser negativo")
        if ti <= 0:
            motivos.append("TI debe ser > 0")

        # Si existen problemas, se descarta la fila y se registra el motivo.
        if motivos:
            errores.append(f"ERROR fila {off} (ID={pid}): " + "; ".join(motivos) + " — fila ignorada.")
            continue

        # Fila válida: se registra el ID y se crea el Proceso de dominio.
        ids_vistos.add(pid)
        procs.append(Proceso(pid, tam, ta, ti))
    
    # Si hubo errores, se devuelve la lista de procesos válidos + texto con advertencias.
    if errores:
        return procs, "Se cargaron procesos, pero se encontraron errores:\n\n" + "\n".join(errores)
    
    # Caso ideal: todos los registros incluidos sin advertencias.
    return procs, "" 

def leer_csv_procesos(path: str) -> Tuple[List[Proceso], str]:
    # Función pública de alto nivel.
    # Abre el archivo CSV (ruta local), lo lee en memoria y delega el parseo
    # a _parsear_csv_data. Devuelve:
    #   (lista_de_Proceso, mensaje_de_error/advertencia).
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            raw = list(csv.reader(f))
    except FileNotFoundError:
        # No se encontró el archivo en la ruta indicada.
        return [], f"Error: No se encontró el archivo en la ruta: {path}"
    except Exception as e:
        # Error general de lectura: archivo no accesible o no es un CSV válido.
        return [], f"ERROR: No se pudo leer el archivo. ¿Es un CSV válido? ({e})"
    
    # Se invoca el parser interno con todas las filas leídas.
    return _parsear_csv_data(raw)
