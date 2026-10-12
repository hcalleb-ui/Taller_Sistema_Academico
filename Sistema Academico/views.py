"""CONTROLADOR: reglas del negocio y CRUD. Aquí NUNCA hay print() ni input()."""
import os

from models import Estudiante, Materia, Matricula
from shared.json_manager import GestorJSON
from shared.herramientas import es_email_valido

# Las rutas se calculan desde la carpeta de este archivo, así funciona
# aunque ejecutes el programa desde otra carpeta.
CARPETA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

gestor_estudiantes = GestorJSON(os.path.join(CARPETA_DATOS, "estudiantes.json"))
gestor_materias = GestorJSON(os.path.join(CARPETA_DATOS, "materias.json"))
gestor_matriculas = GestorJSON(os.path.join(CARPETA_DATOS, "matriculas.json"))

# TUPLAS: campos fijos que nunca se modifican (por eso no son listas).
# Las funciones de este archivo también devuelven la TUPLA (exito, mensaje):
# dos datos de distinto tipo, agrupados e inmutables.
CAMPOS_BUSCABLES_ESTUDIANTE = ("nombre", "apellido", "email", "carnet", "carrera")
CAMPOS_BUSCABLES_MATERIA = ("nombre", "codigo")
OBLIGATORIOS_ESTUDIANTE = ("nombre", "apellido", "email", "carnet")
OBLIGATORIOS_MATERIA = ("nombre", "codigo", "creditos")
CAMPOS_EDITABLES_ESTUDIANTE = ("nombre", "apellido", "email", "carnet", "carrera")
CAMPOS_EDITABLES_MATERIA = ("nombre", "codigo", "creditos", "cupos")


# =====================================================================
# FUNCIONES GENÉRICAS: funcionan con CUALQUIER modelo (polimorfismo).
# Reciben el gestor y la clase; no preguntan de qué tipo es el modelo,
# confían en que todos tienen desde_diccionario() y a_diccionario().
# =====================================================================
def leer_objetos(gestor, clase):
    """Lee el JSON y convierte cada diccionario en un objeto de `clase`."""
    return [clase.desde_diccionario(datos) for datos in gestor.leer()]


def obtener_por_id(gestor, clase, id_registro):
    for objeto in leer_objetos(gestor, clase):
        if objeto.id == id_registro:
            return objeto
    return None


def buscar(gestor, clase, termino, campos):
    """Busca `termino` dentro de los `campos` indicados (una TUPLA)."""
    termino = str(termino).strip().lower()
    encontrados = []
    if termino == "":
        return encontrados
    for objeto in leer_objetos(gestor, clase):
        datos = objeto.a_diccionario()
        for campo in campos:
            if termino in str(datos.get(campo, "")).lower():
                encontrados.append(objeto)
                break                      # ya coincidió: no repetir el objeto
    return encontrados


def siguiente_id(gestor):
    mayor = 0
    for datos in gestor.leer():
        if datos["id"] > mayor:
            mayor = datos["id"]
    return mayor + 1


def guardar_nuevo(gestor, objeto):
    datos = gestor.leer()
    datos.append(objeto.a_diccionario())
    return gestor.guardar(datos)


def reemplazar(gestor, objeto):
    """Cambia en el archivo el registro que tiene el mismo id que `objeto`."""
    datos = gestor.leer()
    for posicion, registro in enumerate(datos):
        if registro["id"] == objeto.id:
            datos[posicion] = objeto.a_diccionario()
            return gestor.guardar(datos)
    return False


def eliminar(gestor, id_registro):
    datos = gestor.leer()
    # Lista nueva sin ese id (nunca se borra mientras se recorre la misma lista)
    restantes = [registro for registro in datos if registro["id"] != id_registro]
    if len(restantes) == len(datos):
        return False
    return gestor.guardar(restantes)


def ids_registrados(gestor):
    # CONJUNTO: saber si un id existe con 'x in conjunto' es instantáneo
    # y los ids no se repiten, que es justo lo que necesitamos.
    return {registro["id"] for registro in gestor.leer()}


def indice_por_id(gestor, clase):
    # DICCIONARIO ÍNDICE {id: objeto}: buscar por id sin recorrer la lista.
    return {objeto.id: objeto for objeto in leer_objetos(gestor, clase)}


