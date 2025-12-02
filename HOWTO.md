# Guía de Uso del Simulador de Planificación y Gestión de Memoria 

## Descripción

Este software es un simulador de Sistema Operativo con Interfaz Gráfica (GUI) diseñado para demostrar visualmente la gestión de procesos y memoria.
Implementa:

* Planificación de CPU **SRTF** (Shortest Remaining Time First) **apropiativo** (con desalojo).
* Gestión de memoria con **Particiones Fijas** y política de asignación **Best-Fit**.

El simulador incorpora además:

* Lógica de **Intercambio (Swapping)**.
* Control estricto del **Grado de Multiprogramación global** y del **grado de multiprogramación en memoria**.


## Requisitos del Sistema

* **Sistema Operativo:** Windows, Linux o macOS.
* **Python:** Versión 3.x instalada.
* **Librerías externas:** `Pillow` (para iconos e imágenes).


## Instalación y Dependencias

El simulador utiliza:

* `tkinter` (incluido por defecto en Python) para la GUI.
* `Pillow` para el manejo de iconos.

Pasos:

1. Abrir terminal o consola.
2. Ejecutar:

   ```bash
   pip install Pillow
   ```

Si `pip` no se reconoce, revisar que en la instalación de Python se haya marcado **“Add Python to PATH”**.


## Ejecución del Simulador

1. Navegar a la carpeta del proyecto en la terminal.
2. Ejecutar:

   ```bash
   python gui.py
   ```

> [!NOTE]
> No ejecutar `simulador_motor.py` ni `lector_csv.py` directamente.
> El punto de entrada de la aplicación es **`gui.py`**.


## Preparación del Archivo CSV

El simulador toma como entrada un archivo `.csv` (valores separados por coma) que describe los procesos.

### Campos requeridos

| Campo      | Descripción                                                | Ejemplo |
| ---------- | ---------------------------------------------------------- | ------- |
| **ID**     | Identificador único del proceso (entero positivo).         | 1       |
| **TAMANO** | Tamaño del proceso en KB (máx. ~250 KB para ser admitido). | 200     |
| **TA**     | Tiempo de arribo al sistema.                               | 0       |
| **TI**     | Tiempo total de irrupción de CPU (burst total de CPU).     | 5       |

> [!NOTE]
> `TI` es el **tiempo total de CPU** del proceso.
> El simulador mantiene internamente un campo `t_restante` y lo actualiza en cada Tick; **no** se carga `t_restante` en el CSV.

### Ejemplo de archivo (`procesos.csv`)

```csv
ID,TAMANO,TA,TI
1,200,0,5
2,50,0,3
5,300,2,6
9,50,6,3
```

### Nombres de columnas aceptados

El lector de CSV es flexible con los encabezados (ignora mayúsculas, acentos y espacios). Ejemplos válidos:

* **ID:** `ID`, `IDP`, `PID`
* **TAMANO:** `TAMANO`, `TAMANIO`, `TAM`, `SIZE`, `TAMM`
* **TA:** `TA`, `ARRIBO`, `LLEGADA`
* **TI:** `TI`, `IRRUPCION`, `IRRUPCIONCPU`, `BURST`, `CPU`, `SERVICIO`, `DURACION`

Si no se detecta encabezado válido pero hay al menos 4 columnas, se asume orden fijo: `ID, TAMANO, TA, TI`.


## Flujo de Uso e Interfaz

### 1. Carga de datos

Al iniciar la aplicación, no hay simulación cargada.

1. Presionar el botón **“Cargar CSV”** en la barra superior.

2. Se abre una ventana modal con dos opciones:

   * **Opción 1 – Ruta manual:** escribir o pegar la ruta (por ejemplo `C:\TP_Sistemas\lote1.csv`).
   * **Opción 2 – Explorador:** usar **“Buscar Archivo Local…”** y seleccionar el archivo desde el sistema de archivos.

3. Si el archivo es válido, se cargan los procesos y el sistema queda preparado en `t = 0`.

### 2. Control de la simulación (paso a paso)

No hay corridas automáticas; el avance es manual:

