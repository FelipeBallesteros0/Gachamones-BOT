"""Perfiles ICC fabricados a mano, sólo para las pruebas: no se commitea ningún `.icc` de fuera."""
import struct

D50 = (0.9642, 1.0, 0.8249)
BRADFORD = ((0.8951, 0.2664, -0.1614), (-0.7502, 1.7135, 0.0367), (0.0389, -0.0685, 1.0296))


def _por(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _producto(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _inversa(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    adj = ((e * i - f * h, c * h - b * i, b * f - c * e),
           (f * g - d * i, a * i - c * g, c * d - a * f),
           (d * h - e * g, b * g - a * h, a * e - b * d))
    return tuple(tuple(x / det for x in fila) for fila in adj)


def _xyz(xy):
    x, y = xy
    return (x / y, 1.0, (1 - x - y) / y)


def _s15(v):
    return struct.pack(">i", round(v * 65536))


def perfil_rgb(primarios, blanco, gamma) -> bytes:
    """Un perfil ICC v2 de matriz y curva: `primarios` son las cromaticidades xy de rojo, verde y
    azul; `blanco`, la xy del blanco; `gamma`, la de la única curva de los tres canales."""
    columnas = [_xyz(p) for p in primarios]
    base = tuple(tuple(columnas[j][i] for j in range(3)) for i in range(3))
    escala = _por(_inversa(base), _xyz(blanco))
    matriz = tuple(tuple(base[i][j] * escala[j] for j in range(3)) for i in range(3))
    # Los colorantes se guardan adaptados al D50 del espacio de conexión (Bradford).
    cono_origen, cono_d50 = _por(BRADFORD, _xyz(blanco)), _por(BRADFORD, D50)
    diagonal = tuple(tuple(cono_d50[i] / cono_origen[i] if i == j else 0.0 for j in range(3)) for i in range(3))
    adaptacion = _producto(_inversa(BRADFORD), _producto(diagonal, BRADFORD))
    adaptada = _producto(adaptacion, matriz)
    etiquetas = {b"wtpt": b"XYZ \0\0\0\0" + b"".join(_s15(v) for v in D50)}
    for i, firma in enumerate((b"rXYZ", b"gXYZ", b"bXYZ")):
        etiquetas[firma] = b"XYZ \0\0\0\0" + b"".join(_s15(adaptada[f][i]) for f in range(3))
    curva = b"curv\0\0\0\0" + struct.pack(">IH", 1, round(gamma * 256)) + b"\0\0"
    for firma in (b"rTRC", b"gTRC", b"bTRC"):
        etiquetas[firma] = curva
    indice, cuerpo = b"", b""
    desplazamiento = 128 + 4 + 12 * len(etiquetas)
    for firma, datos in etiquetas.items():
        indice += firma + struct.pack(">II", desplazamiento + len(cuerpo), len(datos))
        cuerpo += datos
    cabecera = (struct.pack(">I", desplazamiento + len(cuerpo)) + b"\0\0\0\0" + b"\x02\x40\0\0"
                + b"mntrRGB XYZ " + struct.pack(">6H", 2026, 1, 1, 0, 0, 0) + b"acsp"
                + b"\0" * 24 + b"".join(_s15(v) for v in D50)).ljust(128, b"\0")
    return cabecera + struct.pack(">I", len(etiquetas)) + indice + cuerpo