# =====================================================================
# ESTUDIANTES
# =====================================================================
def carnets_registrados(excepto_id=None):
    """CONJUNTO de carnets ya usados: preguntar 'x in conjunto' es instantáneo."""
    return {r["carnet"].upper() for r in gestor_estudiantes.leer()
            if r["id"] != excepto_id}


def emails_registrados(excepto_id=None):
    # CONJUNTO: el email tampoco puede repetirse.
    return {r["email"].lower() for r in gestor_estudiantes.leer()
            if r["id"] != excepto_id}


def validar_estudiante(datos, id_actual=None):
    """Devuelve un MENSAJE de error, o None si todo está bien."""
    # 1) obligatorios: al crear todos; al actualizar, solo los que vienen
    for campo in OBLIGATORIOS_ESTUDIANTE:
        if id_actual is None or campo in datos:
            if str(datos.get(campo, "")).strip() == "":
                return f"El campo {campo} es obligatorio"
    # 2) email válido y no repetido
    if "email" in datos:
        email = str(datos["email"]).strip().lower()
        if not es_email_valido(email):
            return f"Email inválido: '{email}'"
        if email in emails_registrados(id_actual):
            return "Ese email ya está registrado"
    # 3) carnet no repetido
    if "carnet" in datos:
        carnet = str(datos["carnet"]).strip().upper()
        if carnet in carnets_registrados(id_actual):
            return f"El carnet {carnet} ya está registrado"
    return None


def crear_estudiante(datos):
    error = validar_estudiante(datos)
    if error:
        return False, error
    estudiante = Estudiante(siguiente_id(gestor_estudiantes),
                            str(datos["nombre"]).strip().title(),
                            str(datos["apellido"]).strip().title(),
                            str(datos["email"]).strip().lower(),
                            str(datos["carnet"]).strip().upper(),
                            str(datos.get("carrera", "")).strip().title())
    if not guardar_nuevo(gestor_estudiantes, estudiante):
        return False, "No se pudo guardar el estudiante"
    return True, f"Estudiante creado: {estudiante.etiqueta()}"


def obtener_estudiantes():
    return leer_objetos(gestor_estudiantes, Estudiante)


def obtener_estudiante(id_estudiante):
    return obtener_por_id(gestor_estudiantes, Estudiante, id_estudiante)


def buscar_estudiantes(termino):
    return buscar(gestor_estudiantes, Estudiante, termino, CAMPOS_BUSCABLES_ESTUDIANTE)


def actualizar_estudiante(id_estudiante, cambios):
    estudiante = obtener_estudiante(id_estudiante)
    if estudiante is None:
        return False, f"No existe un estudiante con id {id_estudiante}"
    if not cambios:
        return False, "No se indicó ningún cambio"
    # DIFERENCIA de conjuntos: campos que no existen en un estudiante
    desconocidos = set(cambios) - set(CAMPOS_EDITABLES_ESTUDIANTE)
    if desconocidos:
        return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"
    # Se valida ANTES de tocar el objeto: si algo falla, no cambia nada
    error = validar_estudiante(cambios, id_estudiante)
    if error:
        return False, error
    for campo, valor in cambios.items():
        valor = str(valor).strip()
        if campo in ("nombre", "apellido", "carrera"):
            valor = valor.title()
        elif campo == "email":
            valor = valor.lower()
        elif campo == "carnet":
            valor = valor.upper()
        setattr(estudiante, campo, valor)
    reemplazar(gestor_estudiantes, estudiante)      # sin esto el cambio no llega al archivo
    return True, f"Estudiante {id_estudiante} actualizado"


def eliminar_estudiante(id_estudiante):
    if obtener_estudiante(id_estudiante) is None:
        return False, f"No existe un estudiante con id {id_estudiante}"
    eliminar(gestor_estudiantes, id_estudiante)
    return True, f"Estudiante {id_estudiante} eliminado"


def carreras_distintas():
    """CONJUNTO de carreras: sin repetidos. sorted() lo devuelve como lista ordenada."""
    return sorted({e.carrera for e in obtener_estudiantes() if e.carrera != ""})


# =====================================================================
# MATERIAS
# =====================================================================
def codigos_registrados(excepto_id=None):
    # CONJUNTO: el código de materia es único; 'in' responde al instante.
    return {r["codigo"].upper() for r in gestor_materias.leer()
            if r["id"] != excepto_id}


