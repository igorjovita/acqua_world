from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from gestao.models import Caixa, Cliente, Vendedor, Atividade, Reserva, ClienteReserva, Pagamento

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
