from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
import json
from gestao.services import deletar_cliente_da_reserva, processar_salvamento_reserva

from gestao.models import Vendedor, Atividade, Reserva, ClienteReserva

def homepage(request):
    # ==========================================
    # 1. PROCESSAR AÇÃO (POST)
    # ==========================================
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'excluir':
            # Sua lógica de exclusão atual...
            deletar_cliente_da_reserva(request.POST.get('delete_id'))
            
        elif acao in ['checkin_loja', 'checkin_pier']:
            # Lógica Nova do Check-in
            ids_selecionados = request.POST.getlist('cr_ids')
            novo_status = 'LOJA' if acao == 'checkin_loja' else 'PIER'
            
            if ids_selecionados:
                ClienteReserva.objects.filter(id__in=ids_selecionados).update(status_checkin=novo_status)
                
        return redirect(request.get_full_path())

    # ==========================================
    # 2. CARREGAR TELA (GET)
    # ==========================================
    context, template = _preparar_contexto_homepage(request)
    return render(request, template, context)


# --- FUNÇÕES AJUDANTES (Isoladas da View Principal) ---
def _preparar_contexto_homepage(request):
    """
    Constrói a QuerySet de operações, aplica os filtros de busca,
    gera os resumos do dia e decide se o layout é Mobile ou Desktop.
    """
    filtro_data = request.GET.get('data')
    filtro_vendedor = request.GET.get('vendedor')
    filtro_atividade = request.GET.get('atividade')

    # Regra da Data Padrão (Antes das 10h = Hoje, Depois = Amanhã)
    if not filtro_data:
        agora = timezone.localtime(timezone.now()) 
        if agora.hour < 10:
            filtro_data = agora.strftime('%Y-%m-%d')
        else:
            amanha = agora + timedelta(days=1)
            filtro_data = amanha.strftime('%Y-%m-%d')

    operacoes = ClienteReserva.objects.select_related(
        'cliente', 'reserva', 'reserva__vendedor', 'atividade'
    ).all().order_by('cliente__nome')

    if filtro_data:
        operacoes = operacoes.filter(reserva__data=filtro_data)
    if filtro_vendedor:
        operacoes = operacoes.filter(reserva__vendedor__id=filtro_vendedor)
    if filtro_atividade:
        operacoes = operacoes.filter(atividade__id=filtro_atividade)

    data_obj = None
    if filtro_data:
        try:
            data_obj = datetime.strptime(filtro_data, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    # Agregação: Contagem de atividades
    contagem_atividades = {}
    for op in operacoes:
        apelido = op.atividade.apelido
        contagem_atividades[apelido] = contagem_atividades.get(apelido, 0) + 1

    # Detecta Dispositivo
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(device in user_agent for device in ['iphone', 'android', 'mobile'])

    context = {
        'operacoes': operacoes,
        'resumo_atividades': contagem_atividades,
        'vendedores': Vendedor.objects.all().order_by('nome'),
        'atividades': Atividade.objects.all().order_by('nome'),
        'filtros_atuais': {
            'data': filtro_data, 
            'data_obj': data_obj, 
            'vendedor': filtro_vendedor,
            'atividade': filtro_atividade,
        }
    }
    
    template = 'homepage_mobile.html' if is_mobile else 'homepage.html'
    
    return context, template



def sales(request):
    # ==========================================
    # 1. PROCESSAMENTO DA VENDA (POST)
    # ==========================================
    if request.method == "POST":
        processar_salvamento_reserva(request.POST)
        return redirect('homepage')

    # ==========================================
    # 2. CARREGAMENTO DA TELA DE VENDAS (GET)
    # ==========================================
    edit_id = request.GET.get('edit')
    dados_edicao_json = "null"
    
    # Lógica para preencher a tela quando o usuário clica em "Editar Reserva"
    if edit_id:
        try:
            res = Reserva.objects.get(id=edit_id)
            clientes_data = []
            for cr in res.passageiros.all():
                sinal_pg = cr.pagamentos.filter(descricao="Sinal/Adiantamento").first()
                clientes_data.append({
                    'cr_id': cr.id,
                    'nome': cr.cliente.nome,
                    'telefone': cr.cliente.telefone or "",
                    'documento': cr.cliente.documento if "TEMP_" not in cr.cliente.documento else "",
                    'peso': float(cr.cliente.peso) if cr.cliente.peso else "",
                    'altura': float(cr.cliente.altura) if cr.cliente.altura else "",
                    'atividade': cr.atividade.id if cr.atividade else "",
                    'valor': float(cr.valor_cobrado),
                    'status_checkin': cr.status_checkin or 'LOJA',
                    'tem_sinal': "sim" if sinal_pg else "nao",
                    'valor_sinal': float(sinal_pg.valor) if sinal_pg else "",
                    'forma_pg_sinal': sinal_pg.forma_pg if sinal_pg else "PIX",
                    'recebedor_sinal': sinal_pg.recebedor if sinal_pg else "LOJA",
                })
            
            dados_edicao_json = json.dumps({
                'reserva_id': res.id,
                'data': str(res.data),
                'vendedor': res.vendedor.id if res.vendedor else "",
                'clientes': clientes_data
            })
        except Reserva.DoesNotExist:
            pass

    # Prepara as atividades para o JavaScript atualizar os preços na tela
    atividades_list = [
        {'id': a.id, 'apelido': a.apelido, 'valor_padrao': float(a.valor_padrao)} 
        for a in Atividade.objects.all()
    ]

    # Detecção se é Celular ou PC para carregar o HTML correto
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(x in ua for x in ['iphone', 'android', 'mobile'])

    context = {
        'vendedores': Vendedor.objects.all().order_by('nome'),
        'atividades': Atividade.objects.all(),
        'atividades_json': json.dumps(atividades_list),
        'dados_edicao_json': dados_edicao_json 
    }
    
    template = 'sales_mobile.html' if is_mobile else 'sales.html'
    return render(request, template, context)



def print_planilha(request):
    operacoes = ClienteReserva.objects.select_related('cliente', 'reserva', 'reserva__vendedor', 'atividade', 'dm_responsavel').all().order_by('cliente__nome')

    filtro_data = request.GET.get('data')
    filtro_vendedor = request.GET.get('vendedor')
    filtro_atividade = request.GET.get('atividade')

    # A mesma inteligência de data garante que o PDF nunca saia vazio
    if filtro_data is None:
        agora = timezone.localtime(timezone.now()) 
        if agora.hour < 10:
            filtro_data = agora.strftime('%Y-%m-%d')
        else:
            amanha = agora + timedelta(days=1)
            filtro_data = amanha.strftime('%Y-%m-%d')
    elif filtro_data == "":
        filtro_data = None

    if filtro_data:
        operacoes = operacoes.filter(reserva__data=filtro_data)
    if filtro_vendedor:
        operacoes = operacoes.filter(reserva__vendedor__id=filtro_vendedor)
    if filtro_atividade:
        operacoes = operacoes.filter(atividade__id=filtro_atividade)

    data_obj = None
    if filtro_data:
        try:
            data_obj = datetime.strptime(filtro_data, '%Y-%m-%d').date()
        except ValueError:
            pass

    # A MÁGICA ACONTECE AQUI: Completa a lista até dar 40 linhas cravadas
    operacoes_list = list(operacoes)
    vagas_restantes = 40 - len(operacoes_list)
    if vagas_restantes > 0:
        operacoes_list.extend([None] * vagas_restantes) # Adiciona espaços em branco

    context = {
        'operacoes_list': operacoes_list, # Lista com 40 itens exatos (preenchidos ou None)
        'data_obj': data_obj,
    }
    return render(request, 'print_planilha.html', context)


def ping_render(request):
    """ View super leve só para manter o Render acordado """
    return HttpResponse("Estou acordado!")