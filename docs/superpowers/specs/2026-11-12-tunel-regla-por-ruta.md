# El túnel y la regla por ruta, comprobada en seco

Fecha: 2026-11-12. Tarea 7 del plan «web 1: reglas y bot».

## Qué se quería saber

El juego va a servirse en `rowino.online/gachamon` desde un servicio
distinto del que hoy atiende todo `rowino.online`. Los dos salen por el
mismo túnel de Cloudflare, que corre en la Raspberry Pi. Si el túnel puede
repartir por ruta, Rowino casi no se toca. Si no, Rowino tiene que reenviar
esa ruta y el plan 2 crece.

## Cómo se probó

Sin cambiar nada en producción. `cloudflared` puede validar un archivo de
reglas y decir qué regla atendería una dirección, sin abrir conexiones ni
reiniciar nada.

1. Se leyó la configuración real (`/etc/cloudflared/config.yml`), sólo
   lectura.
2. Se escribió una copia en `/tmp/tunel-prueba.yml` con una regla nueva
   justo antes de la única regla de `rowino.online`.
3. Se validó la copia y se preguntó por seis direcciones con
   `cloudflared tunnel --config /tmp/tunel-prueba.yml ingress rule <url>`.
4. Se borró la copia. Se comprobó después que ya no existe.

Versión: `cloudflared version 2026.7.1 (built 2026-07-09-12:59 UTC)`.

## La regla probada

```yaml
  - hostname: rowino.online
    path: ^/gachamon(/.*)?$
    service: http://localhost:8010
```

Va antes de la regla de `rowino.online` sin ruta, que sigue mandando a
`http://localhost:8000`. El orden importa: gana la primera que coincide.

## Resultado

La validación dijo `OK`.

| Dirección | Regla que atendió | Servicio |
|---|---|---|
| `https://rowino.online/gachamon` | la nueva (con `path`) | `http://localhost:8010` |
| `https://rowino.online/gachamon/` | la nueva | `http://localhost:8010` |
| `https://rowino.online/gachamon/api/estado` | la nueva | `http://localhost:8010` |
| `https://rowino.online/generar` | la de `rowino.online` sin ruta | `http://localhost:8000` |
| `https://rowino.online/gachamones` | la de `rowino.online` sin ruta | `http://localhost:8000` |
| `https://rowino.online/` | la de `rowino.online` sin ruta | `http://localhost:8000` |

Todo salió como se esperaba. `/gachamones` no cae en la regla nueva: la
expresión pide `/gachamon` seguido de `/` o del fin de la dirección.

## Conclusión

La regla por ruta sirve: el túnel puede mandar `rowino.online/gachamon/*` a
otro servicio sin que Rowino reenvíe nada.

## Lo que no se probó

- No se aplicó la regla de verdad. Eso pide `sudo` para editar
  `/etc/cloudflared/config.yml` y reiniciar el túnel.
- Reiniciar el túnel corta unos segundos todos los sitios que salen por él.
  Hace falta la autorización de Felipe en el momento.
- No se hizo ninguna petición real por internet: `ingress rule` sólo dice
  qué regla se elegiría, no prueba que el servicio nuevo responda.
- El puerto 8010 es el del plan; todavía no hay nada escuchando ahí.

Todo eso es del plan 2.