* **Botón “Tick”:**

  * Avanza el reloj del simulador en **1 unidad de tiempo**.
  * Dispara todos los eventos de ese instante: arribos, admisiones, swaps, desalojos, finalizaciones, etc.
* **Botón “Reiniciar”:**

  * Detiene la simulación actual.
  * Limpia colas, tablas, memoria y vuelve el reloj a `0`.
  * Deja el simulador listo para cargar otro CSV o recargar el mismo.

### 3. Visualización en tiempo real

La interfaz se organiza en paneles, actualizados en cada Tick:

* **Panel izquierdo – Colas de procesos:**

  * **Ejecutando:** proceso que tiene la CPU en el instante actual.
  * **Listos:** procesos en memoria, preparados para ejecutar.
  * **Listos y Suspendidos (L/S):** procesos que ya entraron al sistema pero no tienen partición asignada (en swap o en espera de Best-Fit).
  * **Sin Arribar:** procesos cuyo tiempo de arribo aún no se cumple o que no pudieron ingresar por **GDM lleno**.
  * **Terminados:** procesos completados.

* **Consola de eventos:**
  Lista textual que describe qué pasó en el instante actual, por ejemplo:

  * `Arriban P1, P2`
  * `Admisión P3(50K) → P2(150K) FI: 100 KB`
  * `Swap: Sale P4(R:8) ↔ Entra P5(R:2) en P1`

* **Panel inferior – Tabla de particiones:**
  Representación de la memoria física:

  * Muestra **ID de partición**, **dirección base**, **tamaño**, **contenido** (SO, proceso o libre) y **fragmentación interna (FI)**.

* **Panel central – Consola de estado (tabla de procesos):**

  * Una fila por cada proceso: ID, TA, TI, tamaño de memoria, estado y porcentaje de ejecución.
  * Debajo, se muestran los promedios y el rendimiento (throughput) luego de que la simulación llega al final.
  * Adicionalmente, al finalizar, se abre una ventana con la tabla detallada por proceso (arribo, 1ª CPU, fin, servicio, W, R, T).


## Políticas y Reglas de Negocio Implementadas

### A. Estructura de memoria (particiones fijas)

Se simula una memoria total de **550 KB** con el siguiente esquema:

| Partición | Base | Tamaño | Uso típico                    |
| :-------: | :--: | :----: | ----------------------------- |
|   **0**   |   0  | 100 KB | Sistema Operativo (reservada) |
|   **1**   |  100 | 250 KB | Procesos grandes              |
|   **2**   |  350 | 150 KB | Procesos medianos             |
|   **3**   |  500 |  50 KB | Procesos pequeños             |

> [!IMPORTANT]
> Un proceso solo puede ubicarse en particiones de usuario (1, 2 o 3).
> Si su tamaño es **mayor a 250 KB**, nunca podrá ser admitido en memoria: será tratado como “no admitido” aunque entre al sistema.

### B. Límite de memoria (grado de multiprogramación en memoria)

Restricción sobre memoria principal:

* Máximo **3 procesos de usuario** cargados simultáneamente en memoria:

  * 1 en **Ejecución**
  * Hasta 2 en **Listos**

Aunque haya particiones libres, si ya hay 3 procesos en memoria, no se admite un cuarto proceso por este criterio.

### C. Grado de multiprogramación global (GDM)

Se controla cuántos procesos están **dentro del sistema**:

* **GDM máximo: 5 procesos activos**.
* Activos = procesos en:

  * **Ejecutando**
  * **Listos**
  * **Listos y Suspendidos (L/S)**

Si el GDM alcanza 5:

* Los procesos cuyo TA se cumple no pasan a L/S; quedan etiquetados en la GUI como **“Sin Arribar”** hasta que se libere un cupo en el sistema.

### D. Intercambio (Swapping)

El Swapping se aplica cuando:

1. La **memoria está llena** bajo el criterio de 3 procesos en memoria.
2. Llega a L/S un proceso que **cabe** en alguna partición actualmente ocupada (por tamaño).
3. Ese proceso tiene **menor tiempo restante (`t_restante`)** que al menos uno de los procesos residentes en memoria.

Reglas:

