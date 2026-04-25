from django.shortcuts import redirect
from decimal import Decimal
from gestao.models import Atividade, Vendedor

def cadastrar_atividade(request):
    if request.method == 'POST':
        valor_atividade = request.POST.get('valor_atividade', '0').replace(',', '.')
        Atividade.objects.create(
            nome=request.POST.get('nome_atividade'),
            apelido=request.POST.get('apelido_atividade'),
            valor_padrao=Decimal(valor_atividade if valor_atividade.strip() else '0'),
            categoria_comissao=request.POST.get('categoria_comissao', 'BATISMO')
        )
    
    return redirect('sales')

def cadastrar_vendedor(request):
    if request.method == 'POST':

        def limpar_decimal(valor, padrao):
            if not valor or str(valor).strip() == '':
                return Decimal(padrao)
            return Decimal(str(valor).replace(',', '.'))
        
        Vendedor.objects.create(
            nome=request.POST.get('nome_vendedor'),
            neto_bat=limpar_decimal(request.POST.get('neto_bat'), '200.00'),
            neto_acp=limpar_decimal(request.POST.get('neto_acp'), '80.00'),
            neto_turismo_1=limpar_decimal(request.POST.get('neto_turismo_1'), '330.00'),
            neto_turismo_2=limpar_decimal(request.POST.get('neto_turismo_2'), '380.00'),
            neto_scuba=limpar_decimal(request.POST.get('neto_scuba'), '480.00'),
            neto_curso=limpar_decimal(request.POST.get('neto_curso'), '10.00')
        )

    return redirect('sales')