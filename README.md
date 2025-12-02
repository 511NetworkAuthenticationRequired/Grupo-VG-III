# Simulador de Planificación y Gestión de Memoria  

Desarrollado como proyecto académico para la cátedra de Sistemas Operativos.  
Este simulador visual implementa los componentes fundamentales de un sistema operativo moderno: **planificación de procesos**, **gestión de memoria**, **swapping**, y **control del grado de multiprogramación**, todo representado mediante una interfaz gráfica paso a paso.


<p align="center">
 <img width="592" height="288" alt="logos vg iii" src="https://github.com/user-attachments/assets/ee50bb86-31c0-4bde-9a0d-02c16c360567" />
</p>


El simulador permite cargar procesos desde un archivo CSV y ejecutar, paso a paso:
- **Planificación SRTF (Shortest Remaining Time First)** con desalojo.  
- **Administración de memoria por Particiones Fijas (MFT)**.  
- **Best-Fit** como política de selección de partición.  
- **Swap** automático cuando la memoria está completa.  
- Control del **grado de multiprogramación**.  

El estado completo del sistema se visualiza en tiempo real: colas, particiones, eventos del tick, progreso por proceso y métricas finales.

---

## Funcionalidades

- Planificación **SRTF** con desalojo inmediato.  
- Administración de memoria **Best-Fit** con particiones fijas.  
- Manejo de **swap** y control del grado de multiprogramación.  
- Panel con procesos en: Nuevos, L/S, Listos, Ejecutando y Terminados.  
- Visualización de particiones y fragmentación interna.  
- Consola de eventos por tick.  
- Tabla dinámica con progreso de cada proceso.  
- Cálculo automático de **T**, **W**, **R** y **Throughput**.  
- Lectura flexible de CSV con encabezados variables.
