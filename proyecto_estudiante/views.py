from models import Estudiante, CAMPOS_ESTUDIANTE



# Importa la clase que lee y guarda la lista de clientes en el archivo JSON.
from shared.json_manager import GestorJSON
# Importa la función que revisa si un texto tiene formato de correo.
from shared.herramientas import es_email_valido


# Crea UN solo gestor para todo el módulo, apuntando al archivo de estudiantes.
gestor = GestorJSON("data/estudiantes.json")

# TUPLAS de configuración: fijas
CAMPOS_OBLIGATORIOS = ("nombre", "apellido", "email", "carnet")
CAMPOS_BUSCABLES = ("nombre", "apellido", "email", "carnet")


# ===================== AYUDAS INTERNAS =====================

# Devuelve un CONJUNTO con todos los emails guardados (en minúsculas).
# 'excepto_id' es opcional: sirve para ignorar el email de un cliente concreto
# (se usa al actualizar, para que un cliente no choque con su propio email).
def carnets_registrados(excepto_id=None):
    """CONJUNTO con los carnets ya usados. Sirve para detectar duplicados al instante."""
    return {
        registro["carnet"].strip().upper()
        for registro in gestor.leer()
        if registro["id"] != excepto_id
    }

# Devuelve un CONJUNTO con todos los emails guardados (en minúsculas).
def emails_registrados(excepto_id=None):
    """CONJUNTO con los emails ya usados."""
    return {
        registro["email"].lower()
        for registro in gestor.leer()
        if registro["id"] != excepto_id
    }

# Calcula el id que le toca al próximo Estudiante.
def siguiente_id():
    # COMPRENSIÓN DE LISTA: saca solo el "id" de cada registro. Ej: [1, 2, 5]
    ids = [registro["id"] for registro in gestor.leer()]
    # Si hay ids, toma el mayor y le suma 1 (ej: 5 + 1 = 6).
    # Si la lista está vacía (no hay clientes), empieza en 1.
    # (Si se elimina el cliente con el id más alto, ese id se vuelve a usar.)
    return max(ids) + 1 if ids else 1


# ===================== C · CREATE =====================

# Crea un cliente nuevo después de validar sus datos, y lo guarda en el archivo.
def crear_estudiante(datos):
    """datos: diccionario con las claves de CAMPOS_ESTUDIANTE. Devuelve (exito, mensaje)."""
    # try/except: si ocurre CUALQUIER error inesperado, el programa no se cae;
    # salta al 'except' del final y devuelve un mensaje de error.
    try:
        valores = {campo: str(datos.get(campo, "")).strip() for campo in CAMPOS_ESTUDIANTE}

        faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if not valores[campo]]
        # Una lista con elementos es True: si falta alguno, se detiene aquí.
        if faltantes:
            # ', '.join(lista) une los elementos con coma. Ej: "nombre, email"
            return False, f"Faltan campos obligatorios: {', '.join(faltantes)}"

        # 3) Formato del email
        # Si es_email_valido devuelve False, 'not' lo vuelve True y se rechaza.
        if not es_email_valido(valores["email"]):
            return False, f"El email '{valores['email']}' no tiene un formato válido"

        # 4) Validación de carnet no duplicado usando SET
        if valores["carnet"].upper() in carnets_registrados():
            return False, "Ese email ya está registrado"

        # 5) Validación de email único
        if valores["email"].lower() in emails_registrados():
            return False, "Ese email ya está registrado"

        # 6) Creo el objeto del Modelo
        estudiante = Estudiante(siguiente_id(), **valores)

        # 7) Agrego a la LISTA y guardo
        registros = gestor.leer()
        registros.append(estudiante.a_diccionario())
        if not gestor.guardar(registros):
            return False, "No se pudo escribir el archivo"

        return True, f"Estudiante {estudiante.obtener_nombre_completo()} creado con id {estudiante.id}"


    # 'Exception' atrapa cualquier error; 'as error' lo guarda en una variable
    # para poder mostrar su descripción en el mensaje.
    except Exception as error:
        return False, f"Error inesperado: {error}"


