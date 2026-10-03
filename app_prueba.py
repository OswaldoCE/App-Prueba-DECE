import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from PIL import Image

# Librerías para exportar a PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# 1. MODO CLARO EXCLUSIVO Y TEMA INSTITUCIONAL
ctk.set_appearance_mode("Light")  # Forzado a modo claro
ctk.set_default_color_theme("blue")  # Tema azul institucional UdeG


class AplicacionHorariosDECE(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.title("DECE - Sistema de Horarios Docentes (UdeG)")
        self.geometry("980x740")
        self.minsize(900, 650)
        self.configure(fg_color="#F4F6F9")  # Fondo claro moderno de macOS

        # Variable para almacenar los registros activos filtrados
        self.registros_consulta = []

        # Inicializar la Base de Datos SQLite
        self.inicializar_bd()

        # Mapeos en memoria para combos (Nombre -> ID)
        self.mapa_profesores = {}
        self.mapa_materias = {}

        # Construir Interfaz
        self.crear_encabezado_institucional()
        self.crear_panel_pestanas()

        # Cargar datos iniciales en controles
        self.cargar_profesores()
        self.cargar_materias()
        self.actualizar_combos_horario()
        self.cargar_filtros_consulta()
        self.consultar_horarios()

    # ==========================================
    # 1. BASE DE DATOS (SQLite)
    # ==========================================
    def inicializar_bd(self):
        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()

        # Tabla de Profesores
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profesores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                carga INTEGER NOT NULL
            )
        """
        )

        # Tabla de Materias
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                horas INTEGER NOT NULL
            )
        """
        )

        # Tabla de Horarios (Relaciona Profesor ID y Materia ID)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS horarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profesor_id INTEGER NOT NULL,
                materia_id INTEGER NOT NULL,
                dia TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL,
                FOREIGN KEY (profesor_id) REFERENCES profesores (id),
                FOREIGN KEY (materia_id) REFERENCES materias (id)
            )
        """
        )

        conexion.commit()
        conexion.close()

    # ==========================================
    # 2. ENCABEZADO INSTITUCIONAL (UdeG & DECE)
    # ==========================================
    def crear_encabezado_institucional(self):
        frame_header = ctk.CTkFrame(
            self, corner_radius=12, fg_color="white", border_width=1, border_color="#E0E0E0"
        )
        frame_header.pack(fill="x", padx=15, pady=(15, 10))

        # Cargar Logo de la UdeG
        ruta_logo = os.path.join(os.path.dirname(__file__), "logo_udg.png")
        if os.path.exists(ruta_logo):
            img_pil = Image.open(ruta_logo)
            logo_ctk = ctk.CTkImage(
                light_image=img_pil, dark_image=img_pil, size=(55, 70)
            )
            lbl_logo = ctk.CTkLabel(frame_header, image=logo_ctk, text="")
            lbl_logo.pack(side="left", padx=15, pady=10)

        # Textos Institucionales
        frame_textos = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_textos.pack(side="left", fill="both", expand=True, pady=10)

        lbl_udg = ctk.CTkLabel(
            frame_textos,
            text="UNIVERSIDAD DE GUADALAJARA",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#002B49",
        )
        lbl_udg.pack(anchor="w")

        lbl_dece = ctk.CTkLabel(
            frame_textos,
            text="Departamento de Emprendimiento, Comercio y Empresa",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#1A1A1A",
        )
        lbl_dece.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame_textos,
            text="Sistema General de Gestión de Horarios Docentes y Materias",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        )
        lbl_sub.pack(anchor="w")

    # ==========================================
    # 3. PANEL DE PESTAÑAS (Navegación macOS)
    # ==========================================
    def crear_panel_pestanas(self):
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color="white",
            segmented_button_selected_color="#002B49",
            segmented_button_selected_hover_color="#0D47A1",
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Pestañas
        self.tab_consulta = self.tabview.add("🔍 1. Consulta General y PDF")
        self.tab_profesores = self.tabview.add("👨‍🏫 2. Profesores")
        self.tab_materias = self.tabview.add("📚 3. Materias")
        self.tab_horarios = self.tabview.add("📅 4. Asignación y Traslapes")

        # Configurar estilos de las tablas integradas (Treeview)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#333333",
            rowheight=28,
            font=("Helvetica", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#F0F2F5",
            foreground="#002B49",
            font=("Helvetica", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#E3F2FD")], foreground=[("selected", "#0D47A1")])

        # Construcción de vistas
        self.construir_pestana_consulta()
        self.construir_pestana_profesores()
        self.construir_pestana_materias()
        self.construir_pestana_horarios()

    # ------------------------------------------
    # PESTAÑA 1: CONSULTA Y FILTROS + EXPORTACIÓN PDF
    # ------------------------------------------
    def construir_pestana_consulta(self):
        card_filtros = ctk.CTkFrame(self.tab_consulta, corner_radius=10, fg_color="#F8F9FA")
        card_filtros.pack(fill="x", padx=10, pady=10)

        lbl_titulo = ctk.CTkLabel(
            card_filtros,
            text="Consulta General de Horarios y Búsqueda Avanzada",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#002B49",
        )
        lbl_titulo.grid(row=0, column=0, columnspan=4, padx=15, pady=(8, 4), sticky="w")

        # Filtro Profesor
        ctk.CTkLabel(card_filtros, text="Profesor:", text_color="#333333", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=(15, 5), pady=8, sticky="w")
        self.cb_filtro_profesor = ctk.CTkComboBox(card_filtros, values=["Todos"], width=200)
        self.cb_filtro_profesor.grid(row=1, column=1, padx=5, pady=8, sticky="w")

        # Filtro Materia
        ctk.CTkLabel(card_filtros, text="Materia:", text_color="#333333", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=(15, 5), pady=8, sticky="w")
        self.cb_filtro_materia = ctk.CTkComboBox(card_filtros, values=["Todas"], width=200)
        self.cb_filtro_materia.grid(row=1, column=3, padx=5, pady=8, sticky="w")

        # Filtro Día
        ctk.CTkLabel(card_filtros, text="Día:", text_color="#333333", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=(15, 5), pady=8, sticky="w")
        self.cb_filtro_dia = ctk.CTkComboBox(
            card_filtros,
            values=["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
            width=200,
        )
        self.cb_filtro_dia.grid(row=2, column=1, padx=5, pady=8, sticky="w")

        # Botones de Acción
        frame_botones = ctk.CTkFrame(card_filtros, fg_color="transparent")
        frame_botones.grid(row=2, column=2, columnspan=2, padx=15, pady=8, sticky="e")

        btn_filtrar = ctk.CTkButton(
            frame_botones,
            text="🔎 Filtrar / Buscar",
            fg_color="#0D47A1",
            hover_color="#002B49",
            width=130,
            command=self.consultar_horarios,
        )
        btn_filtrar.pack(side="left", padx=5)

        btn_pdf = ctk.CTkButton(
            frame_botones,
            text="📄 Exportar a PDF",
            fg_color="#C62828",
            hover_color="#8E0000",
            width=130,
            command=self.exportar_a_pdf,
        )
        btn_pdf.pack(side="left", padx=5)

        # Tabla Resultados Consulta
        frame_tabla = ctk.CTkFrame(self.tab_consulta, corner_radius=10, fg_color="white")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabla_consulta = ttk.Treeview(
            frame_tabla,
            columns=("profesor", "materia", "dia", "horario"),
            show="headings",
            height=8,
        )
        self.tabla_consulta.heading("profesor", text="Profesor")
        self.tabla_consulta.heading("materia", text="Materia Asignada")
        self.tabla_consulta.heading("dia", text="Día")
        self.tabla_consulta.heading("horario", text="Bloque Horario")

        self.tabla_consulta.column("profesor", width=260, anchor="w")
        self.tabla_consulta.column("materia", width=260, anchor="w")
        self.tabla_consulta.column("dia", width=120, anchor="center")
        self.tabla_consulta.column("horario", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla_consulta.yview)
        self.tabla_consulta.configure(yscroll=scrollbar.set)

        self.tabla_consulta.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    # ------------------------------------------
    # PESTAÑA 2: PROFESORES
    # ------------------------------------------
    def construir_pestana_profesores(self):
        card_form = ctk.CTkFrame(self.tab_profesores, corner_radius=10, fg_color="#F8F9FA")
        card_form.pack(fill="x", padx=10, pady=10)

        lbl_titulo = ctk.CTkLabel(
            card_form,
            text="Registro de Nuevo Docente",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#002B49",
        )
        lbl_titulo.grid(row=0, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        self.entry_codigo_p = ctk.CTkEntry(
            card_form, placeholder_text="Código Docente (ej. 001)", width=210
        )
        self.entry_codigo_p.grid(row=1, column=0, padx=15, pady=6)

        self.entry_nombre_p = ctk.CTkEntry(
            card_form, placeholder_text="Nombre Completo del Profesor", width=340
        )
        self.entry_nombre_p.grid(row=1, column=1, padx=15, pady=6)

        self.entry_carga_p = ctk.CTkEntry(
            card_form, placeholder_text="Carga Máxima (Horas)", width=210
        )
        self.entry_carga_p.grid(row=2, column=0, padx=15, pady=6)

        btn_guardar = ctk.CTkButton(
            card_form,
            text="Guardar Profesor",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self.guardar_profesor,
        )
        btn_guardar.grid(row=2, column=1, padx=15, pady=6, sticky="e")

        frame_tabla = ctk.CTkFrame(self.tab_profesores, corner_radius=10, fg_color="white")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabla_profesores = ttk.Treeview(
            frame_tabla,
            columns=("codigo", "nombre", "carga"),
            show="headings",
            height=7,
        )
        self.tabla_profesores.heading("codigo", text="Código")
        self.tabla_profesores.heading("nombre", text="Nombre del Docente")
        self.tabla_profesores.heading("carga", text="Carga Máxima")

        self.tabla_profesores.column("codigo", width=120, anchor="center")
        self.tabla_profesores.column("nombre", width=480, anchor="w")
        self.tabla_profesores.column("carga", width=150, anchor="center")

        self.tabla_profesores.pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------
    # PESTAÑA 3: MATERIAS
    # ------------------------------------------
    def construir_pestana_materias(self):
        card_form = ctk.CTkFrame(self.tab_materias, corner_radius=10, fg_color="#F8F9FA")
        card_form.pack(fill="x", padx=10, pady=10)

        lbl_titulo = ctk.CTkLabel(
            card_form,
            text="Catálogo Oficial de Materias",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#002B49",
        )
        lbl_titulo.grid(row=0, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        self.entry_clave_m = ctk.CTkEntry(
            card_form, placeholder_text="Clave de Materia (ej. MKT-101)", width=210
        )
        self.entry_clave_m.grid(row=1, column=0, padx=15, pady=6)

        self.entry_nombre_m = ctk.CTkEntry(
            card_form, placeholder_text="Nombre Oficial de la Materia", width=340
        )
        self.entry_nombre_m.grid(row=1, column=1, padx=15, pady=6)

        self.entry_horas_m = ctk.CTkEntry(
            card_form, placeholder_text="Horas Semanales", width=210
        )
        self.entry_horas_m.grid(row=2, column=0, padx=15, pady=6)

        btn_guardar_m = ctk.CTkButton(
            card_form,
            text="Guardar Materia",
            fg_color="#0D47A1",
            hover_color="#002B49",
            command=self.guardar_materia,
        )
        btn_guardar_m.grid(row=2, column=1, padx=15, pady=6, sticky="e")

        frame_tabla = ctk.CTkFrame(self.tab_materias, corner_radius=10, fg_color="white")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabla_materias = ttk.Treeview(
            frame_tabla,
            columns=("clave", "nombre", "horas"),
            show="headings",
            height=7,
        )
        self.tabla_materias.heading("clave", text="Clave")
        self.tabla_materias.heading("nombre", text="Nombre de la Asignatura")
        self.tabla_materias.heading("horas", text="Horas / Semanal")

        self.tabla_materias.column("clave", width=140, anchor="center")
        self.tabla_materias.column("nombre", width=460, anchor="w")
        self.tabla_materias.column("horas", width=150, anchor="center")

        self.tabla_materias.pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------
    # PESTAÑA 4: HORARIOS Y TRASLAPES
    # ------------------------------------------
    def construir_pestana_horarios(self):
        card_form = ctk.CTkFrame(self.tab_horarios, corner_radius=10, fg_color="#F8F9FA")
        card_form.pack(fill="x", padx=10, pady=10)

        lbl_titulo = ctk.CTkLabel(
            card_form,
            text="Asignación con Selección de Materia Oficial y Detección de Traslapes",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#002B49",
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=15, pady=8, sticky="w")

        # Combo Profesor
        self.combo_profesor = ctk.CTkComboBox(
            card_form, values=["Seleccione Docente..."], width=280
        )
        self.combo_profesor.grid(row=1, column=0, padx=15, pady=6)

        # Combo Materia
        self.combo_materia = ctk.CTkComboBox(
            card_form, values=["Seleccione Materia..."], width=280
        )
        self.combo_materia.grid(row=1, column=1, padx=15, pady=6)

        # Combo Día
        self.combo_dia = ctk.CTkOptionMenu(
            card_form,
            values=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
            width=160,
            fg_color="#002B49",
        )
        self.combo_dia.grid(row=1, column=2, padx=15, pady=6)

        horas = [f"{h:02d}:00" for h in range(7, 21)]

        # Hora Inicio y Fin
        self.combo_inicio = ctk.CTkOptionMenu(
            card_form, values=horas, width=130, fg_color="#37474F"
        )
        self.combo_inicio.set("08:00")
        self.combo_inicio.grid(row=2, column=0, padx=15, pady=6, sticky="w")

        self.combo_fin = ctk.CTkOptionMenu(
            card_form, values=horas, width=130, fg_color="#37474F"
        )
        self.combo_fin.set("10:00")
        self.combo_fin.grid(row=2, column=1, padx=15, pady=6, sticky="w")

        btn_validar = ctk.CTkButton(
            card_form,
            text="Validar y Asignar Horario",
            fg_color="#1565C0",
            hover_color="#0D47A1",
            command=self.guardar_horario,
        )
        btn_validar.grid(row=2, column=2, padx=15, pady=6, sticky="e")

        frame_tabla = ctk.CTkFrame(self.tab_horarios, corner_radius=10, fg_color="white")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabla_horarios = ttk.Treeview(
            frame_tabla,
            columns=("profesor", "materia", "dia", "horario"),
            show="headings",
            height=6,
        )
        self.tabla_horarios.heading("profesor", text="Profesor")
        self.tabla_horarios.heading("materia", text="Materia Asignada")
        self.tabla_horarios.heading("dia", text="Día")
        self.tabla_horarios.heading("horario", text="Bloque Horario")

        self.tabla_horarios.column("profesor", width=250)
        self.tabla_horarios.column("materia", width=250)
        self.tabla_horarios.column("dia", width=110, anchor="center")
        self.tabla_horarios.column("horario", width=130, anchor="center")

        self.tabla_horarios.pack(fill="both", expand=True, padx=10, pady=10)

    # ==========================================
    # 5. LÓGICA Y MANEJO DE DATOS
    # ==========================================
    def cargar_filtros_consulta(self):
        """Poblar dinámicamente los comboboxes de la pestaña de consulta."""
        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()

        cursor.execute("SELECT nombre FROM profesores ORDER BY nombre ASC")
        profesores = ["Todos"] + [row[0] for row in cursor.fetchall()]
        self.cb_filtro_profesor.configure(values=profesores)
        self.cb_filtro_profesor.set("Todos")

        cursor.execute("SELECT nombre FROM materias ORDER BY nombre ASC")
        materias = ["Todas"] + [row[0] for row in cursor.fetchall()]
        self.cb_filtro_materia.configure(values=materias)
        self.cb_filtro_materia.set("Todas")

        self.cb_filtro_dia.set("Todos")
        conexion.close()

    def consultar_horarios(self):
        """Realizar búsqueda con filtros en la pestaña de consulta."""
        for fila in self.tabla_consulta.get_children():
            self.tabla_consulta.delete(fila)

        profesor = self.cb_filtro_profesor.get()
        materia = self.cb_filtro_materia.get()
        dia = self.cb_filtro_dia.get()

        query = """
            SELECT p.nombre, m.nombre, h.dia, h.hora_inicio, h.hora_fin
            FROM horarios h
            JOIN profesores p ON h.profesor_id = p.id
            JOIN materias m ON h.materia_id = m.id
            WHERE 1=1
        """
        params = []

        if profesor != "Todos":
            query += " AND p.nombre = ?"
            params.append(profesor)

        if materia != "Todas":
            query += " AND m.nombre = ?"
            params.append(materia)

        if dia != "Todos":
            query += " AND h.dia = ?"
            params.append(dia)

        query += " ORDER BY h.dia, h.hora_inicio"

        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()
        cursor.execute(query, params)
        self.registros_consulta = cursor.fetchall()
        conexion.close()

        for reg in self.registros_consulta:
            self.tabla_consulta.insert(
                "", "end", values=(reg[0], reg[1], reg[2], f"{reg[3]} - {reg[4]}")
            )

    def exportar_a_pdf(self):
        """Generar PDF permitiendo al usuario elegir la ubicación de guardado."""
        if not self.registros_consulta:
            messagebox.showwarning(
                "Sin Datos", "No hay registros disponibles para exportar con los filtros seleccionados."
            )
            return

        # Abre el cuadro de diálogo nativo "Guardar como..."
        ruta_guardado = filedialog.asksaveasfilename(
            title="Guardar Reporte de Horarios DECE",
            defaultextension=".pdf",
            initialfile="Reporte_Horarios_DECE.pdf",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        # Si el usuario cancela la selección, se interrumpe el proceso
        if not ruta_guardado:
            return

        doc = SimpleDocTemplate(ruta_guardado, pagesize=letter)
        elementos = []
        estilos = getSampleStyleSheet()

        # Título institucional en PDF
        titulo = Paragraph(
            "<b>UNIVERSIDAD DE GUADALAJARA</b><br/><font size=12>Departamento de Emprendimiento, Comercio y Empresa</font><br/><font size=10 color='#666666'>Reporte General de Horarios Docentes</font>",
            estilos["Title"],
        )
        elementos.append(titulo)
        elementos.append(Spacer(1, 15))

        # Filtros informativos
        info = f"<b>Filtros aplicados:</b> Profesor: {self.cb_filtro_profesor.get()} | Materia: {self.cb_filtro_materia.get()} | Día: {self.cb_filtro_dia.get()}"
        elementos.append(Paragraph(info, estilos["Normal"]))
        elementos.append(Spacer(1, 12))

        # Tabla PDF
        datos = [["Profesor", "Materia", "Día", "Horario"]]
        for reg in self.registros_consulta:
            datos.append([reg[0], reg[1], reg[2], f"{reg[3]} - {reg[4]}"])

        tabla_pdf = Table(datos, colWidths=[170, 180, 80, 90])
        tabla_pdf.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002B49")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ])
        )

        elementos.append(tabla_pdf)

        try:
            doc.build(elementos)
            messagebox.showinfo(
                "PDF Generado", f"El reporte fue guardado exitosamente en:\n\n{ruta_guardado}"
            )
        except Exception as e:
            messagebox.showerror("Error PDF", f"No se pudo crear el archivo PDF: {e}")

    def guardar_profesor(self):
        codigo = self.entry_codigo_p.get().strip()
        nombre = self.entry_nombre_p.get().strip()
        carga = self.entry_carga_p.get().strip()

        if not codigo or not nombre or not carga:
            messagebox.showwarning("Atención", "Todos los campos de profesor son requeridos.")
            return

        try:
            conexion = sqlite3.connect("horarios_dece.db")
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO profesores (codigo, nombre, carga) VALUES (?, ?, ?)",
                (codigo, nombre, int(carga)),
            )
            conexion.commit()
            conexion.close()

            messagebox.showinfo("Éxito", f"Profesor '{nombre}' guardado con éxito.")
            self.entry_codigo_p.delete(0, "end")
            self.entry_nombre_p.delete(0, "end")
            self.entry_carga_p.delete(0, "end")

            self.cargar_profesores()
            self.actualizar_combos_horario()
            self.cargar_filtros_consulta()

        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"El código '{codigo}' ya existe.")
        except ValueError:
            messagebox.showerror("Error", "La carga horaria debe ser un número.")

    def cargar_profesores(self):
        for fila in self.tabla_profesores.get_children():
            self.tabla_profesores.delete(fila)

        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT codigo, nombre, carga FROM profesores ORDER BY nombre ASC")
        registros = cursor.fetchall()
        conexion.close()

        for reg in registros:
            self.tabla_profesores.insert("", "end", values=(reg[0], reg[1], f"{reg[2]} hrs"))

    def guardar_materia(self):
        clave = self.entry_clave_m.get().strip()
        nombre = self.entry_nombre_m.get().strip()
        horas = self.entry_horas_m.get().strip()

        if not clave or not nombre or not horas:
            messagebox.showwarning("Atención", "Todos los campos de la materia son requeridos.")
            return

        try:
            conexion = sqlite3.connect("horarios_dece.db")
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO materias (clave, nombre, horas) VALUES (?, ?, ?)",
                (clave, nombre, int(horas)),
            )
            conexion.commit()
            conexion.close()

            messagebox.showinfo("Éxito", f"Materia '{nombre}' añadida al catálogo oficial.")
            self.entry_clave_m.delete(0, "end")
            self.entry_nombre_m.delete(0, "end")
            self.entry_horas_m.delete(0, "end")

            self.cargar_materias()
            self.actualizar_combos_horario()
            self.cargar_filtros_consulta()

        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"La clave '{clave}' ya pertenece a otra materia.")
        except ValueError:
            messagebox.showerror("Error", "Las horas deben ser un número entero.")

    def cargar_materias(self):
        for fila in self.tabla_materias.get_children():
            self.tabla_materias.delete(fila)

        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT clave, nombre, horas FROM materias ORDER BY nombre ASC")
        registros = cursor.fetchall()
        conexion.close()

        for reg in registros:
            self.tabla_materias.insert("", "end", values=(reg[0], reg[1], f"{reg[2]} hrs"))

    def actualizar_combos_horario(self):
        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()

        # Profesores
        cursor.execute("SELECT id, nombre FROM profesores ORDER BY nombre ASC")
        profesores = cursor.fetchall()
        self.mapa_profesores = {nombre: pid for pid, nombre in profesores}
        lista_profesores = list(self.mapa_profesores.keys())

        if lista_profesores:
            self.combo_profesor.configure(values=lista_profesores)
            self.combo_profesor.set(lista_profesores[0])
        else:
            self.combo_profesor.configure(values=["Registre un profesor primero"])

        # Materias
        cursor.execute("SELECT id, nombre FROM materias ORDER BY nombre ASC")
        materias = cursor.fetchall()
        self.mapa_materias = {nombre: mid for mid, nombre in materias}
        lista_materias = list(self.mapa_materias.keys())

        if lista_materias:
            self.combo_materia.configure(values=lista_materias)
            self.combo_materia.set(lista_materias[0])
        else:
            self.combo_materia.configure(values=["Registre una materia primero"])

        conexion.close()

    def guardar_horario(self):
        nombre_profesor = self.combo_profesor.get()
        nombre_materia = self.combo_materia.get()
        dia = self.combo_dia.get()
        h_inicio = self.combo_inicio.get()
        h_fin = self.combo_fin.get()

        if (
            nombre_profesor == "Registre un profesor primero"
            or nombre_materia == "Registre una materia primero"
        ):
            messagebox.showwarning(
                "Atención", "Debe tener al menos un profesor y una materia registrados."
            )
            return

        if h_inicio >= h_fin:
            messagebox.showerror(
                "Error de Horario", "La hora de inicio debe ser menor a la hora de fin."
            )
            return

        profesor_id = self.mapa_profesores[nombre_profesor]
        materia_id = self.mapa_materias[nombre_materia]

        # --- ALGORITMO DE VERIFICACIÓN DE TRASLAPE ---
        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT m.nombre, h.hora_inicio, h.hora_fin 
            FROM horarios h
            JOIN materias m ON h.materia_id = m.id
            WHERE h.profesor_id = ? 
              AND h.dia = ? 
              AND h.hora_inicio < ? 
              AND h.hora_fin > ?
        """,
            (profesor_id, dia, h_fin, h_inicio),
        )

        conflicto = cursor.fetchone()

        if conflicto:
            conexion.close()
            messagebox.showerror(
                "⚠️️ CONFLICTO DETECTADO",
                f"El docente {nombre_profesor} ya tiene asignada la materia '{conflicto[0]}' "
                f"el {dia} en el horario {conflicto[1]} - {conflicto[2]}.",
            )
            return

        # Insertar horario asociando llaves foráneas
        cursor.execute(
            """
            INSERT INTO horarios (profesor_id, materia_id, dia, hora_inicio, hora_fin) 
            VALUES (?, ?, ?, ?, ?)
        """,
            (profesor_id, materia_id, dia, h_inicio, h_fin),
        )

        conexion.commit()
        conexion.close()

        messagebox.showinfo("Éxito", f"Clase de '{nombre_materia}' asignada correctamente.")
        self.cargar_horarios()
        self.consultar_horarios()

    def cargar_horarios(self):
        for fila in self.tabla_horarios.get_children():
            self.tabla_horarios.delete(fila)

        conexion = sqlite3.connect("horarios_dece.db")
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT p.nombre, m.nombre, h.dia, h.hora_inicio, h.hora_fin
            FROM horarios h
            JOIN profesores p ON h.profesor_id = p.id
            JOIN materias m ON h.materia_id = m.id
            ORDER BY h.dia, h.hora_inicio
        """
        )
        registros = cursor.fetchall()
        conexion.close()

        for reg in registros:
            self.tabla_horarios.insert(
                "", "end", values=(reg[0], reg[1], reg[2], f"{reg[3]} - {reg[4]}")
            )


if __name__ == "__main__":
    app = AplicacionHorariosDECE()
    app.mainloop()