NEW = r'''def generar_certificado_pdf(row):
    """CERTIFICACION DE CALIFICACIONES alineada al MODELO OFICIAL de la UNEM:
    encabezado con escudo y serial, parrafo del Secretario, tabla
    Periodo / Unidad Curricular / U.C. / Calificacion (numero + palabra),
    nota de escala, parrafo especial para TSU, firma y sello reales,
    y representante de la Secretaria del estado."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.graphics.barcode import code128
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics import renderPDF

    def _g(k):
        try:
            v = row.get(k, "")
        except AttributeError:
            v = row[k] if k in row else ""
        return str(v or "").strip()

    ancho, alto = letter
    margen = 18 * mm
    x0, x1 = margen, ancho - margen
    centro = ancho / 2

    nombre_completo = (_g("nombres") + " " + _g("apellidos")).strip()
    cedula = _g("cedula")
    programa = _g("programa")
    estado = _g("estado")
    municipio = _g("municipio")
    sexo = _g("sexo")
    tipo_estudiante = _g("tipo_estudiante").upper()
    es_tsu = "TSU" in tipo_estudiante
    periodo_inicio = _g("periodo_inicio")
    try:
        ppa = int(float(_g("periodos_por_anio") or 2))
    except (ValueError, TypeError):
        ppa = 2
    if ppa < 1:
        ppa = 2
    fecha_emision = _fecha_larga_es()
    titulo_grado = titulo_por_genero(programa, sexo)
    _ced_alnum = "".join(ch for ch in cedula if ch.isalnum())
    serial = str(datetime.now().year) + "-I-" + _ced_alnum

    malla = obtener_malla(programa, incluir_introductorio=False)
    notas = obtener_notas(cedula)

    pos = []
    for m in malla:
        po = int(m.get("periodo_orden") or 0)
        if po not in pos:
            pos.append(po)
    pos_sorted = sorted(p for p in pos if p > 0)
    codigos = _secuencia_periodos(periodo_inicio, ppa, len(pos_sorted)) if periodo_inicio else []
    po_code = {}
    for i, po in enumerate(pos_sorted):
        po_code[po] = codigos[i] if i < len(codigos) else ""

    escudo = next((p for p in ESCUDO_PATHS if os.path.exists(p)), None)
    firma = next((p for p in FIRMA_PATHS if os.path.exists(p)), None)
    sello = next((p for p in SELLO_PATHS if os.path.exists(p)), None)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    def _wrap(texto, fuente, tam, ancho_max):
        out, linea = [], ""
        for w in str(texto).split():
            prueba = (linea + " " + w).strip()
            if stringWidth(prueba, fuente, tam) <= ancho_max or not linea:
                linea = prueba
            else:
                out.append(linea); linea = w
        if linea:
            out.append(linea)
        return out

    def _timbre(y):
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawString(x0, y, "TIMBRE FISCAL")
        c.drawRightString(x1, y, serial)
        c.setFillColorRGB(0, 0, 0)
        return y - 4 * mm

    def _encabezado(y):
        y = _timbre(y)
        if escudo:
            try:
                ew, eh = 20 * mm, 22 * mm
                c.drawImage(ImageReader(escudo), centro - ew / 2, y - eh,
                            width=ew, height=eh, preserveAspectRatio=True, mask="auto")
                y -= eh + 2 * mm
            except Exception:
                y -= 2 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(centro, y, "REP\u00daBLICA BOLIVARIANA DE VENEZUELA")
        y -= 4.2 * mm
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(centro, y, "Universidad Nacional Experimental del Magisterio \u201cSamuel Robinson\u201d")
        y -= 3.8 * mm
        c.setFont("Helvetica", 8)
        c.drawCentredString(centro, y, "Secretar\u00eda")
        y -= 7 * mm
        c.setFont("Helvetica-Bold", 12.5)
        c.drawCentredString(centro, y, "CERTIFICACI\u00d3N DE CALIFICACIONES")
        y -= 7 * mm
        return y

    col_uc = x1 - 30 * mm
    col_calif = x1

    def _cab_tabla(y):
        c.setFillColorRGB(0.12, 0.16, 0.5)
        c.rect(x0, y - 6 * mm, x1 - x0, 6 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x0 + 2 * mm, y - 4.2 * mm, "Per\u00edodo")
        c.drawString(x0 + 20 * mm, y - 4.2 * mm, "Nombre de la Unidad Curricular")
        c.drawRightString(col_uc, y - 4.2 * mm, "U.C.")
        c.drawRightString(col_calif - 2 * mm, y - 4.2 * mm, "Calificaci\u00f3n")
        c.setFillColorRGB(0, 0, 0)
        return y - 6 * mm

    y = _encabezado(alto - margen)

    intro = ("Quien suscribe LENIN ROBERTO ROMERO ROSA, titular de la C\u00e9dula de identidad "
             "No. V-2.956.814, secretario de la Universidad Nacional Experimental del "
             "Magisterio \u201cSamuel Robinson\u201d, con asiento principal en la ciudad de Caracas, "
             "Distrito Capital, Venezuela, certifica que en el Expediente Acad\u00e9mico "
             "Estudiantil UNEM correspondiente a " + nombre_completo + ", C\u00e9dula de Identidad "
             "No. " + cedula + ", quien curs\u00f3 estudios en el Programa Nacional de Formaci\u00f3n en "
             "Educaci\u00f3n para optar al T\u00edtulo de " + titulo_grado + ", en el Estado " + estado + ", "
             "municipio " + municipio + ", se encuentra su registro acad\u00e9mico en donde consta "
             "que curs\u00f3 y aprob\u00f3 las Unidades Curriculares que se especifican a continuaci\u00f3n:")
    c.setFont("Helvetica", 9)
    for ln in _wrap(intro, "Helvetica", 9, x1 - x0):
        c.drawString(x0, y, ln); y -= 4.6 * mm
    y -= 3 * mm

    y = _cab_tabla(y)
    total_uc = 0.0
    fila_alto = 5.4 * mm
    ancho_mat = (col_uc - 3 * mm) - (x0 + 20 * mm)
    if not malla:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(x0 + 2 * mm, y - 4 * mm, "(A\u00fan no hay malla curricular cargada para este programa.)")
        y -= fila_alto
    for m in malla:
        nota_raw = notas.get(m["materia"], "")
        calif = _calificacion_texto(nota_raw) if nota_raw else "POR CURSAR"
        mat_lines = _wrap(m["materia"], "Helvetica", 8, ancho_mat) or [""]
        alto_fila = max(fila_alto, len(mat_lines) * 3.6 * mm + 2 * mm)
        if y - alto_fila < margen + 62 * mm:
            c.showPage()
            y = _encabezado(alto - margen)
            y = _cab_tabla(y)
        po = int(m.get("periodo_orden") or 0)
        cod = po_code.get(po, "")
        uc = float(m["creditos"] or 0)
        total_uc += uc
        yb = y - 4 * mm
        c.setFont("Helvetica", 8)
        c.drawString(x0 + 2 * mm, yb, cod)
        for i, ml in enumerate(mat_lines):
            c.drawString(x0 + 20 * mm, yb - i * 3.6 * mm, ml)
        c.drawRightString(col_uc, yb, ("%g" % uc if uc else "-"))
        c.setFont("Helvetica", 7.5)
        c.drawRightString(col_calif - 2 * mm, yb, calif)
        c.setStrokeColorRGB(0.8, 0.8, 0.8); c.setLineWidth(0.3)
        c.line(x0, y - alto_fila, x1, y - alto_fila)
        y -= alto_fila
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x0 + 2 * mm, y - 4.5 * mm, "TOTAL UNIDADES DE CR\u00c9DITO")
    c.drawRightString(col_uc, y - 4.5 * mm, "%g" % total_uc)
    y -= 11 * mm

    if y < margen + 72 * mm:
        c.showPage(); y = _encabezado(alto - margen)
    nota_escala = ("Se expone en la certificaci\u00f3n solamente las unidades curriculares "
                   "cursadas y aprobadas en el periodo respectivo. La escala de calificaci\u00f3n "
                   "es del 1 al 20 con m\u00ednima aprobatoria 12 (doce). Son consideradas tambi\u00e9n "
                   "las calificaciones de AP \u201cAprobado\u201d, AC \u201cAprobada por Acreditaci\u00f3n\u201d.")
    c.setFont("Helvetica", 8)
    for ln in _wrap(nota_escala, "Helvetica", 8, x1 - x0):
        c.drawString(x0, y, ln); y -= 4 * mm
    y -= 2 * mm

    if es_tsu:
        parr_tsu = ("Estas Notas Certificadas pertenecen a un Profesional al cual se le "
                    "reconoci\u00f3 dos trayectos (T1 y T2) y curs\u00f3 y aprob\u00f3 o acredit\u00f3 dos "
                    "trayectos (T3 y T4) de la malla del Plan de Estudios para obtener el "
                    "T\u00edtulo de: " + titulo_grado + " y as\u00ed dar cumplimiento a la resoluci\u00f3n del "
                    "Consejo Directivo No: 083.12.2022.")
        c.setFont("Helvetica", 8)
        for ln in _wrap(parr_tsu, "Helvetica", 8, x1 - x0):
            c.drawString(x0, y, ln); y -= 4 * mm
        y -= 2 * mm

    cierre = ("Certificaci\u00f3n que se expide a petici\u00f3n de la parte interesada a los "
              "efectos y fines consiguientes, en Caracas el " + fecha_emision + ".")
    c.setFont("Helvetica", 8.5)
    for ln in _wrap(cierre, "Helvetica", 8.5, x1 - x0):
        c.drawString(x0, y, ln); y -= 4.4 * mm
    y -= 14 * mm

    if y < margen + 48 * mm:
        c.showPage(); y = alto - margen - 20 * mm

    if firma:
        try:
            fw, fh = 42 * mm, 17 * mm
            c.drawImage(ImageReader(firma), centro - fw / 2, y, width=fw, height=fh,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    if sello:
        try:
            sw, sh = 30 * mm, 30 * mm
            c.drawImage(ImageReader(sello), centro + 18 * mm, y - 6 * mm, width=sw, height=sh,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.7)
    c.line(centro - 40 * mm, y, centro + 40 * mm, y)
    y -= 4.5 * mm
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(centro, y, "LENIN ROBERTO ROMERO ROSA")
    y -= 4 * mm
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(centro, y, "SECRETARIO")
    y -= 3.8 * mm
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(centro, y, "Universidad Nacional Experimental del Magisterio \u201cSamuel Robinson\u201d")
    y -= 3.5 * mm
    c.drawCentredString(centro, y, "Seg\u00fan Gaceta No: 41.632   Resoluci\u00f3n Conjunta No. 0026/002")
    y -= 13 * mm

    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.6)
    c.line(x0, y, x0 + 70 * mm, y)
    y -= 4 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x0, y, "Representante de la Secretar\u00eda")
    y -= 3.6 * mm
    c.drawString(x0, y, "del Estado " + estado)

    qr_texto = ("UNEM - CERTIFICACION DE CALIFICACIONES\n" +
                "Nombres: " + nombre_completo + "\n" +
                "Titulo: " + titulo_grado + "\n" +
                "Cedula: " + cedula + "\n" +
                "Estado: " + estado + "\n" +
                "Serial: " + serial + "\n" +
                "Emision: " + fecha_emision)
    y_pie = margen + 2 * mm
    try:
        qrw = QrCodeWidget(qr_texto)
        b = qrw.getBounds()
        qsize = 22 * mm
        d = Drawing(qsize, qsize, transform=[qsize / (b[2] - b[0]), 0, 0, qsize / (b[3] - b[1]), 0, 0])
        d.add(qrw)
        renderPDF.draw(d, c, x0, y_pie)
    except Exception:
        pass
    cod = _ced_alnum or "0"
    try:
        barcode = code128.Code128(cod, barHeight=12 * mm, barWidth=0.4 * mm)
        barcode.drawOn(c, x1 - barcode.width, y_pie + 3 * mm)
    except Exception:
        pass
    c.setFont("Helvetica", 7)
    c.drawRightString(x1, y_pie, "Serial: " + serial)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
'''

import io
APP = "/nfs/106072397/outputs/app.py"
with io.open(APP, "r", encoding="utf-8") as f:
    src = f.read()

start = src.index("def generar_certificado_pdf(row):")
marker = "\n\n\n# ============================================================\n# INICIALIZACI\u00d3N"
end = src.index(marker, start)
new_src = src[:start] + NEW + src[end+1:]
with io.open(APP, "w", encoding="utf-8") as f:
    f.write(new_src)
print("replaced. old len", end-start, "new len", len(NEW))