def validar_materia(datos, id_actual=None):
    """Devuelve un MENSAJE de error, o None si todo está bien."""
    for campo in OBLIGATORIOS_MATERIA:
        if id_actual is None or campo in datos:
            if str(datos.get(campo, "")).strip() == "":
                return f"El campo {campo} es obligatorio"
    if "codigo" in datos:
        codigo = str(datos["codigo"]).strip().upper()
        if codigo in codigos_registrados(id_actual):
            return f"El código {codigo} ya está registrado"
    if "creditos" in datos:
        creditos = str(datos["creditos"]).strip()
        if not creditos.isdigit() or not 1 <= int(creditos) <= 10:
            return "Los créditos deben ser un número entero entre 1 y 10"
    if "cupos" in datos and str(datos["cupos"]).strip() != "":
        cupos = str(datos["cupos"]).strip()
        if not cupos.isdigit() or not 0 <= int(cupos) <= Materia.CUPOS_MAXIMOS:
            return f"Los cupos deben ser un entero entre 0 y {Materia.CUPOS_MAXIMOS}"
    return None


def crear_materia(datos):
    error = validar_materia(datos)
    if error:
        return False, error
    cupos = str(datos.get("cupos", "")).strip()
    materia = Materia(siguiente_id(gestor_materias),
                      str(datos["nombre"]).strip().title(),
                      str(datos["codigo"]).strip().upper(),
                      int(datos["creditos"]),
                      int(cupos) if cupos != "" else 0)
    if not guardar_nuevo(gestor_materias, materia):
        return False, "No se pudo guardar la materia"
    return True, f"Materia creada: {materia.etiqueta()}"


def obtener_materias():
    return leer_objetos(gestor_materias, Materia)


def obtener_materia(id_materia):
    return obtener_por_id(gestor_materias, Materia, id_materia)


def buscar_materias(termino):
    return buscar(gestor_materias, Materia, termino, CAMPOS_BUSCABLES_MATERIA)


def actualizar_materia(id_materia, cambios):
    materia = obtener_materia(id_materia)
    if materia is None:
        return False, f"No existe una materia con id {id_materia}"
    if not cambios:
        return False, "No se indicó ningún cambio"
    desconocidos = set(cambios) - set(CAMPOS_EDITABLES_MATERIA)
    if desconocidos:
        return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"
    error = validar_materia(cambios, id_materia)
    if error:
        return False, error
    if "nombre" in cambios:
        materia.nombre = str(cambios["nombre"]).strip().title()
    if "codigo" in cambios:
        materia.codigo = str(cambios["codigo"]).strip().upper()
    if "creditos" in cambios:
        materia.creditos = int(cambios["creditos"])
    if "cupos" in cambios:
        materia.cupos = int(cambios["cupos"])
    reemplazar(gestor_materias, materia)
    return True, f"Materia {id_materia} actualizada"


def eliminar_materia(id_materia):
    if obtener_materia(id_materia) is None:
        return False, f"No existe una materia con id {id_materia}"
    eliminar(gestor_materias, id_materia)
    return True, f"Materia {id_materia} eliminada"


def materias_sin_cupo():
    return [materia for materia in obtener_materias() if not materia.hay_cupo()]


# =====================================================================
# MATRÍCULAS
# =====================================================================
def validar_matricula(datos):
    """Devuelve un MENSAJE de error, o None si todo está bien."""
    try:
        estudiante_id = int(datos.get("estudiante_id", 0))
        materia_id = int(datos.get("materia_id", 0))
    except (TypeError, ValueError):
        return "estudiante_id y materia_id deben ser números enteros"
    periodo = str(datos.get("periodo", "")).strip()
    if periodo == "":
        return "El periodo es obligatorio (ej: 2026-1)"
    # CONJUNTO de ids: ¿existen el estudiante y la materia?
    if estudiante_id not in ids_registrados(gestor_estudiantes):
        return f"No existe un estudiante con id {estudiante_id}"
    if materia_id not in ids_registrados(gestor_materias):
        return f"No existe una materia con id {materia_id}"
    # CONJUNTO de TUPLAS (estudiante, materia, periodo): se compara el trío
    # completo, no cada dato por separado.
    ya_matriculados = {(m.estudiante_id, m.materia_id, m.periodo)
                       for m in obtener_matriculas()}
    if (estudiante_id, materia_id, periodo) in ya_matriculados:
        return "Ese estudiante ya está matriculado en esa materia en ese periodo"
    materia = obtener_materia(materia_id)
    if not materia.hay_cupo():
        return f"No hay cupos en {materia.nombre}"
    return None


