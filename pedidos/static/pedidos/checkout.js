const modalidade = document.getElementById("id_modalidade");
const endereco = document.getElementById("endereco");
const cep = document.getElementById("id_cep");
const cepStatus = document.getElementById("cep-status");
const camposCep = {
  logradouro: document.getElementById("id_logradouro"),
  bairro: document.getElementById("id_bairro"),
  localidade: document.getElementById("id_cidade"),
  uf: document.getElementById("id_uf"),
};
let consultaCep = null;
let esperaCep = null;
const preenchidosCep = new Map();

function cancelarConsultaCep() {
  clearTimeout(esperaCep);
  if (consultaCep) consultaCep.abort();
  consultaCep = null;
}

function atualizarEndereco() {
  const retirada = modalidade.value === "RETIRADA";
  endereco.hidden = retirada;
  endereco.disabled = retirada;
  if (retirada) {
    cancelarConsultaCep();
    if (cepStatus) cepStatus.textContent = "";
  } else if (cep && cepStatus) {
    agendarConsultaCep();
  }
}

async function buscarCep(numero) {
  const controller = new AbortController();
  consultaCep = controller;
  const valoresAntes = Object.fromEntries(
    Object.entries(camposCep).map(([nome, campo]) => [nome, campo.value])
  );
  cepStatus.textContent = "Buscando endereço…";
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const resposta = await fetch(`https://viacep.com.br/ws/${numero}/json/`, {
      signal: controller.signal,
    });
    if (!resposta.ok) throw new Error("Falha na consulta");
    const dados = await resposta.json();
    // Uma consulta antiga não pode substituir o endereço de um novo CEP.
    if (consultaCep !== controller || endereco.disabled || cep.value.replace(/\D/g, "") !== numero) return;
    if (dados.erro) {
      cepStatus.textContent = "CEP não encontrado. Confira o CEP ou preencha o endereço manualmente.";
      return;
    }
    let completo = true;
    for (const [nome, campo] of Object.entries(camposCep)) {
      const valor = typeof dados[nome] === "string" ? dados[nome] : "";
      if (!valor) completo = false;
      // Preserva alterações feitas pelo cliente enquanto a consulta estava em andamento.
      if (valor && campo.value === valoresAntes[nome]) {
        campo.value = valor;
        preenchidosCep.set(campo, campo.value);
      }
    }
    cepStatus.textContent = completo
      ? "Endereço preenchido. Confira os dados e informe o número e, se necessário, o complemento."
      : "CEP localizado. Confira os dados e preencha os campos que faltam, incluindo o número.";
  } catch (erro) {
    if (consultaCep === controller) {
      cepStatus.textContent = "Não foi possível consultar o CEP. Preencha o endereço manualmente ou tente novamente.";
    }
  } finally {
    clearTimeout(timeout);
    if (consultaCep === controller) consultaCep = null;
  }
}

function agendarConsultaCep() {
  cancelarConsultaCep();
  cepStatus.textContent = "";
  if (endereco.disabled) return;
  const numero = cep.value.replace(/\D/g, "");
  if (/^[0-9]{5}-?[0-9]{3}$/.test(cep.value.trim())) {
    esperaCep = setTimeout(() => buscarCep(numero), 350);
  } else if (cep.value.trim()) {
    cepStatus.textContent = "Digite um CEP com oito dígitos.";
  }
}

if (cep && cepStatus && Object.values(camposCep).every(Boolean)) {
  cep.addEventListener("input", () => {
    // Remove apenas valores da consulta anterior que o cliente não editou.
    for (const [campo, valor] of preenchidosCep) {
      if (campo.value === valor) campo.value = "";
    }
    preenchidosCep.clear();
    agendarConsultaCep();
  });
  cep.addEventListener("blur", () => {
    if (/^[0-9]{8}$/.test(cep.value)) cep.value = `${cep.value.slice(0, 5)}-${cep.value.slice(5)}`;
  });
}
if (modalidade && endereco) {
  modalidade.addEventListener("change", atualizarEndereco);
  atualizarEndereco();
}
