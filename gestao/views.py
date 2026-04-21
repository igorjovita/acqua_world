from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Caixa, Cliente, Vendedor, Funcionario, Atividade, Reserva, ClienteReserva, Pagamento
from decimal import Decimal           # <--- ADICIONE ESTA LINHA
from datetime import datetime, timedelta
from django.utils import timezone
import json

from django.shortcuts import redirect
import json # Precisaremos disso para a edição depois

def homepage(request):
    # ==========================================
    # 1. ESCUTA O BOTÃO DE EXCLUIR (POST)
    # ==========================================
    if request.method == 'POST':
        delete_id = request.POST.get('delete_id')
        if delete_id:
            try:
                # Busca o cliente específico
                cr = ClienteReserva.objects.get(id=delete_id)
                reserva = cr.reserva
                cr.delete() # Apaga o cliente
                
                # Se esse era o único cliente da reserva, apaga a reserva inteira para não deixar lixo no banco
                if reserva.passageiros.count() == 0:
                    reserva.delete()
            except ClienteReserva.DoesNotExist:
                pass
                
        # Atualiza a página mantendo você na mesma data que estava olhando
        return redirect(request.get_full_path())

    # ==========================================
    # 2. CARREGA A TABELA E FILTROS (GET)
    # ==========================================
    operacoes = ClienteReserva.objects.select_related('cliente', 'reserva', 'reserva__vendedor', 'atividade').all().order_by('cliente__nome')

    filtro_data = request.GET.get('data')
    filtro_vendedor = request.GET.get('vendedor')
    filtro_atividade = request.GET.get('atividade')

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
    contagem_atividades = {}
    for op in operacoes:
        apelido = op.atividade.apelido
        contagem_atividades[apelido] = contagem_atividades.get(apelido, 0) + 1

    # Detecta se é Mobile (Simples e eficiente)
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

    if is_mobile:
        return render(request, 'homepage_mobile.html', context)
    
    return render(request, 'homepage.html', context)

