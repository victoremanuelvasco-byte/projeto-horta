const modalidade = document.getElementById("id_modalidade");
const endereco = document.getElementById("endereco");
function atualizarEndereco() {
  const retirada = modalidade.value === "RETIRADA";
  endereco.hidden = retirada;
  // Os campos continuam sendo validados no servidor, mesmo sem JavaScript.
  endereco.disabled = retirada;
}
if (modalidade && endereco) {
  modalidade.addEventListener("change", atualizarEndereco);
  atualizarEndereco();
}
