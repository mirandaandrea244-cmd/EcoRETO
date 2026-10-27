document.addEventListener("DOMContentLoaded", () => {

  // 1) Los mensajes desaparecen solos a los 5 segundos
  document.querySelectorAll(".mensaje").forEach(m => {
    setTimeout(() => m.classList.add("oculto"), 5000);
    setTimeout(() => m.remove(), 5600);
  });

  // 2) Botón 👁 para ver u ocultar la contraseña
  document.querySelectorAll("[data-ver-pass]").forEach(boton => {
    boton.addEventListener("click", () => {
      const campo = document.getElementById(boton.dataset.verPass);
      campo.type = campo.type === "password" ? "text" : "password";
    });
  });

  // 3) Buscador + filtros por tipo en la tabla
  const buscador = document.getElementById("buscador");
  const chips = document.querySelectorAll(".chip");
  const filas = document.querySelectorAll("#tabla-acciones tbody tr");
  let tipoActivo = "todos";

  function filtrar() {
    const texto = buscador ? buscador.value.toLowerCase().trim() : "";
    let visibles = 0;
    filas.forEach(fila => {
      const coincide =
        (tipoActivo === "todos" || fila.dataset.tipo === tipoActivo) &&
        fila.dataset.texto.includes(texto);
      fila.hidden = !coincide;
      if (coincide) visibles++;
    });
    const aviso = document.getElementById("sin-resultados");
    if (aviso) aviso.hidden = visibles > 0;
  }

  if (buscador) buscador.addEventListener("input", filtrar);
  chips.forEach(chip => chip.addEventListener("click", () => {
    chips.forEach(c => c.classList.remove("activo"));
    chip.classList.add("activo");
    tipoActivo = chip.dataset.tipo;
    filtrar();
  }));

  // 4) Ventana para confirmar antes de eliminar
  const modal = document.getElementById("modal");
  const formEliminar = document.getElementById("form-eliminar");
  document.querySelectorAll("[data-eliminar]").forEach(boton => {
    boton.addEventListener("click", () => {
      formEliminar.action = boton.dataset.eliminar;
      document.getElementById("modal-nombre").textContent = "“" + boton.dataset.nombre + "”";
      modal.hidden = false;
    });
  });
  document.querySelectorAll("[data-cerrar]").forEach(b =>
    b.addEventListener("click", () => (modal.hidden = true)));
  const confirmar = document.getElementById("confirmar-eliminar");
  if (confirmar) confirmar.addEventListener("click", () => formEliminar.submit());

  // 5) Formulario: unidad automática, contador y validaciones
  const form = document.getElementById("form-accion");
  if (form) {
    const tipo = form.elements["tipo"];
    const unidad = form.elements["unidad"];
    const descripcion = form.elements["descripcion"];
    const contador = document.getElementById("contador");

    // Al elegir el tipo, sugiere la unidad (solo en "nueva")
    tipo.addEventListener("change", () => {
      const opcion = tipo.options[tipo.selectedIndex];
      if (form.dataset.modo === "nueva" && opcion.dataset.unidad) {
        unidad.value = opcion.dataset.unidad;
      }
    });

    // Contador de caracteres
    const contar = () => (contador.textContent = descripcion.value.length + "/120");
    descripcion.addEventListener("input", contar);
    contar();

    // Reglas: [campo, función que valida, mensaje de error]
    const reglas = [
      ["tipo", v => v !== "", "Elige un tipo de acción."],
      ["descripcion", v => v.trim().length >= 5, "Escribe al menos 5 caracteres."],
      ["fecha", v => v !== "", "Elige una fecha."],
      ["cantidad", v => Number(v) > 0, "El impacto debe ser mayor que 0."],
    ];

    form.addEventListener("submit", evento => {
      let todoBien = true;
      reglas.forEach(([nombre, valida, mensaje]) => {
        const campo = form.elements[nombre];
        const aviso = document.getElementById("error-" + nombre);
        const bien = valida(campo.value);
        campo.classList.toggle("invalido", !bien);
        aviso.textContent = bien ? "" : mensaje;
        if (!bien) todoBien = false;
      });
      if (!todoBien) evento.preventDefault(); // no envía si hay errores
    });
  }
});