# ===================== R · READ =====================

# Devuelve todos los clientes guardados, ya convertidos en objetos Cliente.
def obtener_todos():
    """LISTA de objetos Estudiante."""
    return [Estudiante.desde_diccionario(registro) for registro in gestor.leer()]


def obtener_por_id(id_estudiante):
    for estudiante in obtener_todos():
        if estudiante.id == id_estudiante:
            return estudiante
    return None

# ===================== S · SEARCH =====================

# Busca clientes cuyo nombre, apellido, email, teléfono o ciudad CONTENGA el término.
def buscar_estudiantes(termino):
    """Búsqueda lineal: revisa registro por registro los campos de CAMPOS_BUSCABLES."""
    # Limpia espacios y pasa a minúsculas para que la búsqueda no distinga
    # mayúsculas: "ANA", "ana" y " Ana " encuentran lo mismo.
    termino = termino.strip().lower()
    # Si el término quedó vacío, no se busca nada: devuelve una lista vacía.
    # (Sin esto, "" estaría "dentro" de cualquier texto y devolvería a todos.)
    if not termino:
        return []

    # Lista donde se irán guardando los clientes que coincidan.
    encontrados = []
    # Ciclo externo: recorre cada cliente (como diccionario) del archivo.
    for registro in gestor.leer():
        # Ciclo interno: revisa cada campo buscable de ESE cliente.
        for campo in CAMPOS_BUSCABLES:                 # recorro la TUPLA de campos
            # registro.get(campo, "") -> valor del campo o "" si no existe.
            # str(...).lower()        -> texto en minúsculas.
            # 'termino in texto'      -> True si el término aparece en cualquier parte.
            if termino in str(registro.get(campo, "")).lower():
                # Coincidió: convierte el diccionario en objeto y lo agrega.
                encontrados.append(Estudiante.desde_diccionario(registro))
                break                                   # ya coincidió: paso al siguiente cliente
                # (el break evita agregar al mismo cliente dos veces si
                #  coincide en varios campos, ej. nombre y email)
    # Devuelve la lista de objetos Cliente encontrados (puede estar vacía).
    return encontrados


# ===================== U · UPDATE =====================

# Modifica solo los campos indicados en 'cambios' del cliente con ese id.
# Ej: actualizar_cliente(3, {"ciudad": "Milagro", "telefono": "0991234567"})
def actualizar_estudiante(id_estudiante, cambios):
    """cambios: diccionario solo con los campos que se quieren modificar."""
    try:
        # DIFERENCIA DE CONJUNTOS: ¿mandaron algún campo que no existe?
        # set(cambios) -> conjunto con las CLAVES del diccionario de cambios.
        # A - B        -> elementos que están en A pero NO en B.
        # Ej: {"ciudad", "edad"} - {"nombre", ..., "ciudad", ...} -> {"edad"}
        # Esto también impide cambiar el "id", porque no está en CAMPOS_CLIENTE.
        desconocidos = set(cambios) - set(CAMPOS_ESTUDIANTE)
        # Si hay campos desconocidos, se rechaza y se listan ordenados.
        if desconocidos:
            return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"

        # Un diccionario vacío {} es False: si no hay nada que cambiar, se avisa.
        if not cambios:
            return False, "No se indicó ningún cambio"

        # Solo si se quiere cambiar el email, se hacen dos validaciones extra.
        if "email" in cambios:
            # a) Que tenga formato de correo.
            if not es_email_valido(cambios["email"]):
                return False, "El email no tiene un formato válido"
            # b) Que no lo tenga OTRO cliente. Se excluye al propio cliente
            #    (excepto_id) para que pueda volver a guardar su mismo email.
            if cambios["email"].lower() in emails_registrados(excepto_id=id_estudiante):
                return False, "Ese email ya lo usa otro cliente"

        registros = gestor.leer()
        posicion = None
        for indice, registro in enumerate(registros):
            if registro["id"] == id_estudiante:
                posicion = indice
                break

        if posicion is None:
            return False, f"No existe un estudiante con id {id_estudiante}"

        registros[posicion].update(cambios)
        gestor.guardar(registros)
        return True, f"Estudiante {id_estudiante} actualizado ({len(cambios)} campo/s)"

    except Exception as error:
        return False, f"Error inesperado: {error}"