def sales(request):
    if request.method == "POST":

        # ==========================================
        # 1. INTERCEPTA OS MODAIS DE CADASTRO RÁPIDO
        # ==========================================
        tipo_formulario = request.POST.get('form')
        
        if tipo_formulario == 'form-atividade':
            Atividade.objects.create(
                nome=request.POST.get('nome_atividade'),
                apelido=request.POST.get('apelido_atividade'),
                valor_padrao=Decimal(request.POST.get('valor_atividade').replace(',', '.'))
            )
            return redirect('sales') # Recarrega a tela com a atividade nova na lista
            
        elif tipo_formulario == 'form-vendedor':
            Vendedor.objects.create(
                nome=request.POST.get('nome_vendedor'),
                neto_bat=Decimal(request.POST.get('neto_bat', '0').replace(',', '.')),
                neto_acp=Decimal(request.POST.get('neto_acp', '0').replace(',', '.')),
                neto_tur=Decimal(request.POST.get('neto_tur', '0').replace(',', '.'))
            )
            return redirect('sales')
        
        reserva_id_edicao = request.POST.get('reserva_id_edicao')
        
        # 1. CRIA OU ATUALIZA A RESERVA "MÃE"
        if reserva_id_edicao:
            reserva = Reserva.objects.get(id=reserva_id_edicao)
            reserva.data = request.POST.get('data')
            vendedor_id = request.POST.get('vendedor')
            reserva.vendedor = Vendedor.objects.get(id=vendedor_id) if vendedor_id else None
            reserva.save()
        else:
            vendedor_id = request.POST.get('vendedor')
            vendedor = Vendedor.objects.get(id=vendedor_id) if vendedor_id else None
            reserva = Reserva.objects.create(
                data=request.POST.get('data'),
                vendedor=vendedor,
            )

        # 2. LISTAS CAPTURADAS DO HTML
        cr_ids = request.POST.getlist("cr_id") # IDs de quem já existia
        nomes = request.POST.getlist("nome")
        telefones = request.POST.getlist("telefone")
        documentos = request.POST.getlist("documento")
        pesos = request.POST.getlist("peso")
        alturas = request.POST.getlist("altura")
        atividades = request.POST.getlist("atividade")
        valores = request.POST.getlist("valor")
        
        tem_sinais = request.POST.getlist("tem_sinal")
        valores_sinal = request.POST.getlist("valor_sinal")
        formas_pg_sinal = request.POST.getlist("forma_pg_sinal")
        recebedores_sinal = request.POST.getlist("recebedor_sinal")

        # Se for edição, guarda os IDs que vieram no formulário
        ids_recebidos = [int(id) for id in cr_ids if id.strip()]
        
        # Se for edição, apaga os mergulhadores que foram "removidos" na tela
        if reserva_id_edicao:
            reserva.passageiros.exclude(id__in=ids_recebidos).delete()

        # 3. SALVA OS MERGULHADORES UM POR UM
        for i in range(len(nomes)):
            # Geramos um identificador único para novos clientes sem documento
            # Usamos o timestamp ou o ID da iteração para evitar colisão
            doc_final = documentos[i].strip() if (i < len(documentos) and documentos[i]) else f"TEMP_{reserva.id}_{i}"
            
            # 1. Buscamos ou criamos o Cliente baseado no documento
            cliente, criado = Cliente.objects.get_or_create(
                documento=doc_final,
                defaults={
                    'nome': nomes[i],
                    'telefone': telefones[i] if i < len(telefones) else "",
                    'peso': pesos[i] if (i < len(pesos) and pesos[i]) else None,
                    'altura': alturas[i] if (i < len(alturas) and alturas[i]) else None
                }
            )

            # 2. SE NÃO FOI CRIADO AGORA, ATUALIZAMOS (Crucial para correções de nomes e TEMP)
            if not criado:
                cliente.nome = nomes[i]
                if i < len(telefones) and telefones[i]: cliente.telefone = telefones[i]
                if i < len(pesos) and pesos[i]: cliente.peso = pesos[i]
                if i < len(alturas) and alturas[i]: cliente.altura = alturas[i]
                cliente.save()

            atividade = Atividade.objects.get(id=atividades[i]) if (i < len(atividades) and atividades[i]) else None
            valor_cobrado = Decimal(valores[i]) if (i < len(valores) and valores[i]) else Decimal('0.00')

            # 3. VINCULAMOS O CLIENTE À RESERVA (ClienteReserva)
            # Pegamos o ID do ClienteReserva (se existir) para saber se estamos editando uma linha ou criando nova
            cr_id_atual = cr_ids[i] if i < len(cr_ids) else ""
            
            if cr_id_atual.strip():
                # Atualização de linha existente
                cr = ClienteReserva.objects.get(id=int(cr_id_atual))
                cr.cliente = cliente
                cr.atividade = atividade
                cr.valor_cobrado = valor_cobrado
                cr.save()
                # Limpa pagamentos de sinal apenas se for necessário recriar
                # (Opcional: você pode manter se não quiser deletar o histórico de sinal na edição)
                cr.pagamentos.filter(descricao="Sinal/Adiantamento").delete()
            else:
                # Criação de nova linha de passageiro
                cr = ClienteReserva.objects.create(
                    reserva=reserva,
                    cliente=cliente,
                    atividade=atividade,
                    valor_cobrado=valor_cobrado
                )

            # Salva o Sinal, se houver
            if i < len(tem_sinais) and tem_sinais[i] == "sim":
                valor_s = Decimal(valores_sinal[i]) if valores_sinal[i] else Decimal('0.00')
                if valor_s > 0:
                    p = Pagamento.objects.create(
                        cliente_reserva=cr,
                        valor=valor_s,
                        forma_pg=formas_pg_sinal[i],
                        recebedor=recebedores_sinal[i],
                        descricao="Sinal/Adiantamento"
                    )
                    if recebedores_sinal[i] == 'LOJA':
                        Caixa.objects.create(
                            data=timezone.localtime(timezone.now()).date(),
                            tipo='ENTRADA',
                            descricao=f"SINAL: {nomes[i]}".upper(),
                            forma_pg=formas_pg_sinal[i],
                            valor=valor_s,
                            pagamento_origem=p # Link direto para auditoria
                        )

        return redirect('homepage')

    # ==========================================
    # CARREGAR FORMULÁRIO E DADOS DE EDIÇÃO (GET)
    # ==========================================
    dados_edicao_json = "null"
    edit_id = request.GET.get('edit')
    
    if edit_id:
        try:
            reserva = Reserva.objects.get(id=edit_id)
            passageiros = reserva.passageiros.all()
            
            clientes_data = []
            for cr in passageiros:
                pgs = cr.pagamentos.all()
                tem_sinal = "sim" if pgs.exists() else "nao"
                valor_sinal = sum(p.valor for p in pgs) if pgs else ""
                forma_pg = pgs[0].forma_pg if pgs else ""
                recebedor = pgs[0].recebedor if pgs else ""

                clientes_data.append({
                    'cr_id': cr.id,
                    'nome': cr.cliente.nome,
                    'telefone': cr.cliente.telefone or "",
                    'documento': cr.cliente.documento or "",
                    'peso': float(cr.cliente.peso) if cr.cliente.peso else "",
                    'altura': float(cr.cliente.altura) if cr.cliente.altura else "",
                    'atividade': cr.atividade.id if cr.atividade else "",
                    'valor': float(cr.valor_cobrado),
                    'tem_sinal': tem_sinal,
                    'valor_sinal': float(valor_sinal) if valor_sinal else "",
                    'forma_pg_sinal': forma_pg,
                    'recebedor_sinal': recebedor
                })
            
            dados_edicao = {
                'reserva_id': reserva.id,
                'data': str(reserva.data),
                'vendedor': reserva.vendedor.id if reserva.vendedor else "",
                'quantidade': passageiros.count(),
                'clientes': clientes_data
            }
            dados_edicao_json = json.dumps(dados_edicao)
        except Reserva.DoesNotExist:
            pass

    # AQUI ESTÁ A CORREÇÃO DO ERRO DO JS: Preparar as atividades em JSON seguro
    atividades_list = list(Atividade.objects.all())
    atividades_json_data = [
        {'id': a.id, 'apelido': a.apelido, 'valor_padrao': float(a.valor_padrao)} 
        for a in atividades_list
    ]
    # Detecção de Mobile
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(device in user_agent for device in ['iphone', 'android', 'mobile'])

    context = {
        'vendedores': Vendedor.objects.all().order_by('nome'),
        'atividades': atividades_list, # Para os formulários rápidos no topo da página
        'atividades_json': json.dumps(atividades_json_data), # Para o JavaScript usar
        'dados_edicao_json': dados_edicao_json 
    }
    if is_mobile:
        return render(request, 'sales_mobile.html', context)
    return render(request, 'sales.html', context)

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



