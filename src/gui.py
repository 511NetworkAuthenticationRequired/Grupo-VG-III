import tkinter as tk
from tkinter import ttk, filedialog, messagebox, PanedWindow
from typing import Optional, List
from PIL import Image, ImageTk 
import os 

from simulador_motor import Simulador, Proceso
from lector_csv import leer_csv_procesos

class CargarCsvDialog(tk.Toplevel):
    # Ventana modal para elegir cómo se cargará el CSV (ruta escrita o explorador).
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cargar Procesos")
        
        # Guarda el resultado de la interacción:
        #   {"tipo": "ruta"/"explorador", "valor": <str>} o None si se cancela.
        self.resultado: Optional[dict] = None 
        
        # Hace la ventana modal respecto de la ventana principal.
        self.transient(parent)
        self.grab_set()

        # Configuración visual base.
        COLOR_FONDO = '#111827'
        self.config(bg=COLOR_FONDO)

        # --- Opción 1: Ingresar la ruta completa del archivo manualmente ---
        frame_url = ttk.LabelFrame(self, text="Opción 1: Escribir Ruta Local", padding=10)
        frame_url.pack(fill=tk.X, padx=10, pady=5)
        
        self.url_var = tk.StringVar()
        entry_url = ttk.Entry(frame_url, textvariable=self.url_var, width=50)
        entry_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_url = ttk.Button(frame_url, text="Cargar", command=self._cargar_ruta)
        btn_url.pack(side=tk.LEFT)

        # --- Opción 2: Usar el explorador de archivos del sistema ---
        frame_archivo = ttk.LabelFrame(self, text="Opción 2: Cargar desde Archivo Local", padding=10)
        frame_archivo.pack(fill=tk.X, padx=10, pady=5)
        
        btn_archivo = ttk.Button(frame_archivo, text="Buscar Archivo Local...", command=self._cargar_explorador)
        btn_archivo.pack(fill=tk.X)
        
        # Manejo del cierre con la "X" de la ventana.
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        entry_url.focus()

    def _cargar_ruta(self):
        # Toma la ruta escrita, valida formato y la devuelve al llamador.
        ruta = self.url_var.get().strip().strip('"') 
        
        # Validación de ruta no vacía.
        if not ruta:
            messagebox.showerror("Error", "La ruta no puede estar vacía.", parent=self)
            return
        
        # Valida extensión CSV.
        if not ruta.lower().endswith(".csv"):
            messagebox.showerror("Error", "La ruta debe ser un archivo .csv", parent=self)
            return

        # Guarda el tipo de decisión y cierra el diálogo.
        self.resultado = {"tipo": "ruta", "valor": ruta}
        self.destroy()

    def _cargar_explorador(self):
        # Indica que se usará el explorador de archivos en la ventana principal.
        self.resultado = {"tipo": "explorador"}
        self.destroy()

    def _cancelar(self):
        # Cierra el diálogo sin selección de archivo (operación cancelada).
        self.resultado = None
        self.destroy()

