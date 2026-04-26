from django.urls import path
from gestao.views.operacoes import homepage, sales, print_planilha, ping_render
from gestao.views.financeiro import pagamentos, caixa, print_caixa
from gestao.views.comissoes import comissoes, print_comissoes
from gestao.views.cadastros import cadastrar_atividade, cadastrar_vendedor

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
    path('ping/', ping_render),

    path('cadastrar-atividade/', cadastrar_atividade, name='cadastrar_atividade'),
    path('cadastrar-vendedor/', cadastrar_vendedor, name='cadastrar_vendedor'),


    # --- ROTAS TEMPORÁRIAS ---
    # Apontando para a homepage apenas para o base.html não quebrar
    path('links/', homepage, name='links_gerados'),
    path('upload/', homepage, name='upload'),
    path('staff/', homepage, name='staff'),
    path('equipamentos/', homepage, name='painel_equipamentos'),
    path('financeiro/', homepage, name='financeiro_dashboard'),
    path('sair/', homepage, name='logout'),
]