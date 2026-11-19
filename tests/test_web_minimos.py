"""Con los muebles que se usan solos, ninguna barra se ve por debajo de su mínimo.

La fila de la base sí puede quedar por debajo: un cuidado que gasta la deja así, y
el mínimo se aplica al leer, en `db.avanzar`. Por eso aquí cada ruta que enseña
barras —o las dice en una frase, o enseña la cara que sale de ellas— se llama con
las filas crudas por debajo del mínimo, y se mira todo lo que contesta.

Las lecturas crudas que quedan en `web/` las vigila la guarda de
`tests/test_web_app.py`.
"""
import re
from dataclasses import replace

import cosmeticos as cos
import db
import departamento as dep
import especies as esp
import identidad
import objetos
import simulacion as sim
from ayudas_web import ESCRIBIR, PUEBLO, con_gachamon, con_monedas_web, en_casa, poner_reloj
from test_web_departamento import un_mueble

API = "/gachamon/api"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)
MINIMO = dep.MINIMO_SOSTENIDO
# Lo que se deja a mano en la fila: por debajo del mínimo, y también de 30, que
# con la fila cruda pondría la cara de «mal».
CRUDA = 10.0
AHORA = re.compile(r"\(ahora (\d+)\)")


def por_debajo(ahora):
    """Deja la fila de cada vivo con las tres barras en `CRUDA`, al día en `ahora`."""
    for criatura in db.plantel(YO, G):
        db.guardar(replace(criatura, hambre=CRUDA, animo=CRUDA, limpieza=CRUDA, actualizada_en=ahora))


def recorrer(cuerpo, donde, vistas, malas):
    """Apunta en `vistas` cada barra, frase con «(ahora N)» o cara que enseña la
    respuesta, y en `malas` las que están por debajo del mínimo."""
    if isinstance(cuerpo, list):
        for i, valor in enumerate(cuerpo):
            recorrer(valor, f"{donde}[{i}]", vistas, malas)
        return
    if not isinstance(cuerpo, dict):
        return
    for clave, valor in cuerpo.items():
        aqui = f"{donde}.{clave}"
        if clave == "barras":
            vistas.append(aqui)
            malas += [f"{aqui}.{barra} = {n}" for barra, n in valor.items() if n < MINIMO]
        elif clave in ("cara", "retrato"):
            vistas.append(aqui)
            if valor == esp.MAL or f"/{esp.MAL}/" in valor:
                malas.append(f"{aqui} = {valor}")
        elif isinstance(valor, str):
            for n in AHORA.findall(valor):
                vistas.append(aqui)
                if int(n) < MINIMO:
                    malas.append(f"{aqui} = «{valor}»")
        else:
            recorrer(valor, aqui, vistas, malas)


def test_con_el_refrigerador_la_consola_y_la_ducha_ninguna_ruta_ensena_una_barra_por_debajo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente); en_casa(cliente); con_monedas_web(cliente, 1000)
    pelusa = db.criatura_activa(YO, G)
    rulo = db.crear(YO, G, "pollito", "Rulo", (10, 10, 10, 10), reloj.ahora, activa=False, se_nombro_solo=True)
    # Las dos camas de partida van en (0, 0) y (0, 1); la tercera es la de Rulo.
    for clave, x, y in (("refrigerador", 2, 0), ("consola", 2, 1), ("ducha", 2, 2), ("cama_sencilla", 0, 2)):
        un_mueble(clave, x, y)
    maceta = un_mueble("maceta")                               # guardada
    db.regalar(YO, G, objetos.CATALOGO["golosinas"])
    titulo = cos.del_tipo(cos.TITULO)[0]
    with db.conectar() as con:
        db.guardar_en_el_ropero_en(con, YO, G, titulo.clave)
    eventos = iter(f"evento-minimo-{n:03d}" for n in range(100))
    malas = []

    def pedir(ruta, cuerpo=None, metodo="POST"):
        """La pide con las filas por debajo y apunta lo que se ve por debajo."""
        por_debajo(reloj.ahora)
        if metodo == "GET":
            r = cliente.get(f"{API}/{ruta}")
        else:
            r = cliente.post(f"{API}/{ruta}", json=cuerpo, headers=ESCRIBIR)
        que = f"{metodo} {ruta} {cuerpo or ''}".rstrip()
        assert r.status_code == 200, (que, r.text)
        vistas, aqui = [], []
        recorrer(r.json(), "", vistas, aqui)
        assert vistas, f"{que} no enseña ninguna barra"
        malas.extend(f"{que}: {m}" for m in aqui)
        return r.json()

    # Entrenar en el mínimo deja la fila por debajo; la barra, no.
    assert pedir("cuidar", {"accion": sim.ENTRENAR, "evento_id": next(eventos)})["ok"]
    assert db.criatura_activa(YO, G).hambre < MINIMO
    reloj.pasar(hours=2)                                      # lo que espera entrenar

    pedir("estado", metodo="GET")
    pedir("departamento", metodo="GET")
    pedir("ficha", metodo="GET")
    for gachamon in (pelusa, rulo):
        pedir(f"ficha?gachamon_id={gachamon.id}", metodo="GET")

    # Cada cuidado, al que sale contigo y a otro; y el replay de uno.
    for accion in sim.ACCIONES_DE_CUIDADO:
        assert pedir("cuidar", {"accion": accion, "evento_id": next(eventos)})["ok"]
        cuidado = {"accion": accion, "evento_id": next(eventos), "gachamon_id": rulo.id}
        assert pedir("cuidar", cuidado)["ok"]
    pedir("cuidar", cuidado)
    reloj.pasar(hours=2)
    for accion in sim.ACCIONES_DE_CUIDADO:
        assert pedir("cuidar/todos", {"accion": accion, "evento_id": next(eventos)})["ok"]
    pedir("acariciar")
    pedir("acariciar", {"gachamon_id": rulo.id})

    # La comida de la mochila, y el replay del mismo uso.
    uso = {"clave": "golosinas", "evento_id": next(eventos)}
    for _ in range(2):
        assert "(ahora " in pedir("mochila/usar", uso)["mensaje"]

    pedir("bautizar", {"nombre": "Brisa", "gachamon_id": rulo.id})
    assert pedir("ropero/poner", {"clave": titulo.clave, "gachamon_id": pelusa.id})["ok"]
    assert pedir("ropero/quitar", {"tipo": cos.TITULO, "gachamon_id": pelusa.id})["ok"]

    # En tu casa: salir con otro, ampliar, poner y guardar.
    assert pedir("departamento/salir", {"gachamon_id": rulo.id})["ok"]
    assert pedir("departamento/salir", {"gachamon_id": pelusa.id})["ok"]
    assert pedir("departamento/ampliar", {"eje": "ancho", "evento_id": next(eventos)})["ok"]
    assert pedir("departamento/poner", {"mueble_id": maceta, "x": 3, "y": 0, "giro": 0})["ok"]
    assert pedir("departamento/guardar", {"mueble_id": maceta})["ok"]

    # La Incubadora y la Tienda.
    pedir("lugar", {"lugar": "incubadora"})
    pedir("incubadora", metodo="GET")
    assert pedir("incubadora/sacar", {"gachamon_id": rulo.id})["ok"]
    pedir("lugar", {"lugar": "tienda"})
    assert pedir("tienda/comprar", {"que": "objeto", "clave": "golosinas", "evento_id": next(eventos)})["ok"]

    assert not malas, "\n".join(malas)
