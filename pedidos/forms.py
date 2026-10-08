import re
import unicodedata

from django import forms

from .models import ConfiguracaoLoja, Pedido


CAMPOS_ENDERECO = ["cep", "logradouro", "numero_endereco", "complemento", "bairro", "cidade", "uf", "referencia"]
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()


class CheckoutForm(forms.ModelForm):
    telefone_cliente = forms.CharField(label="Telefone / WhatsApp", max_length=22, widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}))
    confirmacao = forms.CharField(widget=forms.HiddenInput)
    revisar = forms.BooleanField(
        label="Revisei os itens, as quantidades e os valores. Entendo que o pedido depende da confirmação do vendedor.",
    )

    class Meta:
        model = Pedido
        fields = ["nome_cliente", "telefone_cliente", "modalidade", "forma_pagamento", *CAMPOS_ENDERECO, "observacoes"]
        widgets = {
            "telefone_cliente": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
            "nome_cliente": forms.TextInput(attrs={"autocomplete": "name"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
            "cep": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "postal-code", "placeholder": "00000-000", "aria-describedby": "cep-status"}),
            "uf": forms.Select(choices=[("", "Selecione")] + [(uf, uf) for uf in UFS]),
        }

    def clean_telefone_cliente(self):
        texto = self.cleaned_data["telefone_cliente"]
        numero = re.sub(r"[^0-9]", "", texto)
        if len(numero) in (10, 11):
            numero = "55" + numero
        if not re.fullmatch(r"55[1-9][0-9]{9,10}", numero):
            raise forms.ValidationError("Informe um telefone com DDD, com 10 ou 11 dígitos.")
        return numero

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loja = ConfiguracaoLoja.objects.filter(pk=1).first()
        if self.loja and not self.is_bound:
            self.initial.update(cidade=self.loja.cidade_entrega, uf=self.loja.uf_entrega)
        self.fields["modalidade"].choices = [("", "Selecione")] + list(Pedido.Modalidade.choices)
        self.fields["forma_pagamento"].choices = [("", "Selecione")] + list(Pedido.Pagamento.choices)

    def clean(self):
        dados = super().clean()
        if dados.get("modalidade") == Pedido.Modalidade.RETIRADA:
            self.instance.taxa_entrega = 0
            for campo in CAMPOS_ENDERECO:
                dados[campo] = ""
        else:
            self.instance.taxa_entrega = None
        if dados.get("modalidade") == "ENTREGA" and self.loja and self.loja.cidade_entrega:
            normalizar = lambda valor: "".join(c for c in unicodedata.normalize("NFKD", valor).casefold() if c.isalnum() and not unicodedata.combining(c))
            if normalizar(dados.get("cidade", "")) != normalizar(self.loja.cidade_entrega):
                self.add_error("cidade", f"Entregamos apenas em {self.loja.cidade_entrega}/{self.loja.uf_entrega}.")
            if dados.get("uf", "") != self.loja.uf_entrega:
                self.add_error("uf", f"Entregamos apenas em {self.loja.cidade_entrega}/{self.loja.uf_entrega}.")
        cep = dados.get("cep", "")
        if cep and not re.fullmatch(r"[0-9]{5}-?[0-9]{3}", cep):
            self.add_error("cep", "Informe um CEP com oito dígitos.")
        return dados

    @property
    def campos_cliente(self):
        return [self[nome] for nome in ["nome_cliente", "telefone_cliente", "modalidade", "forma_pagamento"]]

    @property
    def campos_endereco(self):
        return [self[nome] for nome in CAMPOS_ENDERECO]
