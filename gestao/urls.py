from django.urls import path
from gestao.views.operacoes import homepage, sales, print_planilha
from gestao.views.financeiro import pagamentos, caixa, print_caixa
from gestao.views.comissoes import comissoes, print_comissoes

urlpatterns = [
    # Rota principal
    path('', homepage, name='homepage'),
    
    
    path('sales/', sales, name='sales'),

    path('imprimir-planilha/', print_planilha, name='print_planilha'),

    path('pagamentos/', pagamentos, name='pagamentos'),
    path('comissoes/', comissoes, name='comissoes'),
    path('imprimir-comissoes/', print_comissoes, name='print_comissoes'),
    path('caixa/', caixa, name='caixa'),
    path('print-caixa/', print_caixa, name='print_caixa'),
    
]