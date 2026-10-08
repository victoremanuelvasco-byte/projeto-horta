from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.catalogo, name="inicio"),
    path("cesta/", views.cesta, name="cesta"),
    path("cesta/adicionar/<int:opcao_id>/", views.adicionar, name="adicionar"),
    path("cesta/adicionar-produto/<int:produto_id>/", views.adicionar_produto, name="adicionar_produto"),
    path("cesta/atualizar/<int:opcao_id>/", views.atualizar, name="atualizar"),
    path("cesta/remover/<int:opcao_id>/", views.remover, name="remover"),
]
