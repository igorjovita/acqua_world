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
        tipo_formulario = request.POST.get('form')
        
        # 1. CADASTRO RÁPIDO DE ATIVIDADE
        if tipo_formulario == 'form-atividade':
            Atividade.objects.create(
                nome=request.POST.get('nome_atividade'),
                apelido=request.POST.get('apelido_atividade'),
                valor_padrao=Decimal(request.POST.get('valor_atividade').replace(',', '.')),
                categoria_comissao=request.POST.get('categoria_comissao') # Novo campo
            )
            return redirect('sales')
            
        # 2. CADASTRO RÁPIDO DE VENDEDOR (Com os novos Netos e Cursos)
        elif tipo_formulario == 'form-vendedor':
            Vendedor.objects.create(
                nome=request.POST.get('nome_vendedor'),
                neto_bat=Decimal(request.POST.get('neto_bat', '200').replace(',', '.')),
                neto_acp=Decimal(request.POST.get('neto_acp', '80').replace(',', '.')),
                neto_turismo_1=Decimal(request.POST.get('neto_turismo_1', '330').replace(',', '.')),
                neto_turismo_2=Decimal(request.POST.get('neto_turismo_2', '380').replace(',', '.')),
                neto_scuba=Decimal(request.POST.get('neto_scuba', '480').replace(',', '.')),
                neto_curso=Decimal(request.POST.get('neto_curso', '10').replace(',', '.'))
            )
            return redirect('sales')
        
        # 3. PROCESSAMENTO DA RESERVA
        reserva_id_edicao = request.POST.get('reserva_id_edicao')
        vendedor_id = request.POST.get('vendedor')
        vendedor = Vendedor.objects.get(id=vendedor_id) if vendedor_id else None
        data_reserva = request.POST.get('data')

        if reserva_id_edicao:
            reserva = Reserva.objects.get(id=reserva_id_edicao)
            reserva.data = data_reserva
            reserva.vendedor = vendedor
            reserva.save()
        else:
            reserva = Reserva.objects.create(data=data_reserva, vendedor=vendedor)

        # Captura listas do formulário
        cr_ids = request.POST.getlist("cr_id")
        nomes = request.POST.getlist("nome")
        telefones = request.POST.getlist("telefone")
        documentos = request.POST.getlist("documento")
        pesos = request.POST.getlist("peso")
        alturas = request.POST.getlist("altura")
        atividades_ids = request.POST.getlist("atividade")
        valores = request.POST.getlist("valor")
        
        tem_sinais = request.POST.getlist("tem_sinal")
        valores_sinal = request.POST.getlist("valor_sinal")
        formas_pg_sinal = request.POST.getlist("forma_pg_sinal")
        recebedores_sinal = request.POST.getlist("recebedor_sinal")

        # Gestão de remoção na edição
        if reserva_id_edicao:
            ids_recebidos = [int(i) for i in cr_ids if i.strip()]
            reserva.passageiros.exclude(id__in=ids_recebidos).delete()

        # 4. LOOP DE SALVAMENTO DOS PASSAGEIROS
        for i in range(len(nomes)):
            if not nomes[i].strip(): continue

            # Documento ou temporário
            doc_final = documentos[i].strip() if (i < len(documentos) and documentos[i].strip()) else f"TEMP_{reserva.id}_{i}"
            
            cliente, _ = Cliente.objects.get_or_create(
                documento=doc_final,
                defaults={'nome': nomes[i]}
            )
            # Atualiza dados do cliente sempre
            cliente.nome = nomes[i]
            if i < len(telefones): cliente.telefone = telefones[i]
            if i < len(pesos) and pesos[i]: cliente.peso = Decimal(pesos[i].replace(',', '.'))
            if i < len(alturas) and alturas[i]: cliente.altura = Decimal(alturas[i].replace(',', '.'))
            cliente.save()

            atividade = Atividade.objects.get(id=atividades_ids[i]) if atividades_ids[i] else None
            valor_c = Decimal(valores[i].replace(',', '.')) if valores[i] else Decimal('0.00')

            cr_id_atual = cr_ids[i] if i < len(cr_ids) else ""
            
            if cr_id_atual.strip():
                cr = ClienteReserva.objects.get(id=int(cr_id_atual))
                cr.cliente = cliente
                cr.atividade = atividade
                cr.valor_cobrado = valor_c
                cr.save() # Aqui o model calcula a comissão sozinho!
            else:
                cr = ClienteReserva.objects.create(
                    reserva=reserva,
                    cliente=cliente,
                    atividade=atividade,
                    valor_cobrado=valor_c
                ) # O create também dispara o save() do model

            # 5. PAGAMENTOS (SINAL)
            # Limpa sinais antigos se for edição para evitar duplicidade ao re-salvar
            cr.pagamentos.filter(descricao="Sinal/Adiantamento").delete()

            if i < len(tem_sinais) and tem_sinais[i] == "sim":
                v_sinal = Decimal(valores_sinal[i].replace(',', '.')) if valores_sinal[i] else Decimal('0.00')
                if v_sinal > 0:
                    p = Pagamento.objects.create(
                        cliente_reserva=cr,
                        valor=v_sinal,
                        forma_pg=formas_pg_sinal[i],
                        recebedor=recebedores_sinal[i],
                        descricao="Sinal/Adiantamento"
                    )
                    # Se caiu na LOJA, vai para o Livro Caixa
                    if recebedores_sinal[i] == 'LOJA':
                        Caixa.objects.create(
                            data=reserva.data,
                            tipo='ENTRADA',
                            descricao=f"SINAL: {cliente.nome} ({atividade.apelido})".upper(),
                            forma_pg=formas_pg_sinal[i],
                            valor=v_sinal,
                            pagamento_origem=p
                        )

        return redirect('homepage')

    # ==========================================
    # LÓGICA DO GET (CARREGAMENTO DA TELA)
    # ==========================================
    edit_id = request.GET.get('edit')
    dados_edicao_json = "null"
    
    if edit_id:
        try:
            res = Reserva.objects.get(id=edit_id)
            clientes_data = []
            for cr in res.passageiros.all():
                # Busca sinal se existir
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

    # Prepara as atividades para o JS (Preenchimento automático de preços)
    atividades_list = [
        {'id': a.id, 'apelido': a.apelido, 'valor_padrao': float(a.valor_padrao)} 
        for a in Atividade.objects.all()
    ]

    # Detecção simples de Mobile
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