* Se define un conjunto de posibles víctimas: procesos en memoria (CPU + Listos) cuyo tamaño cabe en la partición que podría usar el nuevo proceso.
* La **víctima** es el proceso con **mayor `t_restante`** (SRTF inverso).
* Acción:

  * Víctima → se pasa a **L/S** y se libera su partición.
  * Candidato → se carga en la partición liberada y pasa a **Listo**.

> [!IMPORTANT]
> Si el proceso no cabe en ninguna partición de usuario, **no habrá swap posible**.
> Swapping no “salta” la limitación física de las particiones.

### E. Planificación de CPU (SRTF)

* Política: **Shortest Remaining Time First** con desalojo.

* Criterios:

  1. **Primario:** menor `t_restante`.
  2. Desempate 1: menor tiempo de llegada a la cola de **Listos**.
  3. Desempate 2: menor ID de proceso.

* Desalojo:

  * Si un proceso entra a **Listos** (por admisión o swap) con menor `t_restante` que el proceso en ejecución, entonces se produce desalojo inmediato.
  * El proceso desalojado vuelve a la cola de Listos.


## Interpretación de Métricas Finales

Al finalizar la simulación se muestra, por proceso:

* **Arribo:** tiempo en que entra al sistema (`TA`).
* **1ª CPU:** primer instante en que toma la CPU.
* **Fin:** instante en que finaliza.
* **Servicio:** tiempo total de CPU (`TI`).
* **Espera W**, **Respuesta R** y **Retorno T**:

Fórmulas:

* **Retorno T:**
  T = fin - arribo
  
* **Espera W:**
  W = T - servicio

* **Respuesta R:**
  R = 1ª CPU - arribo

Ejemplo breve:

* Proceso P3:

  * Arribo = 2
  * 1ª CPU = 5
  * Fin = 12
  * Servicio (TI) = 4
* Entonces:

  * ( T = 12 - 2 = 10 )
  * ( W = 10 - 4 = 6 )
  * ( R = 5 - 2 = 3 )

Promedios:

* El simulador calcula y muestra:

  * Espera promedio
  * Respuesta promedio
  * Retorno promedio
* Y el **throughput** (rendimiento):
  Throughput = (procesos terminados) / (tiempo total de simulación)


## Diferencia entre “Nuevos” y “Listos y Suspendidos (L/S)”

Conceptualmente:

* **Nuevos:**

  * Procesos **que todavía no ingresaron al sistema**.
  * Motivos:

    * Aún no llegó su `TA`, o
    * Su `TA` llegó, pero el **GDM = 5** está completo y no pueden pasar a L/S.

* **Listos y Suspendidos (L/S):**

  * Procesos **que ya ingresaron al sistema** (cuentan para GDM) pero **no tienen memoria asignada**.
  * Casos:

    * Llegaron al sistema pero no hay partición disponible.
    * Fueron víctimas de **Swap Out** y esperan ser readmitidos.

## Limitaciones Conocidas

1. Se simulan hasta **10 procesos** por lote (se toman los primeros 10 ordenados por TA e ID).
2. Procesos con tamaño **> 250 KB** nunca serán admitidos en memoria: pueden aparecer en L/S como “no admitidos”.
3. Seguridad: si el reloj supera las **500 t.u.**, la simulación se detiene automáticamente.


## Solución de Problemas Frecuentes

### Error: `ModuleNotFoundError: No module named 'PIL'`

* Falta la librería `Pillow`.
* Solución:

  ```bash
  pip install Pillow
  ```

### Error al cargar CSV: “Valores no enteros” o “Estructura incorrecta”

* Revisar:

  * Que el archivo sea realmente `.csv` con separador coma (`,`).
  * Que no haya filas vacías al final.
  * Que las columnas estén en alguno de los formatos aceptados (ver sección de encabezados).

### Un proceso queda en “Sin Arribar” aunque ya pasó su TA

* Situación típica de **GDM lleno**:

  * Si ya hay 5 procesos activos (en memoria o en L/S), el proceso no puede entrar al sistema.
  * Una vez que finalice o salga alguno, el proceso pendiente será admitido automáticamente y dejará de aparecer como “Sin Arribar”.

