document.addEventListener("DOMContentLoaded", function() {
    const input = document.getElementById("busqueda");
    const cards = document.querySelectorAll(".card");

    input.addEventListener("input", function() {
      const filtro = input.value.toLowerCase();
      cards.forEach(card => {
        const texto = card.getAttribute("data-nombre").toLowerCase();
        const visible = texto.includes(filtro);
        card.parentElement.style.display = visible ? "block" : "none";
      });
    });
  });