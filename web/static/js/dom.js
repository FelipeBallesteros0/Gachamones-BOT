// La única forma en que el cliente crea elementos.
//
// `el('button', {class: 'boton', onclick: f}, 'Texto')`. Los atributos `on…`
// se escuchan como eventos y tienen que ser una función: otra cosa sería un
// manejador en línea, y es un error de programación. `true` pone el atributo
// vacío y `false`, `null` o `undefined` no lo ponen. Los hijos de texto entran
// como nodos de texto, así que nada de lo que se escribe se lee como marcado.
export function el(etiqueta, atributos, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [nombre, valor] of Object.entries(atributos || {})) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (nombre.toLowerCase().startsWith('on')) {
      if (typeof valor !== 'function') throw new TypeError(`«${nombre}» tiene que ser una función`);
      nodo.addEventListener(nombre.slice(2), valor);
    } else {
      nodo.setAttribute(nombre, valor === true ? '' : String(valor));
    }
  }
  for (const hijo of hijos.flat()) {
    if (hijo === false || hijo === null || hijo === undefined) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}
