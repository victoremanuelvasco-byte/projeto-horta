from django.urls import path

from . import views

app_name = "pedidos"
urlpatterns = [
    path("finalizar/", views.checkout, name="checkout"),
    path("<uuid:chave>/", views.confirmacao, name="confirmacao"),
]
