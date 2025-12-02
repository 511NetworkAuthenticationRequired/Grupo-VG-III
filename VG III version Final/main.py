# main.py
import tkinter as tk          # Toolkit base para la creación de la ventana principal.
from gui import App           # Clase que construye y gestiona toda la interfaz del simulador.

if __name__ == "__main__":
    # Punto de entrada del programa: inicializa y lanza la aplicación GUI.
    root = tk.Tk()            # Instancia la ventana raíz de Tkinter.
    App(root)                 # Crea la aplicación del simulador sobre la ventana raíz.
    root.mainloop()           # Inicia el loop de eventos de la interfaz (bloqueante).