def crear_matricula(datos):
    # datos = {"estudiante_id": 1, "materia_id": 2, "periodo": "2026-1"}
    error = validar_matricula(datos)
    if error:
        return False, error
    materia = obtener_materia(int(datos["materia_id"]))
    matricula = Matricula(siguiente_id(gestor_matriculas),
                          int(datos["estudiante_id"]),
                          materia.id,
                          str(datos["periodo"]).strip())
    materia.ocupar_cupo()
    reemplazar(gestor_materias, materia)             # guarda el cupo nuevo en materias.json
    guardar_nuevo(gestor_matriculas, matricula)      # guarda la matrícula en matriculas.json
    return True, f"Matrícula {matricula.id} registrada en {materia.nombre}"


def obtener_matriculas():
    return leer_objetos(gestor_matriculas, Matricula)


def obtener_matricula(id_matricula):
    return obtener_por_id(gestor_matriculas, Matricula, id_matricula)


def registrar_nota(id_matricula, nota):
    matricula = obtener_matricula(id_matricula)
    if matricula is None:
        return False, f"No existe la matrícula {id_matricula}"
    if not Materia.es_nota_valida(nota):             # método ESTÁTICO de Materia
        return False, f"Nota inválida: '{nota}' (debe estar entre 0 y 20)"
    matricula.nota = float(str(nota).strip().replace(",", "."))
    reemplazar(gestor_matriculas, matricula)
    return True, f"Nota registrada: {matricula.nota:g} ({matricula.estado()})"


def retirar_matricula(id_matricula):
    """Borra la matrícula y devuelve el cupo a la materia."""
    matricula = obtener_matricula(id_matricula)
    if matricula is None:
        return False, f"No existe la matrícula {id_matricula}"
    materia = obtener_materia(matricula.materia_id)
    if materia is not None:
        materia.liberar_cupo()
        reemplazar(gestor_materias, materia)
    eliminar(gestor_matriculas, id_matricula)
    return True, f"Matrícula {id_matricula} retirada y cupo devuelto"


def certificado(id_matricula):
    matricula = obtener_matricula(id_matricula)
    if matricula is None:
        return None
    # DICCIONARIOS ÍNDICE {id: objeto}: cruzar tres entidades por id
    # sin recorrer listas dentro de listas.
    estudiantes = indice_por_id(gestor_estudiantes, Estudiante)
    materias = indice_por_id(gestor_materias, Materia)
    estudiante = estudiantes.get(matricula.estudiante_id)
    materia = materias.get(matricula.materia_id)
    nota = "sin calificar" if matricula.nota is None else f"{matricula.nota:g}"
    if estudiante:
        quien = f"{estudiante.nombre_completo()}   ({estudiante.carnet})"
    else:
        quien = "eliminado"
    if materia:
        que = f"{materia.nombre}   ({materia.codigo}) · {materia.creditos} créditos"
    else:
        que = "eliminada"
    texto = f"CERTIFICADO #{matricula.id}   periodo: {matricula.periodo}\n"
    texto += f"Estudiante: {quien}\n"
    texto += f"Materia   : {que}\n"
    texto += "-" * 42 + "\n"
    texto += f"Nota      : {nota}\n"
    texto += f"Estado    : {matricula.estado()}"
    return texto


def matriculas_por_estudiante():
    """DICCIONARIO de LISTAS: {estudiante_id: [matrículas de ese estudiante]}.
    Elegido porque cada estudiante tiene VARIAS matrículas y se accede por su id."""
    agrupadas = {}
    for matricula in obtener_matriculas():
        agrupadas.setdefault(matricula.estudiante_id, []).append(matricula)
    return agrupadas


def promedio_de_estudiante(id_estudiante):
    """Promedio de sus notas ya registradas, o None si todavía no tiene ninguna."""
    matriculas = matriculas_por_estudiante().get(id_estudiante, [])
    notas = [m.nota for m in matriculas if m.nota is not None]
    if not notas:
        return None
    return round(sum(notas) / len(notas), 2)


def matriculas_aprobadas():
    return sum(1 for matricula in obtener_matriculas() if matricula.esta_aprobada())