def pagamentos(request):
    # ==========================================
    # PROCESSAR PAGAMENTO (POST)
    # ==========================================
    if request.method == "POST":
        reserva_id = request.POST.get("reserva_id")
        tipo_pg = request.POST.get("tipo_acerto") # 'grupo' ou 'individual'
        
        reserva = Reserva.objects.get(id=reserva_id)
        
        if tipo_pg == 'grupo':
            # Pagamento do saldo total restante
            valor_pago = Decimal(request.POST.get("valor_grupo"))
            forma_pg = request.POST.get("forma_pg_grupo")
            
            # Atrelamos o pagamento ao primeiro passageiro da reserva
            primeiro_cliente = reserva.passageiros.first()
            p = Pagamento.objects.create(
                cliente_reserva=primeiro_cliente,
                valor=valor_pago,
                forma_pg=forma_pg,
                recebedor='LOJA',
                descricao="Acerto Final (Grupo)"
            )

            Caixa.objects.create(
                data=timezone.localtime(timezone.now()).date(),
                tipo='ENTRADA',
                descricao=f"ACERTO GRUPO: {primeiro_cliente.cliente.nome}".upper(),
                forma_pg=forma_pg,
                valor=valor_pago,
                pagamento_origem=p
            )
            
        elif tipo_pg == 'individual':
            # Pagamento separado por pessoa
            ids_cr = request.POST.getlist("id_cr")
            valores = request.POST.getlist("valor_ind")
            formas = request.POST.getlist("forma_pg_ind")
            
            for i in range(len(ids_cr)):
                valor = Decimal(valores[i])
                if valor > 0: # Só cria registro se o valor digitado for maior que 0
                    cr = ClienteReserva.objects.get(id=ids_cr[i])
                    p = Pagamento.objects.create(
                        cliente_reserva=cr,
                        valor=valor,
                        forma_pg=formas[i],
                        recebedor='LOJA',
                        descricao="Acerto Final (Individual)"
                    )
                    Caixa.objects.create(
                        data=timezone.localtime(timezone.now()).date(),
                        tipo='ENTRADA',
                        descricao=f"ACERTO FINAL: {cr.cliente.nome}".upper(),
                        forma_pg=formas[i],
                        valor=valor,
                        pagamento_origem=p
                    )
        
        # Opcional: Se o saldo zerou, podemos mudar o status da reserva para FINALIZADA
        # reserva.situacao = 'FINALIZADA'
        # reserva.save()
        
        return redirect('pagamentos')

    # ==========================================
    # CARREGAR TELA (GET)
    # ==========================================
    filtro_data = request.GET.get('data')

    if filtro_data is None:
        agora = timezone.localtime(timezone.now()) 
        if agora.hour < 10:
            filtro_data = agora.strftime('%Y-%m-%d')
        else:
            amanha = agora + timedelta(days=1)
            filtro_data = amanha.strftime('%Y-%m-%d')
    elif filtro_data == "":
        filtro_data = None

    # Busca as Reservas e traz os passageiros e pagamentos de uma vez só (otimização)
    reservas_query = Reserva.objects.prefetch_related(
        'passageiros__cliente', 'passageiros__pagamentos'
    ).all().order_by('data')

    if filtro_data:
        reservas_query = reservas_query.filter(data=filtro_data)

    dados_reservas = []
    
    for r in reservas_query:
        passageiros = r.passageiros.all()
        if not passageiros: continue
        
        # Nome de exibição (Igor + 1)
        primeiro_nome = passageiros[0].cliente.nome.split()[0]
        qtd_extras = len(passageiros) - 1
        nome_exibicao = f"{primeiro_nome} + {qtd_extras}" if qtd_extras > 0 else primeiro_nome
        
        total_reserva = Decimal('0.00')
        pago_vendedor = Decimal('0.00')
        pago_acqua = Decimal('0.00')
        
        passageiros_json = []
        
        for p in passageiros:
            total_reserva += p.valor_cobrado
            
            # Separação dos pagamentos por recebedor
            pagamentos_cliente = p.pagamentos.all()
            for pg in pagamentos_cliente:
                if pg.recebedor == 'VENDEDOR':
                    pago_vendedor += pg.valor
                else:
                    pago_acqua += pg.valor
            
            # Saldo individual para o modal
            ja_pago_total = sum(pg.valor for pg in pagamentos_cliente)
            passageiros_json.append({
                'id_cr': p.id,
                'nome': p.cliente.nome,
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
            'passageiros_json': json.dumps(passageiros_json)
        })

    context = {
        'reservas': dados_reservas,
        'filtro_data': filtro_data
    }
    return render(request, 'pagamentos.html', context)