class App:
    # Ventana principal de la aplicación GUI del simulador SRTF + Best-Fit.
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simulador de Planificación y Memoria (SRTF + Best-Fit)")
        self.root.geometry("1100x780")
        self.root.resizable(True, True)

        # Motor de simulación y cantidad total de procesos cargados.
        self.simulador: Optional[Simulador] = None
        self.total_procesos: int = 0

        # Estilos visuales (tema oscuro y colores).
        self.configurar_estilo_moderno()

        # Diccionario para mantener referencias a los iconos (evita que se liberen).
        self.iconos_referencia = {} 
        
        # Construye toda la interfaz.
        self.crear_widgets()

    def configurar_estilo_moderno(self):
        # Define y aplica un tema oscuro personalizado para ttk y widgets Tk.
        style = ttk.Style()
        style.theme_use("clam")

        # Paleta de colores principal.
        COLOR_FONDO = '#111827'
        COLOR_FONDO_ALT = '#1F2933'
        COLOR_CONTENT_BG = '#13111C'
        COLOR_PANEL = '#111827'
        COLOR_BORDE = '#4B5563'
        COLOR_TEXTO = '#F9FAFB'
        COLOR_TEXTO_SUAVE = '#E5E7EB'
        COLOR_ACCENTO = '#EC4899' # Rosa principal.
        COLOR_ACCENTO_SEC = '#F472B6'

        # Fuentes principales.
        self.FONT_NORMAL = ("Segoe UI", 9)
        self.FONT_NORMAL_SMALL = ("Segoe UI", 8)
        self.FONT_BOLD = ("Segoe UI", 9, "bold")
        self.FONT_TITLE = ("Georgia", 11, "bold")

        self.root.config(bg=COLOR_FONDO)

        # Estilo para frames y labelframes.
        style.configure("TFrame", background=COLOR_FONDO)
        style.configure("TLabelframe",
                        background=COLOR_PANEL,
                        bordercolor=COLOR_ACCENTO,
                        relief="groove")
        style.configure("TLabelframe.Label",
                        background=COLOR_PANEL,
                        foreground=COLOR_TEXTO,
                        font=self.FONT_TITLE)
        
        # Estilo general de etiquetas.
        style.configure("TLabel",
                        background=COLOR_PANEL,
                        foreground=COLOR_TEXTO,
                        font=self.FONT_NORMAL)

        # Botones de la barra de herramientas (secundarios).
        style.configure("ToolButton.TButton",
                        background="#020617",
                        foreground=COLOR_TEXTO,
                        font=self.FONT_NORMAL_SMALL,
                        padding=(4, 4),
                        bordercolor=COLOR_ACCENTO)
        style.map("ToolButton.TButton",
                  background=[('active', '#111827')],
                  foreground=[('disabled', COLOR_TEXTO_SUAVE)])

        # Botón principal (Cargar CSV).
        style.configure("Primary.TButton",
                        background="#020617",
                        foreground=COLOR_TEXTO,
                        font=("Segoe UI Semibold", 10),
                        padding=(10, 8),
                        borderwidth=2,
                        bordercolor=COLOR_ACCENTO)
        style.map("Primary.TButton",
                  background=[('active', '#020617'),
                              ('disabled', '#020617')],
                  foreground=[('disabled', '#e5e7eb')])

        # Estilo genérico para el resto de botones ttk.
        style.configure("TButton",
                        background="#020617",
                        foreground=COLOR_TEXTO,
                        font=self.FONT_NORMAL,
                        padding=(6, 4),
                        bordercolor=COLOR_ACCENTO)
        style.map("TButton",
                  background=[('active', '#111827')],
                  foreground=[('disabled', COLOR_TEXTO_SUAVE)])

        # Estilo para la tabla Treeview.
        style.configure("Treeview",
                        background=COLOR_CONTENT_BG,
                        foreground=COLOR_TEXTO,
                        fieldbackground=COLOR_CONTENT_BG,
                        font=self.FONT_NORMAL,
                        bordercolor=COLOR_BORDE)
        style.configure("Treeview.Heading",
                        background=COLOR_FONDO_ALT,
                        foreground=COLOR_TEXTO,
                        font=self.FONT_BOLD,
                        relief="flat",
                        bordercolor=COLOR_ACCENTO)
        style.map("Treeview.Heading",
                  background=[('active', COLOR_FONDO)],
                  foreground=[('disabled', COLOR_TEXTO_SUAVE)])

        # Scrollbar vertical moderno.
        style.configure("Vertical.TScrollbar",
                        gripcount=0,
                        background=COLOR_FONDO_ALT,
                        darkcolor=COLOR_FONDO_ALT,
                        lightcolor=COLOR_FONDO_ALT,
                        troughcolor=COLOR_CONTENT_BG,
                        bordercolor=COLOR_BORDE,
                        arrowcolor=COLOR_TEXTO)

        # Barra de progreso horizontal (para avance global de procesos).
        style.configure("Modern.Horizontal.TProgressbar",
                        troughcolor=COLOR_CONTENT_BG,
                        background=COLOR_ACCENTO_SEC,
                        bordercolor=COLOR_BORDE)

        # Guarda colores para usarlos con widgets Tk "puros".
        self.COLOR_CONTENT_BG = COLOR_CONTENT_BG
        self.COLOR_FONDO = COLOR_FONDO
        self.COLOR_FONDO_ALT = COLOR_FONDO_ALT
        self.COLOR_TEXTO = COLOR_TEXTO
        self.COLOR_TEXTO_SUAVE = COLOR_TEXTO_SUAVE
        self.COLOR_ACCENTO = COLOR_ACCENTO
        self.COLOR_ACCENTO_SEC = COLOR_ACCENTO_SEC


    def cargar_iconos(self):
        # Carga los iconos PNG asociados a la barra de herramientas.
        icon_map = {
            "Cargar": "cargar.png",
            "Tick": "tick.png",
            "Completo": "completo.png",
            "Reiniciar": "reiniciar.png"
        }

        ICON_SIZE = (24, 24)
        base_dir = os.path.dirname(__file__)
        icon_dir = os.path.join(base_dir, "iconos")

        for name, filename in icon_map.items():
            file_path = os.path.join(icon_dir, filename)
            try:
                # Usa PIL para abrir, redimensionar y convertir a PhotoImage.
                icon_ref = Image.open(file_path)
                icon_ref = icon_ref.resize(ICON_SIZE, Image.Resampling.LANCZOS)
                self.iconos_referencia[name] = ImageTk.PhotoImage(icon_ref)
            except Exception:
                # Si falla la carga, usa un cuadrado gris como marcador de posición.
                dummy_img = Image.new('RGB', ICON_SIZE, color='lightgray')
                self.iconos_referencia[name] = ImageTk.PhotoImage(dummy_img)


    def crear_widgets(self):
        # Construye y dispone todos los contenedores y widgets de la GUI.
        
        self.cargar_iconos()
        
        # --- Barra superior de herramientas (carga, avance de tick, reinicio) ---
        toolbar = tk.Frame(self.root,
                           bd=0,
                           relief=tk.FLAT,
                           bg=self.COLOR_FONDO_ALT,
                           padx=10,
                           pady=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Botón "Cargar CSV" (habilita la simulación).
        self.btn_toolbar_cargar = ttk.Button(
            toolbar,
            text="Cargar CSV",
            image=self.iconos_referencia["Cargar"],
            compound=tk.LEFT,
            command=self.cargar_csv,
            style="Primary.TButton"
        )
        self.btn_toolbar_cargar.pack(side=tk.LEFT, padx=(0, 12))

        # Botón "Tick" para avanzar un paso en el simulador.
        self.btn_toolbar_tick = ttk.Button(
            toolbar,
            text="Tick",
            image=self.iconos_referencia["Tick"],
            compound=tk.LEFT,
            command=self.siguiente_tick,
            state=tk.DISABLED,
            style="ToolButton.TButton"
        )
        self.btn_toolbar_tick.pack(side=tk.LEFT, padx=4)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Botón para reiniciar completamente la simulación y la interfaz.
        self.btn_toolbar_reset = ttk.Button(
            toolbar,
            text="Reiniciar",
            image=self.iconos_referencia["Reiniciar"],
            compound=tk.LEFT,
            command=self.reset_simulador,
            style="ToolButton.TButton"
        )
        self.btn_toolbar_reset.pack(side=tk.LEFT, padx=4)

        # Expansor para empujar el reloj y la barra de progreso a la derecha.
        tk.Frame(toolbar, bg=self.COLOR_FONDO_ALT).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- Progreso global y reloj de simulación ---
        self.progress_var = tk.DoubleVar(value=0.0)
        progress_container = tk.Frame(toolbar, bg=self.COLOR_FONDO_ALT)
        progress_container.pack(side=tk.RIGHT)

        ttk.Label(
            progress_container,
            text="Progreso procesos",
            style="TLabel"
        ).pack(side=tk.TOP, anchor=tk.E)

        self.progressbar = ttk.Progressbar(
            progress_container,
            orient=tk.HORIZONTAL,
            mode="determinate",
            variable=self.progress_var,
            length=220,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progressbar.pack(side=tk.BOTTOM, pady=(2, 0))

        # Etiqueta que muestra el "tiempo de reloj" del simulador.
        self.lbl_reloj_var = tk.StringVar(value="Reloj: 0")
        ttk.Label(toolbar,
                  textvariable=self.lbl_reloj_var,
                  font=("Segoe UI Semibold", 10),
                  background=self.COLOR_FONDO_ALT,
                  foreground=self.COLOR_TEXTO).pack(side=tk.RIGHT, padx=(0, 16))


        # --- Paneles principales (superior: colas+procesos, inferior: memoria) ---
        main_panes = PanedWindow(self.root,
                                 orient=tk.VERTICAL,
                                 sashrelief=tk.RAISED,
                                 bg=self.COLOR_FONDO)
        main_panes.pack(fill=tk.BOTH, expand=True)

        top_panes = PanedWindow(main_panes,
                                orient=tk.HORIZONTAL,
                                sashrelief=tk.RAISED,
                                bg=self.COLOR_FONDO)
        main_panes.add(top_panes, height=500) 

        # ===================== PANEL IZQUIERDO =====================
        # Muestra colas de procesos y la lista de eventos del instante actual.
        frame_izquierda = ttk.LabelFrame(top_panes, text="Colas de Procesos y Eventos", padding="10")
        top_panes.add(frame_izquierda, width=400)
        colas_frame = ttk.Frame(frame_izquierda, padding="0 5")
        colas_frame.pack(fill=tk.X)
        
        # Proceso actualmente en CPU.
        ttk.Label(colas_frame, text="Ejecutando:", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(5, 0))
        self.lbl_ejecutando_var = tk.StringVar(value="—")
        tk.Label(
            colas_frame,
            textvariable=self.lbl_ejecutando_var,
            bg=self.COLOR_CONTENT_BG,
            fg='#22C55E',
            font=self.FONT_BOLD,
            relief=tk.SUNKEN,
            padx=5,
            pady=4,
            anchor=tk.W
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 5))

        # Cola de listos.
        ttk.Label(colas_frame, text="Listos:", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(5, 0))
        self.lbl_listos_var = tk.StringVar(value="—")
        tk.Label(
            colas_frame,
            textvariable=self.lbl_listos_var,
            bg=self.COLOR_CONTENT_BG,
            fg=self.COLOR_TEXTO,
            font=self.FONT_NORMAL,
            relief=tk.SUNKEN,
            padx=5,
            pady=2,
            anchor=tk.W
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        # Listos suspendidos (en swap).
        ttk.Label(colas_frame, text="Listos y Suspendidos:", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(5, 0))
        self.lbl_ls_var = tk.StringVar(value="—")
        tk.Label(
            colas_frame,
            textvariable=self.lbl_ls_var,
            bg=self.COLOR_CONTENT_BG,
            fg=self.COLOR_TEXTO_SUAVE,
            font=self.FONT_NORMAL,
            relief=tk.SUNKEN,
            padx=5,
            pady=2,
            anchor=tk.W
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        # Procesos que aún no arribaron.
        ttk.Label(colas_frame, text="Sin Arribar (Nuevos):", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(5, 0))
        self.lbl_nuevos_var = tk.StringVar(value="—")
        tk.Label(
            colas_frame,
            textvariable=self.lbl_nuevos_var,
            bg=self.COLOR_CONTENT_BG,
            fg=self.COLOR_TEXTO,
            font=self.FONT_NORMAL,
            relief=tk.SUNKEN,
            padx=5,
            pady=2,
            anchor=tk.W
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        # Procesos terminados.
        ttk.Label(colas_frame, text="Terminados:", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(5, 0))
        self.lbl_terminados_var = tk.StringVar(value="—")
        tk.Label(
            colas_frame,
            textvariable=self.lbl_terminados_var,
            bg=self.COLOR_CONTENT_BG,
            fg=self.COLOR_ACCENTO if hasattr(self, "COLOR_ACCENTO") else "#22C55E",
            font=self.FONT_NORMAL,
            relief=tk.SUNKEN,
            padx=5,
            pady=2,
            anchor=tk.W
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        
        # Lista de eventos que ocurrieron en el último tick.
        ttk.Label(frame_izquierda, text="Eventos del Instante:", font=self.FONT_BOLD).pack(anchor=tk.W, pady=(10, 0))
        scrollbar_eventos = ttk.Scrollbar(frame_izquierda, orient=tk.VERTICAL)
        self.list_eventos = tk.Listbox(frame_izquierda, 
                                       height=10, 
                                       yscrollcommand=scrollbar_eventos.set,
                                       bg=self.COLOR_CONTENT_BG, 
                                       fg=self.COLOR_TEXTO, 
                                       font=self.FONT_NORMAL, 
                                       relief=tk.SUNKEN, 
                                       bd=2,
                                       highlightthickness=0)
        scrollbar_eventos.config(command=self.list_eventos.yview)
        
        scrollbar_eventos.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_eventos.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        
        # ===================== PANEL CENTRAL (CONSOLa) =====================
        # Tabla de procesos + estado general + métricas finales.
        frame_consola = ttk.LabelFrame(top_panes, text="Consola de Estado (Tabla de Procesos)", padding="5")
        top_panes.add(frame_consola, width=600)

        # Treeview que muestra una fila por proceso con datos y progreso.
        cols_consola = ("pid", "ta", "ti", "mem", "estado", "barra", "progreso")
        self.tree_consola = ttk.Treeview(frame_consola, columns=cols_consola, show="headings", height=6)
        
        # Configuración de encabezados y columnas.
        self.tree_consola.heading("pid", text="PID"); self.tree_consola.column("pid", width=50, anchor=tk.CENTER)
        self.tree_consola.heading("ta", text="TA"); self.tree_consola.column("ta", width=60, anchor=tk.E)
        self.tree_consola.heading("ti", text="TI"); self.tree_consola.column("ti", width=60, anchor=tk.E)
        self.tree_consola.heading("mem", text="Mem (kB)"); self.tree_consola.column("mem", width=80, anchor=tk.E)
        self.tree_consola.heading("estado", text="Estado"); self.tree_consola.column("estado", width=120, anchor=tk.W)
        self.tree_consola.heading("barra", text="Progreso"); self.tree_consola.column("barra", width=150, anchor=tk.W)
        self.tree_consola.heading("progreso", text="%"); self.tree_consola.column("progreso", width=60, anchor=tk.E)

        # Tags de color según el estado del proceso.
        self.tree_consola.tag_configure("estado_Ejecutando", foreground="#38BDF8")
        self.tree_consola.tag_configure("estado_Listo", foreground=self.COLOR_TEXTO)
        self.tree_consola.tag_configure("estado_ListoSuspendido", foreground="#FBBF24")
        self.tree_consola.tag_configure("estado_Terminado", foreground="#22C55E")
        self.tree_consola.tag_configure("estado_Nuevo", foreground=self.COLOR_TEXTO_SUAVE)
        
        self.tree_consola.pack(fill=tk.BOTH, expand=True)
        
        # Mensaje de estado general de la consola (pie de tabla).
        self.lbl_consola_status_var = tk.StringVar(value="Listo. Cargue un archivo CSV para comenzar.")
        
        tk.Label(frame_consola,
                 textvariable=self.lbl_consola_status_var, 
                 bg=self.COLOR_CONTENT_BG,
                 fg=self.COLOR_TEXTO_SUAVE,
                 relief=tk.SUNKEN,
                 anchor=tk.W,
                 font=self.FONT_NORMAL).pack(fill=tk.X, pady=(5, 0))

        # Contenedor para métricas finales (espera, respuesta, retorno, throughput).
        promedios_frame = ttk.Frame(frame_consola, padding=(0, 5))
        promedios_frame.pack(fill=tk.X)
        
        self.lbl_prom_espera_var = tk.StringVar(value="")
        self.lbl_prom_respuesta_var = tk.StringVar(value="")
        self.lbl_prom_retorno_var = tk.StringVar(value="")
        self.lbl_throughput_var = tk.StringVar(value="")
        
        ttk.Label(promedios_frame, textvariable=self.lbl_prom_espera_var, font=self.FONT_BOLD).pack(anchor=tk.W)
        ttk.Label(promedios_frame, textvariable=self.lbl_prom_respuesta_var, font=self.FONT_BOLD).pack(anchor=tk.W)
        ttk.Label(promedios_frame, textvariable=self.lbl_prom_retorno_var, font=self.FONT_BOLD).pack(anchor=tk.W)
        ttk.Label(promedios_frame, textvariable=self.lbl_throughput_var, font=self.FONT_BOLD).pack(anchor=tk.W)
        
        
        # ===================== PANEL INFERIOR (MEMORIA) =====================
        # Tabla con las particiones de memoria y su estado (Best-Fit).
        frame_derecha = ttk.LabelFrame(main_panes, text="Tabla de Particiones de Memoria", padding="10")
        main_panes.add(frame_derecha)

        # Treeview que describe cada partición de memoria.
        cols = ("id", "base", "tamano", "contenido", "estado")
        self.tree_particiones = ttk.Treeview(frame_derecha, columns=cols, show="headings")
        self.tree_particiones.heading("id", text="ID"); self.tree_particiones.column("id", width=40, anchor=tk.CENTER)
        self.tree_particiones.heading("base", text="Base"); self.tree_particiones.column("base", width=60, anchor=tk.E)
        self.tree_particiones.heading("tamano", text="Tamaño"); self.tree_particiones.column("tamano", width=80, anchor=tk.E)
        self.tree_particiones.heading("contenido", text="Contenido"); self.tree_particiones.column("contenido", width=200)
        self.tree_particiones.heading("estado", text="Estado / FI"); self.tree_particiones.column("estado", width=150)
        self.tree_particiones.pack(fill=tk.BOTH, expand=True)
        
    def reset_simulador(self):
        # Vuelve la GUI y el motor a su estado inicial (sin simulación cargada).
        self.simulador = None 
        self.total_procesos = 0
        
        # Restaura valores iniciales de etiquetas de estado.
        self.lbl_reloj_var.set("Reloj: 0")
        self.lbl_ejecutando_var.set("—")
        self.lbl_listos_var.set("—")
        self.lbl_ls_var.set("—")
        self.lbl_nuevos_var.set("—")
        self.lbl_terminados_var.set("—")

        if hasattr(self, "progress_var"):
            self.progress_var.set(0.0)
        
        # Limpia todos los contenedores (listas/tablas).
        self.list_eventos.delete(0, tk.END)
        self.tree_particiones.delete(*self.tree_particiones.get_children())
        self.tree_consola.delete(*self.tree_consola.get_children())
 
        self.lbl_consola_status_var.set("Simulación reiniciada. Cargue un nuevo archivo CSV.")
        
        # Borra cualquier métrica final previa.
        self.lbl_prom_espera_var.set("")
        self.lbl_prom_respuesta_var.set("")
        self.lbl_prom_retorno_var.set("")
        self.lbl_throughput_var.set("")

        # El avance por tick vuelve a deshabilitarse hasta que se cargue un CSV.
        self.btn_toolbar_tick.config(state=tk.DISABLED)
    
    def siguiente_tick(self):
        # Avanza un instante de tiempo en el motor de simulación y refresca la GUI.
        if not self.simulador:
            return
        
        # Ajuste de reloj interno: comienza en 1 si estaba en 0, luego se incrementa.
        if self.simulador.get_reloj() == 0:
            self.simulador.reloj = 1
        else:
            self.simulador.reloj += 1

        # Ejecuta la lógica del siguiente tick en el motor.
        self.simulador.tick()
        
        # Refresca todos los paneles de la interfaz.
        self.actualizar_gui()

        # Si el simulador ya no tiene procesos activos, se finaliza la simulación.
        if not self.simulador.is_running():
            self.finalizar_simulacion()

    def finalizar_simulacion(self):
        # Acciones de cierre tras el último tick: bloquea avance y muestra reporte.
        if not self.simulador:
            return

        # No se puede seguir avanzando el reloj.
        self.btn_toolbar_tick.config(state=tk.DISABLED)

        # Progreso global al 100%.
        if hasattr(self, "progress_var"):
            self.progress_var.set(100.0)

        # Mensaje informativo con el tiempo de finalización.
        messagebox.showinfo("Simulación Terminada", f"La simulación finalizó en t={self.simulador.get_reloj()}.")
        self.lbl_consola_status_var.set(f"Simulación terminada en t={self.simulador.get_reloj()}. Generando reporte...")

        # Obtiene el resumen final calculado por el motor.
        if not self.simulador:
            return
        reporte = self.simulador.get_reporte_final()

        # Actualiza las métricas en la consola central.
        self.actualizar_consola_final(reporte)

        # Abre una ventana aparte con la tabla detallada de métricas por proceso.
        self.mostrar_reporte_final_ventana(reporte)

    def actualizar_consola_final(self, reporte):
        # Carga en las etiquetas los promedios y el throughput del reporte final.
        if not self.simulador:
            return

        if reporte["procesos_contados"] > 0:
            proms = reporte["promedios"]
            self.lbl_prom_espera_var.set(f"- Espera promedio = {proms['espera']}")
            self.lbl_prom_respuesta_var.set(f"- Respuesta promedio = {proms['respuesta']}")
            self.lbl_prom_retorno_var.set(f"- Retorno promedio = {proms['retorno']}")
            
            pc = reporte["procesos_contados"]
            tf = reporte["tiempo_final"]
            tp = reporte["throughput"]
            self.lbl_throughput_var.set(f"Rendimiento: {pc} terminados / {tf} t.u. = {tp} trabajos/t.u.")
        else:
            # Caso límite: ningún proceso llegó a completarse.
            self.lbl_prom_espera_var.set("- No finalizaron procesos.")

    def mostrar_reporte_final_ventana(self, reporte):
        # Crea una ventana independiente con la tabla final de métricas por proceso.
        win = tk.Toplevel(self.root)
        win.title("Reporte Final de Simulación")
        
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Treeview para mostrar, por proceso, arribo, 1ª CPU, fin, servicio, W, R, T.
        cols_consola = ("pid", "arribo", "primera_cpu", "fin", "servicio", "espera", "respuesta", "retorno")
        tree = ttk.Treeview(frame, columns=cols_consola, show="headings", height=10)

        # Configuración de columnas para el reporte.
        tree.heading("pid", text="PID"); tree.column("pid", width=60, anchor=tk.CENTER)
        tree.heading("arribo", text="Arribo"); tree.column("arribo", width=80, anchor=tk.CENTER)
        tree.heading("primera_cpu", text="1ª CPU"); tree.column("primera_cpu", width=80, anchor=tk.CENTER)
        tree.heading("fin", text="Fin"); tree.column("fin", width=70, anchor=tk.CENTER)
        tree.heading("servicio", text="Servicio"); tree.column("servicio", width=80, anchor=tk.CENTER)
        tree.heading("espera", text="Espera W"); tree.column("espera", width=90, anchor=tk.CENTER)
        tree.heading("respuesta", text="Respuesta R"); tree.column("respuesta", width=110, anchor=tk.CENTER)
        tree.heading("retorno", text="Retorno T"); tree.column("retorno", width=120, anchor=tk.CENTER)

        # Scrollbar vertical para la tabla de reporte.
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Inserta los registros de cada proceso en el treeview.
        for p_data in reporte["procesos"]:
            tree.insert(
                "",
                tk.END,
                values=(
                    p_data["pid"],
                    p_data["arribo"],
                    p_data["primera_cpu"],
                    p_data["fin"],
                    p_data["servicio"],
                    p_data["espera"],
                    p_data["respuesta"],
                    p_data["retorno"],
                ),
            )

        # Muestra promedios en la parte inferior de la ventana de reporte.
        bottom = ttk.Frame(win, padding=(10, 5))
        bottom.pack(fill=tk.X)

        if reporte["procesos_contados"] > 0:
            proms = reporte["promedios"]
            pc = reporte["procesos_contados"]
            tf = reporte["tiempo_final"]
            tp = reporte["throughput"]

            ttk.Label(
                bottom,
                text=f"Espera promedio: {proms['espera']} | Respuesta promedio: {proms['respuesta']} | Retorno promedio: {proms['retorno']}",
                font=self.FONT_BOLD,
            ).pack(anchor=tk.W)
            ttk.Label(
                bottom,
                text=f"Rendimiento: {pc} terminados / {tf} t.u. = {tp} trabajos/t.u.",
                font=self.FONT_BOLD,
            ).pack(anchor=tk.W)
        else:
            ttk.Label(
                bottom,
                text="No finalizaron procesos.",
                font=self.FONT_BOLD,
            ).pack(anchor=tk.W)


    def actualizar_gui(self):
        # Toma el snapshot de estado del simulador y lo refleja en todos los paneles.
        if not self.simulador: 
            return

        # Diccionario estructurado con todo lo que la GUI necesita pintar.
        datos = self.simulador.get_datos_gui()

        # --- Actualización de etiquetas de colas y reloj ---
        self.lbl_reloj_var.set(f"Reloj: {datos['reloj']}")
        self.lbl_ejecutando_var.set(datos['ejecutando']) 
        self.lbl_listos_var.set(", ".join(datos['listos']) or "—")
        self.lbl_ls_var.set(", ".join(datos['listos_suspendidos']) or "—")
        self.lbl_nuevos_var.set(", ".join(datos['nuevos']) or "—")
        self.lbl_terminados_var.set(", ".join(datos['terminados']) or "—")

        # --- Progreso global en función de procesos terminados ---
        try:
            terminados_count = len(datos.get('terminados', []))
            if self.total_procesos > 0:
                progreso = (terminados_count / self.total_procesos) * 100
                if hasattr(self, "progress_var"):
                    self.progress_var.set(progreso)
        except Exception:
            # Evita que cualquier error en el cálculo corte la actualización visual.
            pass

        # --- Tabla de procesos (con barra textual de progreso por proceso) ---
        self.tree_consola.delete(*self.tree_consola.get_children())
        for p_data in datos.get("tabla_procesos", []):
            # Construye una barra de 10 bloques (█) proporcional al porcentaje.
            progreso = p_data["progreso"]
            bloques = 10
            llenos = max(0, min(bloques, int(round(progreso / 10))))
            barra_txt = "█" * llenos + " " * (bloques - llenos)

            estado = p_data["estado"]
            tag = f"estado_{estado}" if estado else ""

            self.tree_consola.insert(
                "",
                tk.END,
                values=(
                    p_data["pid"],
                    p_data["ta"],
                    p_data["ti"],
                    p_data["mem"],
                    estado,
                    barra_txt,
                    f"{progreso:.1f}",
                ),
                tags=(tag,) if tag else None, # Aplica el tag de color de estado.
            )

        # --- Lista de eventos del tick actual ---
        self.list_eventos.delete(0, tk.END) 
        if datos['eventos']:
            for ev in datos['eventos']:
                self.list_eventos.insert(tk.END, ev)
        else:
            # Si no hay eventos pero el reloj avanzó, se indica explícitamente.
            if self.simulador.get_reloj() > 0: 
                self.list_eventos.insert(tk.END, "--- Sin eventos ---")
        self.list_eventos.yview(tk.END) # Hace scroll al final.

        # --- Tabla de particiones de memoria ---
        self.tree_particiones.delete(*self.tree_particiones.get_children()) 
        for p_data in datos['particiones']:
            self.tree_particiones.insert("", tk.END, values=(
                p_data['id'], p_data['base'], p_data['tamano'], p_data['contenido'], p_data['estado']
            ))

    def cargar_csv(self):
        # Orquesta el flujo completo de carga del CSV y creación del simulador.
        # 1) Muestra diálogo de elección de ruta.
        dialog = CargarCsvDialog(self.root)
        self.root.wait_window(dialog)
        
        decision = dialog.resultado
        
        # Si el usuario cerró/canceló el diálogo, no se hace nada más.
        if decision is None:
            self.lbl_consola_status_var.set("Carga cancelada.")
            return

        procesos = []
        error_str = ""
        fuente_carga = ""
        ruta_final = ""

        try:
            # 2) Determina la ruta final (explorador o ruta escrita).
            if decision["tipo"] == "explorador":
                path = filedialog.askopenfilename(
                    title="Seleccionar archivo CSV de procesos",
                    filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
                )
                if not path: 
                    self.lbl_consola_status_var.set("Carga cancelada.")
                    return
                ruta_final = path
            
            elif decision["tipo"] == "ruta":
                ruta_final = decision["valor"] 
            
            if not ruta_final:
                 self.lbl_consola_status_var.set("Carga cancelada.")
                 return

            # 3) Llama al lector/validador de CSV externo (lector_csv.leer_csv_procesos).
            fuente_carga = os.path.basename(ruta_final)
            procesos, error_str = leer_csv_procesos(ruta_final)

        except Exception as e:
            # Captura errores inesperados durante la carga/lectura.
            error_str = f"Ocurrió un error inesperado: {e}"

        # 4) Manejo de errores de validación y arranque del simulador.
        if error_str: 
            # Muestra advertencias de validación pero, si hay procesos válidos,
            # permite continuar.
            messagebox.showwarning("Errores de Validación", error_str)
        
        if not procesos:
            # Si no se pudo construir ningún proceso válido, aborta la simulación.
            messagebox.showerror("Error", "No se cargaron procesos válidos. La simulación no puede iniciar.")
            return
        
        # Reestablece la GUI y crea una nueva instancia del motor de simulación.
        self.reset_simulador()
        self.simulador = Simulador(procesos)
        self.total_procesos = len(procesos)

        if hasattr(self, "progress_var"):
            self.progress_var.set(0.0)
        
        # Habilita el avance por ticks.
        self.btn_toolbar_tick.config(state=tk.NORMAL)
        
        # Confirma cantidad de procesos cargados y estado inicial.
        messagebox.showinfo("Simulación Lista", f"Se cargaron {len(procesos)} procesos válidos. \nPresione 'Tick' para comenzar en T=0.")
        self.lbl_consola_status_var.set(f"Archivo cargado: {fuente_carga} | Procesos listos: {len(procesos)}")
        
        # Pinta el estado para t=0 (antes del primer tick).
        self.actualizar_gui()

# --- Punto de entrada de la aplicación ---
if __name__ == "__main__":
    try:
        root = tk.Tk() 
        app = App(root) 
        root.mainloop()
    except Exception as e:
        # Fallback en consola por si hay problemas con PIL o iconos.
        print(f"Ocurrió un error al iniciar la aplicación: {e}")
        print("Asegúrate de tener instalada la librería Pillow (pip install Pillow) y que los iconos PNG estén en el directorio 'iconos/'.")
