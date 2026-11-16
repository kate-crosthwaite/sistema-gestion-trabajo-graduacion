// Kate Crosthwaite · 8-1009-1386
// Comportamiento de la interfaz del SGME: confirmaciones, contadores, resumen de evaluación,
// documentos requeridos por modalidad con validación previa de archivos y contraseña visible.
(function () {
  const $ = (selector, raiz = document) => raiz.querySelector(selector);
  const $$ = (selector, raiz = document) => Array.from(raiz.querySelectorAll(selector));

  const menu = $('#menu-lateral');
  if (menu) menu.addEventListener('click', () => $('#app').classList.toggle('sin-lateral'));

  const dialogo = $('#dialogo');
  function mostrar(texto, conCancelar) {
    return new Promise(resolver => {
      $('#dialogo-texto').textContent = texto;
      $('#dialogo-no').hidden = !conCancelar;
      dialogo.returnValue = '';
      dialogo.addEventListener('close', () => resolver(dialogo.returnValue === 'si'), { once: true });
      dialogo.showModal();
    });
  }

  document.addEventListener('click', async evento => {
    const requiere = evento.target.closest('[data-requiere]');
    if (requiere) {
      const campo = $(requiere.dataset.requiere);
      if (!campo.value.trim()) {
        evento.preventDefault();
        const contenedor = campo.closest('.campo');
        contenedor.classList.add('invalido');
        if (!$('.error-campo', contenedor)) {
          const aviso = crearElemento('span', 'error-campo', requiere.dataset.mensajeRequiere);
          aviso.setAttribute('role', 'alert');
          contenedor.append(aviso);
          campo.addEventListener('input', () => { aviso.remove(); contenedor.classList.remove('invalido'); }, { once: true });
        }
        campo.focus();
        return;
      }
    }
    const elemento = evento.target.closest('[data-confirmar]');
    if (!elemento) return;
    evento.preventDefault();
    if (await mostrar(elemento.dataset.confirmar, true)) {
      if (elemento.tagName === 'A') window.location.href = elemento.href;
      else elemento.form.requestSubmit(elemento);
    }
  });

  $$('textarea[data-max]').forEach(area => {
    const contador = $(area.dataset.contador);
    const actualizar = () => {
      contador.textContent = area.value.length + ' / ' + area.dataset.max;
      contador.classList.toggle('excede', area.value.length > Number(area.dataset.max));
    };
    area.addEventListener('input', actualizar);
    actualizar();
  });

  const evaluaciones = $$('select.eval');
  function resumir() {
    const cuenta = { CUMPLE: 0, PENDIENTE: 0, NO_CUMPLE: 0 };
    evaluaciones.forEach(s => { s.dataset.valor = s.value; if (s.value in cuenta) cuenta[s.value]++; });
    Object.keys(cuenta).forEach(k => $$('[data-cuenta="' + k + '"]').forEach(e => { e.textContent = cuenta[k]; }));
  }
  evaluaciones.forEach(s => s.addEventListener('change', resumir));
  if (evaluaciones.length) resumir();

  const ver = $('#ver-clave');
  if (ver) {
    ver.addEventListener('click', () => {
      const entrada = $('#contrasena');
      const oculta = entrada.type === 'password';
      entrada.type = oculta ? 'text' : 'password';
      ver.textContent = oculta ? 'Ocultar' : 'Mostrar';
    });
  }

  const facultad = $('#facultad'), carrera = $('#carrera');
  if (facultad && carrera) {
    const filtrar = () => $$('option', carrera).forEach(o => {
      if (!o.value) return;
      const fuera = Boolean(facultad.value) && o.dataset.facultad !== facultad.value;
      o.hidden = o.disabled = fuera;
      if (fuera && o.selected) { carrera.value = ''; carrera.dispatchEvent(new Event('change')); }
    });
    facultad.addEventListener('change', filtrar);
    filtrar();
  }

  const datos = $('#datos-docs');
  if (datos) {
    const D = JSON.parse(datos.textContent);
    const ETIQUETA = { PENDIENTE: 'Pendiente', CARGADO: 'Cargado', OPCIONAL: 'Opcional' };
    const FORMATOS = ['pdf', 'docx'], MAXIMO = 20 * 1024 * 1024;
    const MSG_FORMATO = 'El formato del archivo no es permitido. Solo se aceptan archivos PDF y DOCX.';
    const MSG_TAMANO = 'El archivo excede el tamaño máximo permitido de 20 MB.';
    const modalidad = $('#modalidad'), contenedor = $('#documentos');
    const ICONO_SUBIR = '<svg class="ico" xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>';

    const crear = (etiqueta, atributos = {}, texto = '') => {
      const e = document.createElement(etiqueta);
      Object.entries(atributos).forEach(([k, v]) => e.setAttribute(k, v));
      e.textContent = texto;
      return e;
    };

    function pintar() {
      const requeridos = D.requeridos.filter(r => String(r.modalidad_id) === modalidad.value);
      contenedor.replaceChildren();
      if (!requeridos.length) {
        contenedor.append(crear('p', { class: 'vacio' }, 'Seleccione una modalidad para ver los documentos requeridos.'));
        return;
      }
      const envoltura = crear('div', { class: 'tabla-envoltura' });
      const tabla = crear('table', { class: 'tabla' });
      const cabecera = crear('tr');
      ['Documento', 'Descripción', 'Estado', 'Archivo', 'Acción'].forEach(t => cabecera.append(crear('th', {}, t)));
      const encabezado = crear('thead');
      encabezado.append(cabecera);
      const cuerpo = crear('tbody');
      tabla.append(encabezado, cuerpo);
      requeridos.forEach(r => {
        const actual = D.actuales[r.id] || {};
        const estado = actual.estado || (r.obligatorio ? 'PENDIENTE' : 'OPCIONAL');
        const fila = crear('tr', D.errores.includes('doc_' + r.id) ? { class: 'invalido-fila' } : {});
        const insignia = crear('span', { class: 'badge b-doc-' + estado.toLowerCase() }, ETIQUETA[estado]);
        const archivo = crear('span', {}, actual.archivo || 'No cargado');
        const mensaje = crear('span', { class: 'msg-doc' }, D.mensajes[r.id] || '');
        const entrada = crear('input', { type: 'file', name: 'doc_' + r.id, accept: '.pdf,.docx', hidden: '' });
        const boton = crear('label', { class: 'btn btn-sec btn-sm' });
        boton.innerHTML = ICONO_SUBIR + ' ' + (actual.archivo ? 'Reemplazar' : 'Seleccionar');
        boton.append(entrada);
        entrada.addEventListener('change', () => {
          const f = entrada.files[0];
          mensaje.textContent = '';
          if (!f) return;
          const extension = f.name.split('.').pop().toLowerCase();
          if (!FORMATOS.includes(extension)) { mensaje.textContent = MSG_FORMATO; entrada.value = ''; return; }
          if (f.size > MAXIMO) { mensaje.textContent = MSG_TAMANO; entrada.value = ''; return; }
          archivo.textContent = f.name + ' (sin guardar)';
          insignia.className = 'badge b-doc-cargado';
          insignia.textContent = ETIQUETA.CARGADO;
        });
        const celdaNombre = crear('td', {}, r.nombre);
        if (r.obligatorio) celdaNombre.append(crear('i', { class: 'req' }, '*'));
        const celdaArchivo = crear('td'); celdaArchivo.append(archivo, mensaje);
        const celdaEstado = crear('td'); celdaEstado.append(insignia);
        const celdaAccion = crear('td', { class: 'der' }); celdaAccion.append(boton);
        fila.append(celdaNombre, crear('td', {}, r.descripcion || ''), celdaEstado, celdaArchivo, celdaAccion);
        cuerpo.append(fila);
      });
      envoltura.append(tabla);
      contenedor.append(envoltura);
    }
    const formulario = modalidad.closest('form');
    function actualizarProgreso() {
      const campos = ['telefono', 'modalidad_id', 'titulo', 'asesor_id', 'descripcion'].map(n => formulario.elements[n]).filter(Boolean);
      let total = campos.length, hechos = campos.filter(c => c.value.trim()).length;
      D.requeridos.filter(r => String(r.modalidad_id) === modalidad.value && r.obligatorio).forEach(r => {
        total++;
        const entrada = formulario.elements['doc_' + r.id];
        if ((D.actuales[r.id] && D.actuales[r.id].archivo) || (entrada && entrada.files.length)) hechos++;
      });
      const porcentaje = total ? Math.round(hechos * 100 / total) : 0;
      $('#progreso-relleno').style.width = porcentaje + '%';
      $('#progreso-texto').textContent = porcentaje + '%';
      $('#progreso-detalle').textContent = porcentaje === 100 ? 'Todo listo: ya puedes enviar tu solicitud.'
        : hechos + ' de ' + total + ' requisitos completados.';
    }
    modalidad.addEventListener('change', () => { pintar(); actualizarProgreso(); });
    formulario.addEventListener('input', actualizarProgreso);
    formulario.addEventListener('change', actualizarProgreso);
    pintar();
    actualizarProgreso();
  }

  // Desplegables propios: el <select> original se conserva oculto para enviar el formulario y como respaldo sin JavaScript.
  const svg = (trazos, tam = 16) => '<svg class="ico" xmlns="http://www.w3.org/2000/svg" width="' + tam + '" height="' + tam + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + trazos + '</svg>';
  const FLECHA = svg('<polyline points="6 9 12 15 18 9"/>', 16);
  const MARCA = svg('<polyline points="20 6 9 17 4 12"/>', 15);
  const ICONOS_EVAL = {
    CUMPLE: svg('<circle cx="12" cy="12" r="10"/><polyline points="8 12 11 15 16 9"/>', 16),
    PENDIENTE: svg('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>', 16),
    NO_CUMPLE: svg('<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>', 16)
  };
  let abierto = null;
  let contador = 0;

  function mejorarSelect(select) {
    const evaluacion = select.classList.contains('eval');
    const id = 'sel-' + (++contador);
    const envoltura = crearElemento('div', 'sel' + (evaluacion ? ' sel-eval' : ''));
    const boton = crearElemento('button', 'sel-boton');
    boton.type = 'button';
    boton.setAttribute('aria-haspopup', 'listbox');
    boton.setAttribute('aria-expanded', 'false');
    boton.setAttribute('aria-controls', id);
    const icono = crearElemento('span', 'sel-ico');
    const texto = crearElemento('span', 'sel-texto');
    const flecha = crearElemento('span', 'sel-flecha');
    flecha.innerHTML = FLECHA;
    boton.append(icono, texto, flecha);
    const lista = crearElemento('ul', 'sel-lista');
    lista.id = id;
    lista.setAttribute('role', 'listbox');
    lista.hidden = true;
    select.parentNode.insertBefore(envoltura, select);
    envoltura.append(boton, lista, select);
    select.classList.add('sel-nativo');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');

    const etiqueta = select.getAttribute('aria-label') || (select.closest('label')
      ? Array.from(select.closest('label').childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim() : '');
    let items = [], activo = -1, busqueda = '', temporizador = null;

    function sincronizar() {
      const opcion = select.selectedOptions[0];
      const vacia = !select.value;
      texto.textContent = opcion ? opcion.textContent.trim() : '';
      boton.classList.toggle('sel-vacio', vacia);
      boton.dataset.valor = select.value;
      icono.innerHTML = evaluacion && select.value ? ICONOS_EVAL[select.value] : '';
      boton.setAttribute('aria-label', (etiqueta ? etiqueta + ': ' : '') + texto.textContent);
    }

    function pintar() {
      lista.replaceChildren();
      items = Array.from(select.options).filter(o => !o.hidden && !o.disabled);
      items.forEach((o, i) => {
        const li = crearElemento('li', 'sel-opcion' + (o.value === '' ? ' sel-placeholder' : ''));
        li.id = id + '-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', o.selected ? 'true' : 'false');
        li.dataset.valor = o.value;
        if (evaluacion && o.value) li.insertAdjacentHTML('beforeend', ICONOS_EVAL[o.value]);
        li.append(crearElemento('span', 'sel-op-texto', o.textContent.trim()));
        if (o.selected && o.value) li.insertAdjacentHTML('beforeend', '<span class="sel-marca">' + MARCA + '</span>');
        lista.append(li);
      });
    }

    function marcar(indice) {
      if (!items.length) return;
      activo = (indice + items.length) % items.length;
      $$('.activa', lista).forEach(e => e.classList.remove('activa'));
      const li = lista.children[activo];
      li.classList.add('activa');
      boton.setAttribute('aria-activedescendant', li.id);
      li.scrollIntoView({ block: 'nearest' });
    }

    function abrir() {
      if (abierto && abierto !== api) abierto.cerrar(false);
      pintar();
      lista.hidden = false;
      lista.classList.remove('arriba');
      const caja = boton.getBoundingClientRect();
      const necesario = Math.min(lista.scrollHeight, 272) + 14;
      const debajo = window.innerHeight - caja.bottom - 76;
      if (debajo < necesario && caja.top - 16 > debajo) lista.classList.add('arriba');
      boton.setAttribute('aria-expanded', 'true');
      abierto = api;
      marcar(Math.max(items.findIndex(o => o.selected), 0));
    }

    function cerrar(foco) {
      lista.hidden = true;
      lista.replaceChildren();
      boton.setAttribute('aria-expanded', 'false');
      boton.removeAttribute('aria-activedescendant');
      if (abierto === api) abierto = null;
      if (foco) boton.focus();
    }

    function elegir(indice) {
      const opcion = items[indice];
      if (!opcion) return;
      select.value = opcion.value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      sincronizar();
      cerrar(true);
    }

    const api = { envoltura, cerrar };
    boton.addEventListener('click', () => (lista.hidden ? abrir() : cerrar(true)));
    boton.addEventListener('keydown', evento => {
      const tecla = evento.key;
      if (lista.hidden) {
        if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(tecla)) { evento.preventDefault(); abrir(); }
        return;
      }
      if (tecla === 'ArrowDown') { evento.preventDefault(); marcar(activo + 1); }
      else if (tecla === 'ArrowUp') { evento.preventDefault(); marcar(activo - 1); }
      else if (tecla === 'Home') { evento.preventDefault(); marcar(0); }
      else if (tecla === 'End') { evento.preventDefault(); marcar(items.length - 1); }
      else if (tecla === 'Enter' || tecla === ' ') { evento.preventDefault(); elegir(activo); }
      else if (tecla === 'Escape') { evento.preventDefault(); cerrar(true); }
      else if (tecla === 'Tab') cerrar(false);
      else if (tecla.length === 1 && !evento.ctrlKey && !evento.metaKey) {
        busqueda += tecla.toLowerCase();
        clearTimeout(temporizador);
        temporizador = setTimeout(() => { busqueda = ''; }, 600);
        const encontrado = items.findIndex(o => o.textContent.trim().toLowerCase().startsWith(busqueda));
        if (encontrado >= 0) marcar(encontrado);
      }
    });
    lista.addEventListener('mousedown', evento => evento.preventDefault());
    lista.addEventListener('click', evento => {
      evento.preventDefault();
      evento.stopPropagation();
      const li = evento.target.closest('li');
      if (li) elegir(Array.from(lista.children).indexOf(li));
    });
    lista.addEventListener('mousemove', evento => {
      const li = evento.target.closest('li');
      if (li) marcar(Array.from(lista.children).indexOf(li));
    });
    select.addEventListener('change', sincronizar);
    sincronizar();
  }

  function crearElemento(etiqueta, clase, texto) {
    const e = document.createElement(etiqueta);
    if (clase) e.className = clase;
    if (texto) e.textContent = texto;
    return e;
  }

  document.addEventListener('click', evento => {
    if (abierto && !abierto.envoltura.contains(evento.target)) abierto.cerrar(false);
  });
  $$('select').forEach(mejorarSelect);
})();