def comissoes(request):
    # ==========================================
    # PROCESSAR O ACERTO (POST) - Continua igual
    # ==========================================
    if request.method == 'POST':
        cr_ids_str = request.POST.get('cr_ids')
        data_acerto = request.POST.get('data_acerto')
        forma_pg_acerto = request.POST.get('forma_pg_acerto')
        
        if cr_ids_str:
            lista_ids = cr_ids_str.split(',')
            objetos = ClienteReserva.objects.filter(id__in=lista_ids)
            
            # Automação de Caixa (se saldo != 0)
            saldo_total = sum((o.neto_atividade - o.recebido_loja) for o in objetos)
            if saldo_total != 0:
                v_nome = objetos.first().reserva.vendedor.nome
                Caixa.objects.create(
                    data=data_acerto,
                    tipo='ENTRADA' if saldo_total > 0 else 'SAIDA',
                    descricao=f"ACERTO COMISSÃO: {v_nome}".upper(),
                    forma_pg=forma_pg_acerto,
                    valor=abs(saldo_total)
                )

            objetos.update(acerto_liquidado=True, data_acerto=data_acerto, forma_pg_acerto=forma_pg_acerto)
        return redirect('comissoes')

    # ==========================================
    # CARREGAR A TELA (GET)
    # ==========================================
    data_inicio = request.GET.get('inicio')
    data_fim = request.GET.get('fim')
    vendedor_id = request.GET.get('vendedor')

    hoje = timezone.localtime(timezone.now()).date()
    if not data_inicio: data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
    if not data_fim: data_fim = hoje.strftime('%Y-%m-%d')

    # Filtro de reservas que já aconteceram e não foram liquidadas
    reservas_qs = Reserva.objects.filter(
        data__range=[data_inicio, data_fim],
        data__lte=hoje,
        passageiros__acerto_liquidado=False
    ).distinct().select_related('vendedor').prefetch_related('passageiros__cliente', 'passageiros__atividade')

    if vendedor_id:
        reservas_qs = reservas_qs.filter(vendedor__id=vendedor_id)

    lista_comissoes = []

    for r in reservas_qs:
        crs = r.passageiros.filter(acerto_liquidado=False)
        if not crs: continue

        # Lógica Igor + 1
        primeiro_passageiro = crs.first()
        primeiro_nome = primeiro_passageiro.cliente.nome.split()[0]
        qtd_extras = crs.count() - 1
        nome_exibicao = f"{primeiro_nome} + {qtd_extras}" if qtd_extras > 0 else primeiro_nome

        # Lógica Composição (1 BAT + 1 ACP)
        contagem = {}
        sub_neto = Decimal('0.00')
        sub_acqua = Decimal('0.00')
        sub_vend = Decimal('0.00')
        ids_linha = []

        for cr in crs:
            sigla = cr.atividade.apelido
            contagem[sigla] = contagem.get(sigla, 0) + 1
            sub_neto += cr.neto_atividade
            sub_acqua += cr.recebido_loja
            sub_vend += cr.retido_vendedor
            ids_linha.append(str(cr.id))

        composicao = " + ".join([f"{q} {s}" for s, q in contagem.items()])
        saldo = sub_neto - sub_acqua

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

    context = {
        'comissoes': lista_comissoes,
        'vendedores_list': Vendedor.objects.all().order_by('nome'),
        'filtros': {'inicio': data_inicio, 'fim': data_fim, 'vendedor_id': vendedor_id}
    }
    return render(request, 'comissoes.html', context)


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
            sub_neto += cr.neto_atividade
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