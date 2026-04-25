from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import  timedelta
from decimal import Decimal
import json

from gestao.models import Caixa, Reserva
from gestao.services import processar_pagamentos_loja

def pagamentos(request):
    # ==========================================
    # 1. PROCESSAR PAGAMENTO (POST)
    # ==========================================
    if request.method == "POST":
        processar_pagamentos_loja(request.POST)
        return redirect('pagamentos')

    # ==========================================
    # 2. CARREGAR TELA (GET)
    # ==========================================
    filtro_data = request.GET.get('data')
    context = _preparar_contexto_pagamentos(filtro_data)
    
    return render(request, 'pagamentos.html', context)


# --- FUNÇÃO AJUDANTE (Isolada da View Principal) ---
def _preparar_contexto_pagamentos(filtro_data):
    """ Regra de negócio para buscar e formatar os dados da tela de pagamentos """
    
    if filtro_data is None:
        agora = timezone.localtime(timezone.now()) 
        if agora.hour < 10:
            filtro_data = agora.strftime('%Y-%m-%d')
        else:
            amanha = agora + timedelta(days=1)
            filtro_data = amanha.strftime('%Y-%m-%d')
    elif filtro_data == "":
        filtro_data = None

    reservas_query = Reserva.objects.prefetch_related(
        'passageiros__cliente', 'passageiros__pagamentos'
    ).all().order_by('data')

    if filtro_data:
        reservas_query = reservas_query.filter(data=filtro_data)

    dados_reservas = []
    
    for r in reservas_query:
        passageiros = r.passageiros.all()
        if not passageiros: continue
        
        primeiro_nome = passageiros[0].cliente.nome.split()[0]
        qtd_extras = len(passageiros) - 1
        nome_exibicao = f"{primeiro_nome} + {qtd_extras}" if qtd_extras > 0 else primeiro_nome
        
        total_reserva = Decimal('0.00')
        pago_vendedor = Decimal('0.00')
        pago_acqua = Decimal('0.00')
        
        passageiros_json = []
        historico_pagamentos = [] # <--- LISTA NOVA AQUI
        
        for p in passageiros:
            total_reserva += p.valor_cobrado
            pagamentos_cliente = p.pagamentos.all()
            
            for pg in pagamentos_cliente:
                if pg.recebedor == 'VENDEDOR':
                    pago_vendedor += pg.valor
                else:
                    pago_acqua += pg.valor
                    
                # Guardamos o histórico para mostrar na tela
                historico_pagamentos.append({
                    'id': pg.id,
                    'valor': float(pg.valor),
                    'forma': pg.forma_pg,
                    'recebedor': pg.recebedor,
                    'descricao': pg.descricao,
                    'passageiro': p.cliente.nome
                })
            
            ja_pago_total = sum(pg.valor for pg in pagamentos_cliente)
            passageiros_json.append({
                'id_cr': p.id,
                'nome': p.cliente.nome,
                'atividade': p.atividade.apelido,
                'valor_cobrado': float(p.valor_cobrado),
                'pago': float(ja_pago_total),
                'saldo': float(p.valor_cobrado - ja_pago_total)
            })
            
        valor_a_receber = total_reserva - (pago_vendedor + pago_acqua)
        status = "PAGO" if valor_a_receber <= 0 else "PENDENTE"
        
        dados_reservas.append({
            'id': r.id,
            'nome_exibicao': nome_exibicao,
            'vendedor': r.vendedor.nome,
            'pago_vendedor': pago_vendedor,
            'pago_acqua': pago_acqua,
            'total_reserva': total_reserva,
            'valor_a_receber': valor_a_receber,
            'status': status,
            'historico_json': json.dumps(historico_pagamentos), # <--- MANDANDO PRO HTML
            'passageiros_json': json.dumps(passageiros_json)
        })

    return {
        'reservas': dados_reservas,
        'filtro_data': filtro_data
    }




def caixa(request):
    # ==========================================
    # 1. LANÇAMENTO MANUAL (POST)
    # ==========================================
    if request.method == 'POST':
        Caixa.objects.create(
            data=request.POST.get('data') or timezone.localtime(timezone.now()).date(),
            tipo=request.POST.get('tipo'), # 'ENTRADA' ou 'SAIDA'
            descricao=request.POST.get('descricao').upper(),
            forma_pg=request.POST.get('forma_pg'),
            valor=Decimal(request.POST.get('valor').replace(',', '.'))
        )
        return redirect('caixa')

    # ==========================================
    # 2. CARREGAR O FLUXO DO DIA (GET)
    # ==========================================
    data_filtro = request.GET.get('data')
    if not data_filtro:
        data_filtro = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')

    # Busca todos os registros do dia na tabela Caixa
    registros = Caixa.objects.filter(data=data_filtro).order_by('id')

    entradas = []
    saidas = []
    total_entradas = Decimal('0.00')
    total_saidas = Decimal('0.00')

    for r in registros:
        if r.tipo == 'ENTRADA':
            entradas.append(r)
            total_entradas += r.valor
        elif r.tipo == 'SAIDA':
            saidas.append(r)
            total_saidas += r.valor

    saldo_dia = total_entradas - total_saidas

    context = {
        'data_filtro': data_filtro,
        'entradas': entradas,
        'saidas': saidas,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_dia': saldo_dia
    }
    return render(request, 'caixa.html', context)


def print_caixa(request):
    data = request.GET.get('data')
    registros = Caixa.objects.filter(data=data)
    
    entradas = registros.filter(tipo='ENTRADA')
    saidas = registros.filter(tipo='SAIDA')
    
    context = {
        'entradas': entradas,
        'saidas': saidas,
        'total_entradas': sum(e.valor for e in entradas),
        'total_saidas': sum(s.valor for s in saidas),
        'saldo_dia': sum(e.valor for e in entradas) - sum(s.valor for s in saidas)
    }
    return render(request, 'print_caixa.html', context)