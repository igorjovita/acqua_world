from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from gestao.models import Reserva, Vendedor
from gestao.services import processar_acerto_comissao

def comissoes(request):
    # ==========================================
    # 1. PROCESSAR O ACERTO (POST)
    # ==========================================
    if request.method == 'POST':
        processar_acerto_comissao(request.POST)
        return redirect('comissoes')

    # ==========================================
    # 2. CARREGAR A TELA (GET)
    # ==========================================
    context = _preparar_contexto_comissoes(request.GET)
    return render(request, 'comissoes.html', context)


# --- FUNÇÃO AJUDANTE (Isolada da View Principal) ---
def _preparar_contexto_comissoes(dados_get):
    """
    Filtra as reservas não liquidadas e formata os dados 
    para a tabela de fechamento de comissões, aplicando regras de B2B.
    """
    data_inicio = dados_get.get('inicio')
    data_fim = dados_get.get('fim')
    vendedor_id = dados_get.get('vendedor')

    hoje = timezone.localtime(timezone.now()).date()
    if not data_inicio: 
        data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
    if not data_fim: 
        data_fim = hoje.strftime('%Y-%m-%d')

    reservas_qs = Reserva.objects.filter(
        data__range=[data_inicio, data_fim],
        data__lte=hoje, # Já garante que o mergulho aconteceu (Check-in/Data passada)
        passageiros__acerto_liquidado=False
    ).distinct().select_related('vendedor').prefetch_related('passageiros__cliente', 'passageiros__atividade')

    if vendedor_id:
        reservas_qs = reservas_qs.filter(vendedor__id=vendedor_id)

    lista_comissoes = []

    for r in reservas_qs:
        # =========================================================
        # PORTÃO 1: A reserva foi totalmente paga?
        # =========================================================
        todos_passageiros = r.passageiros.all()
        total_cobrado = sum(cr.valor_cobrado for cr in todos_passageiros)
        total_pago = sum(cr.recebido_loja + cr.retido_vendedor for cr in todos_passageiros)

        # Se o que foi pago for menor que o valor cobrado, o cliente ainda deve.
        # Portanto, não entra no acerto de comissões. Pula para a próxima reserva.
        if total_pago < total_cobrado:
            continue

        # =========================================================
        # PROCESSAMENTO NORMAL DAS COMISSÕES
        # =========================================================
        crs_pendentes = r.passageiros.filter(acerto_liquidado=False)
        if not crs_pendentes: 
            continue

        # Lógica Igor + 1
        primeiro_passageiro = crs_pendentes.first()
        primeiro_nome = primeiro_passageiro.cliente.nome.split()[0]
        qtd_extras = crs_pendentes.count() - 1
        nome_exibicao = f"{primeiro_nome} + {qtd_extras}" if qtd_extras > 0 else primeiro_nome

        # Lógica Composição e Saldos
        contagem = {}
        sub_neto = Decimal('0.00')
        sub_acqua = Decimal('0.00')
        sub_vend = Decimal('0.00')
        ids_linha = []

        for cr in crs_pendentes:
            sigla = cr.atividade.apelido
            contagem[sigla] = contagem.get(sigla, 0) + 1
            sub_neto += cr.neto_praticado
            sub_acqua += cr.recebido_loja
            sub_vend += cr.retido_vendedor
            ids_linha.append(str(cr.id))

        composicao = " + ".join([f"{q} {s}" for s, q in contagem.items()])
        saldo = sub_neto - sub_acqua

        # =========================================================
        # PORTÃO 2: Auto-Liquidação (Saldo Zero)
        # =========================================================
        # Se a reserva está paga E ninguém deve ninguém (a loja pegou exatos 400 e o parceiro exatos 100)
        if saldo == Decimal('0.00'):
            # Marca como liquidado no banco de dados automaticamente
            crs_pendentes.update(
                acerto_liquidado=True, 
                data_acerto=hoje, 
                forma_pg_acerto='AUTO_BAIXA_SALDO_ZERO'
            )
            # Como já foi resolvida, pula e não mostra na tela de comissões pendentes
            continue

        lista_comissoes.append({
            'id_reserva': r.id,
            'data': r.data,
            'vendedor': r.vendedor.nome,
            'vendedor_id': r.vendedor.id,
            'cliente': nome_exibicao,
            'quantidade': composicao,
            'pago_acqua': sub_acqua,
            'pago_vendedor': sub_vend,
            'saldo': saldo,
            'saldo_abs': abs(saldo),
            'ids_cr': ",".join(ids_linha)
        })

    return {
        'comissoes': lista_comissoes,
        'vendedores_list': Vendedor.objects.all().order_by('nome'),
        'filtros': {'inicio': data_inicio, 'fim': data_fim, 'vendedor_id': vendedor_id}
    }

