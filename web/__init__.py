"""El servicio web de Gachamon."""

# Todo cuelga de aquí. Vive en el paquete y no en `web.app` para que otros
# módulos de `web` armen direcciones con él sin importar la app (sería un ciclo).
PREFIJO = "/monsteropolis"
# La dirección de antes: lo que cuelga de ella redirige (308) a la misma ruta bajo
# `PREFIJO`, para las páginas abiertas, los marcadores y los enlaces ya escritos.
PREFIJO_ANTIGUO = "/gachamon"
