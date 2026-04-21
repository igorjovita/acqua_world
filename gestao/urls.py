from django.urls import path
from . import views

urlpatterns = [
    # Rota principal
    path('', views.homepage, name='homepage'),
    
    
    path('sales/', views.sales, name='sales'),

    path('imprimir-planilha/', views.print_planilha, name='print_planilha'),

    path('pagamentos/', views.pagamentos, name='pagamentos'),
    path('comissoes/', views.comissoes, name='comissoes'),
    path('imprimir-comissoes/', views.print_comissoes, name='print_comissoes'),
    path('caixa/', views.caixa, name='caixa'),
    path('print-caixa/', views.print_caixa, name='print_caixa'),
    # --- ROTAS TEMPORÁRIAS ---
    # Apontando para a homepage apenas para o base.html não quebrar
    path('links/', views.homepage, name='links_gerados'),
    path('upload/', views.homepage, name='upload'),
    path('staff/', views.homepage, name='staff'),
    path('equipamentos/', views.homepage, name='painel_equipamentos'),
    path('financeiro/', views.homepage, name='financeiro_dashboard'),
    path('sair/', views.homepage, name='logout'),
]