# ===================== D · DELETE =====================

def eliminar_estudiante(id_estudiante):
    registros = gestor.leer()
    quedan = [registro for registro in registros if registro["id"] != id_estudiante]

    if len(quedan) == len(registros):
        return False, f"No existe un estudiante con id {id_estudiante}"

    gestor.guardar(quedan)
    return True, f"Estudiante {id_estudiante} eliminado"


# ===================== EXTRA: estadísticas con conjuntos =====================

def agregar_nota(id_estudiante, materia, nota):
    """Agrega una nota (entre 0 y 20) al estudiante indicado."""
    if not (0 <= nota <= 20):
        return False, "La nota debe estar entre 0 y 20"

    estudiante = obtener_por_id(id_estudiante)
    if not estudiante:
        return False, f"No existe el estudiante con ID {id_estudiante}"

    estudiante.agregar_nota(materia, nota)
    
    # Guardamos los cambios en el archivo JSON
    registros = gestor.leer()
    for i, reg in enumerate(registros):
        if reg["id"] == id_estudiante:
            registros[i] = estudiante.a_diccionario()
            break
    
    gestor.guardar(registros)
    return True, f"Nota {nota} agregada en {materia} a {estudiante.nombre}"


def materias_ofertadas():
    """Devuelve un SET con todas las materias inscritas por los estudiantes, sin repetir."""
    estudiantes = obtener_todos()
    todas_materias = set()
    for est in estudiantes:
        todas_materias.update(est.materias)
    return todas_materias


def estudiante_en_comun(id_a, id_b):
    """Usa la intersección de conjuntos para devolver las materias compartidas."""
    est_a = obtener_por_id(id_a)
    est_b = obtener_por_id(id_b)

    if not est_a or not est_b:
        return set()

    return est_a.materias_en_comun(est_b)

# ------------------------------------------------------------------
# PRUEBA DE LAS FUNCIONES
# Este bloque SOLO se ejecuta si corres este archivo directamente:
#     python views.py
# Si main.py importa este archivo, este bloque NO se ejecuta.
#
# Cómo leer la prueba: cada función se llama, su resultado se guarda
# en una variable y se imprime. En el texto dice qué deberías ver.
# ------------------------------------------------------------------
if __name__ == "__main__":
    from shared.herramientas import imprimir_titulo, imprimir_info, imprimir_exito

    imprimir_titulo("PRUEBA DE views.py (Estudiantes)")

    gestor = GestorJSON("data/estudiantes_prueba.json")
    gestor.guardar([])
    imprimir_info("Se usa el archivo data/estudiantes_prueba.json")

    # 1. Crear Estudiantes
    est1 = {"nombre": "Ana", "apellido": "Pérez", "email": "ana@gmail.com", "carnet": "EST001"}
    est2 = {"nombre": "Luis", "apellido": "Mora", "email": "luis@gmail.com", "carnet": "EST002"}
    crear_estudiante(est1)
    crear_estudiante(est2)

    # 2. Agregar Notas
    print("\n===== Agregar Notas =====")
    print(agregar_nota(1, "Matemáticas", 18))
    print(agregar_nota(1, "Física", 15))
    print(agregar_nota(2, "Matemáticas", 17))
    print("Nota inválida (debe fallar):", agregar_nota(1, "Química", 25))

    # 3. Materias Ofertadas
    print("\n===== Materias Ofertadas =====")
    print("Materias globales:", materias_ofertadas())

    # 4. Materias en común
    print("\n===== Materias en Común =====")
    print("Materias que comparten 1 y 2:", estudiante_en_comun(1, 2))

    # Limpiar archivo de prueba
    gestor.guardar([])
    print()
    imprimir_exito("Fin de las pruebas")