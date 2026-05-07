from collections import defaultdict


def construir_grafo_conflictos(clases):

    grafo = defaultdict(set)
    n = len(clases)
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = clases[i], clases[j]
            if ci["grupo"] == cj["grupo"] or ci["docente"] == cj["docente"]:
                grafo[ci["id"]].add(cj["id"])
                grafo[cj["id"]].add(ci["id"])
    # Garantizar que todos los nodos esten presentes aunque no tengan vecinos
    for c in clases:
        if c["id"] not in grafo:
            grafo[c["id"]] = set()
    return dict(grafo)


def coloreo_voraz_greedy(grafo, orden):

    coloracion = {}
    for nodo in orden:
        colores_vecinos = {coloracion[v] for v in grafo.get(nodo, set()) if v in coloracion}
        color = 1
        while color in colores_vecinos:
            color += 1
        coloracion[nodo] = color
    return coloracion


def coloreo_dsatur(grafo):

    coloracion = {}
    saturacion = {nodo: 0 for nodo in grafo}
    paleta_vecinos = {nodo: set() for nodo in grafo}
    pendientes = set(grafo.keys())

    while pendientes:
        # Seleccionar nodo con mayor saturacion; desempate: mayor grado
        nodo = max(
            pendientes,
            key=lambda v: (saturacion[v], len(grafo.get(v, set())), v),
        )
        # Asignar el menor color no usado por los vecinos
        color = 1
        while color in paleta_vecinos[nodo]:
            color += 1
        coloracion[nodo] = color
        pendientes.remove(nodo)
        # Actualizar saturacion de vecinos aun no coloreados
        for vecino in grafo.get(nodo, set()):
            if vecino in pendientes:
                paleta_vecinos[vecino].add(color)
                saturacion[vecino] = len(paleta_vecinos[vecino])

    return coloracion


def coloreo_voraz_greedy_disponibilidad(grafo, orden, docente_clase, bloques_prohibidos):

    coloracion = {}
    for nodo in orden:
        docente = docente_clase.get(nodo)
        # Bloques que el docente no puede cubrir segun su disponibilidad
        prohibidos = bloques_prohibidos.get(docente, set())
        paleta_vecinos = {coloracion[v] for v in grafo.get(nodo, set()) if v in coloracion}
        # Vetados = conflictos con vecinos + restricciones de disponibilidad
        vetados = paleta_vecinos | prohibidos
        color = 1
        while color in vetados:
            color += 1
        coloracion[nodo] = color
    return coloracion


def coloreo_dsatur_disponibilidad(grafo, docente_clase, bloques_prohibidos):

    coloracion = {}
    saturacion = {nodo: 0 for nodo in grafo}
    paleta_vecinos = {nodo: set() for nodo in grafo}
    pendientes = set(grafo.keys())

    while pendientes:
        # Seleccionar nodo con mayor saturacion; desempate: mayor grado
        nodo = max(
            pendientes,
            key=lambda v: (saturacion[v], len(grafo.get(v, set())), v),
        )
        docente = docente_clase.get(nodo)
        # Bloques que el docente no puede cubrir segun su disponibilidad
        prohibidos = bloques_prohibidos.get(docente, set())
        # Asignar el menor color no usado por los vecinos ni prohibido
        vetados = paleta_vecinos[nodo] | prohibidos
        color = 1
        while color in vetados:
            color += 1
        coloracion[nodo] = color
        pendientes.remove(nodo)
        # Actualizar saturacion de vecinos aun no coloreados
        for vecino in grafo.get(nodo, set()):
            if vecino in pendientes:
                paleta_vecinos[vecino].add(color)
                saturacion[vecino] = len(paleta_vecinos[vecino])

    return coloracion