def print_comissoes(request):
    vendedor_id = request.GET.get('vendedor')
    data_inicio = request.GET.get('inicio')
    data_fim = request.GET.get('fim')

    if not vendedor_id:
        return HttpResponse("Erro: Nenhum vendedor selecionado para impressão.")

    vendedor = Vendedor.objects.get(id=vendedor_id)
    
    reservas_query = Reserva.objects.filter(
        vendedor=vendedor,
        data__range=[data_inicio, data_fim],
        passageiros__acerto_liquidado=False
    ).distinct().prefetch_related('passageiros__cliente', 'passageiros__atividade', 'passageiros__pagamentos')

    lista_reservas = []
    totais = {
        'vendedor_deve': Decimal('0.00'), # O que o vendedor tem que pagar
        'acqua_deve': Decimal('0.00'),    # O que a Acqua tem que pagar
        'saldo_geral': Decimal('0.00')
    }

    for r in reservas_query:
        crs = r.passageiros.filter(acerto_liquidado=False)
        if not crs: continue

        primeiro_passageiro = crs.first()
        primeiro_nome = primeiro_passageiro.cliente.nome.split()[0]
        qtd_extras = crs.count() - 1
        nome_exibicao = f"{primeiro_nome} + {qtd_extras}" if qtd_extras > 0 else primeiro_nome

        contagem = {}
        sub_total = Decimal('0.00')
        sub_neto = Decimal('0.00')
        sub_acqua = Decimal('0.00')
        sub_vend = Decimal('0.00')

        for cr in crs:
            sigla = cr.atividade.apelido
            contagem[sigla] = contagem.get(sigla, 0) + 1
            sub_total += cr.valor_cobrado
            sub_neto += cr.neto_praticado
            sub_acqua += cr.recebido_loja
            sub_vend += cr.retido_vendedor

        composicao = " + ".join([f"{q} {s}" for s, q in contagem.items()])
        saldo_linha = sub_neto - sub_acqua
        
        # Lógica direta de quem deve quem naquela reserva
        if saldo_linha > 0:
            totais['vendedor_deve'] += saldo_linha
        elif saldo_linha < 0:
            totais['acqua_deve'] += abs(saldo_linha)

        totais['saldo_geral'] += saldo_linha

        lista_reservas.append({
            'data': r.data,
            'nome_exibicao': nome_exibicao,
            'composicao': composicao,
            'pago_acqua': sub_acqua,
            'pago_vend': sub_vend,
            'saldo_reserva': saldo_linha,
            'saldo_reserva_abs': abs(saldo_linha)
        })

    context = {
        'vendedor': vendedor,
        'inicio': datetime.strptime(data_inicio, '%Y-%m-%d'),
        'fim': datetime.strptime(data_fim, '%Y-%m-%d'),
        'reservas': lista_reservas,
        'totais': {
            **totais,
            'saldo_geral_abs': abs(totais['saldo_geral'])
        }
    }
    return render(request, 'print_comissoes.html', context)



