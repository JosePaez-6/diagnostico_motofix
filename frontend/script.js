document.getElementById("btn-analizar").addEventListener("click", async () => {
  const descripcion = document.getElementById("descripcion").value;
  const motocicleta = document.getElementById("motocicleta").value;
  const resultadoDiv = document.getElementById("resultado");
  const pdfBtn = document.getElementById("btn-pdf");

  if (!motocicleta || !descripcion.trim()) {
    alert("Selecciona una motocicleta y describe la falla.");
    return;
  }

  resultadoDiv.innerHTML = `
    <div class="text-center text-muted">
      <div class="spinner-border text-primary" role="status"></div>
      <p>Analizando con IA, espera un momento...</p>
    </div>
  `;
  pdfBtn.classList.add("d-none");

  try {
    const res = await fetch("http://localhost:8000/api/diagnostico", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ descripcion, motocicleta })
    });

    const data = await res.json();
    resultadoDiv.innerHTML = "";

    // Mostrar predicciones
    data.predicciones.forEach(item => {
      const card = document.createElement("div");
      card.classList.add("card", "p-3", "shadow-sm", "mb-3");

      const explicacionLimpia = item.explicacion.replace(/^.*Análisis.*\n?/i, "");
      card.innerHTML = `
        <h4>${item.pieza} — ${(item.probabilidad * 100).toFixed(1)}%</h4>
        <div>${marked.parse(explicacionLimpia)}</div>
      `;
      resultadoDiv.appendChild(card);
    });

    // Mostrar botón PDF
    pdfBtn.classList.remove("d-none");
    pdfBtn.onclick = () => generarPDF(motocicleta, descripcion, data.predicciones);

    // Crear botón de ticket
    const ticketBtn = document.createElement("button");
    ticketBtn.classList.add("btn", "btn-success", "mt-3");
    ticketBtn.textContent = "🧾 Registrar Ticket";
    resultadoDiv.appendChild(ticketBtn);

    // Al hacer clic → abre formulario modal
    ticketBtn.onclick = () => mostrarFormularioTicket(motocicleta, descripcion, data.predicciones[0]);

  } catch (error) {
    resultadoDiv.innerHTML = "<p class='text-danger'>❌ Error al conectar con la API.</p>";
    console.error(error);
  }
});


// ==========================
// Generar PDF
// ==========================
function generarPDF(motocicleta, descripcion, predicciones) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  doc.setFontSize(16);
  doc.text("Reporte de Diagnóstico MotoFix", 14, 20);
  doc.setFontSize(12);
  doc.text(`Motocicleta: ${motocicleta}`, 14, 30);
  doc.text(`Descripción: ${descripcion}`, 14, 40);

  const tableData = predicciones.map(p => [
    p.pieza,
    (p.probabilidad * 100).toFixed(1) + "%",
    p.explicacion.replace(/\*\*/g, "")
  ]);

  doc.autoTable({
    head: [["Pieza", "Probabilidad", "Explicación"]],
    body: tableData,
    startY: 50,
    styles: { fontSize: 9, cellWidth: 'wrap' },
    columnStyles: { 2: { cellWidth: 100 } }
  });

  doc.save(`diagnostico_${motocicleta}.pdf`);
}


// ==========================
// Registrar Ticket
// ==========================
function mostrarFormularioTicket(motocicleta, descripcion, prediccion) {
  const modalHTML = `
    <div class="modal fade" id="ticketModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Registrar Ticket de Diagnóstico</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <p><strong>Pieza sugerida:</strong> ${prediccion.pieza}</p>
            <p><strong>Probabilidad:</strong> ${(prediccion.probabilidad * 100).toFixed(1)}%</p>

            <div class="mb-3">
              <label for="fallaReal" class="form-label">Falla real</label>
              <input type="text" class="form-control" id="fallaReal" placeholder="Ejemplo: válvula de escape dañada">
            </div>
            <div class="mb-3">
              <label for="cambios" class="form-label">Cambios realizados</label>
              <textarea class="form-control" id="cambios" rows="3" placeholder="Ejemplo: se reemplazó válvula y se ajustó culata."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" id="guardarTicket">Guardar Ticket</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Insertar modal al DOM
  document.body.insertAdjacentHTML("beforeend", modalHTML);
  const modal = new bootstrap.Modal(document.getElementById("ticketModal"));
  modal.show();

  document.getElementById("guardarTicket").onclick = async () => {
    const fallaReal = document.getElementById("fallaReal").value;
    const cambios = document.getElementById("cambios").value;

    if (!fallaReal.trim() || !cambios.trim()) {
      alert("Por favor completa todos los campos.");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          motocicleta,
          descripcion,
          diagnostico: prediccion.explicacion,
          pieza: prediccion.pieza,
          probabilidad: prediccion.probabilidad,
          falla_real: fallaReal,
          cambios_realizados: cambios
        })
      });

      const data = await res.json();
      if (data.status === "ok") {
        alert("✅ Ticket registrado correctamente.");
      } else {
        alert("❌ Error al registrar el ticket: " + data.message);
      }
      modal.hide();
    } catch (err) {
      console.error(err);
      alert("Error al conectar con la API.");
    }
  };
}
