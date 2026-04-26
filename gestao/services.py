# gestao/services.py
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from .models import Reserva, Vendedor, Cliente, Atividade, ClienteReserva, Pagamento, Caixa

@transaction.atomic
def processar_salvamento_reserva(dados_post):
    """
    Recebe o request.POST e processa toda a lógica pesada de criação
    ou atualização de Reserva, Clientes, Pagamentos e Livro Caixa.
    """
    reserva_id_edicao = dados_post.get('reserva_id_edicao')
    vendedor_id = dados_post.get('vendedor')
    vendedor = Vendedor.objects.get(id=vendedor_id) if vendedor_id else None
    data_reserva = dados_post.get('data')

    # 1. Cria ou Atualiza a Reserva
    if reserva_id_edicao:
        reserva = Reserva.objects.get(id=reserva_id_edicao)
        reserva.data = data_reserva
        reserva.vendedor = vendedor
        reserva.save()
    else:
        reserva = Reserva.objects.create(data=data_reserva, vendedor=vendedor)

    # 2. Captura todas as listas enviadas pelo HTML
    cr_ids = dados_post.getlist("cr_id")
    nomes = dados_post.getlist("nome")
    telefones = dados_post.getlist("telefone")
    documentos = dados_post.getlist("documento")
    pesos = dados_post.getlist("peso")
    alturas = dados_post.getlist("altura")
    atividades_ids = dados_post.getlist("atividade")
    valores = dados_post.getlist("valor")

    status_checkins = dados_post.getlist("status_checkin")
    
    tem_sinais = dados_post.getlist("tem_sinal")
    valores_sinal = dados_post.getlist("valor_sinal")
    formas_pg_sinal = dados_post.getlist("forma_pg_sinal")
    recebedores_sinal = dados_post.getlist("recebedor_sinal")

    # Gestão de remoção na edição (Deleta quem foi tirado da tela)
    if reserva_id_edicao:
        ids_recebidos = [int(i) for i in cr_ids if i.strip()]
        reserva.passageiros.exclude(id__in=ids_recebidos).delete()

    # 3. LOOP DE SALVAMENTO DOS PASSAGEIROS
    for i in range(len(nomes)):
        if not nomes[i].strip(): continue

        # Tratamento do Documento (Cria TEMP se vazio)
        doc_final = documentos[i].strip() if (i < len(documentos) and documentos[i].strip()) else f"TEMP_{reserva.id}_{i}"
        
        cliente, _ = Cliente.objects.get_or_create(
            documento=doc_final,
            defaults={'nome': nomes[i]}
        )
        
        # Atualiza dados do cliente sempre (caso a pessoa tenha corrigido o nome ou preenchido peso)
        cliente.nome = nomes[i]
        if i < len(telefones): cliente.telefone = telefones[i]
        if i < len(pesos) and pesos[i]: cliente.peso = Decimal(pesos[i].replace(',', '.'))
        if i < len(alturas) and alturas[i]: cliente.altura = Decimal(alturas[i].replace(',', '.'))
        cliente.save()

        # Busca a Atividade e trata o valor cobrado
        atividade = Atividade.objects.get(id=atividades_ids[i]) if atividades_ids[i] else None
        valor_c = Decimal(valores[i].replace(',', '.')) if valores[i] else Decimal('0.00')

        cr_id_atual = cr_ids[i] if i < len(cr_ids) else ""
        status_c = status_checkins[i] if i < len(status_checkins) else ""
        
        # Cria ou Atualiza o ClienteReserva
        if cr_id_atual.strip():
            cr = ClienteReserva.objects.get(id=int(cr_id_atual))
            cr.cliente = cliente
            cr.atividade = atividade
            cr.valor_cobrado = valor_c
            cr.status_checkin = status_c
            cr.save() # A comissão já é calculada automaticamente lá no models.py!
        else:
            cr = ClienteReserva.objects.create(
                reserva=reserva,
                cliente=cliente,
                atividade=atividade,
                valor_cobrado=valor_c,
                status_checkin=status_c
            )

        # 4. PAGAMENTOS (SINAL E CAIXA)
        # Limpa sinais antigos se for edição para evitar duplicidade de valores
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
                # Se o sinal caiu na LOJA, joga direto para o Livro Caixa
                if recebedores_sinal[i] == 'LOJA':
                    Caixa.objects.create(
                        data=reserva.data,
                        tipo='ENTRADA',
                        descricao=f"SINAL: {cliente.nome} ({atividade.apelido})".upper(),
                        forma_pg=formas_pg_sinal[i],
                        valor=v_sinal,
                        pagamento_origem=p
                    )


@transaction.atomic
def processar_pagamentos_loja(dados_post):
    reserva_id = dados_post.get("reserva_id")
    ids_passageiros = dados_post.getlist("ids_passageiros")
    valor_total = Decimal(dados_post.get("valor_total_pagamento").replace(',', '.'))
    forma_pg = dados_post.get("forma_pg")
    data_pg = dados_post.get("data_pagamento")
    recebedor = dados_post.get("recebedor_pg")
    pagador = dados_post.get("pagador_pg")
    
    if valor_total <= 0 or not ids_passageiros:
        return

    # Para fins de registo, usamos o primeiro passageiro selecionado como referência principal
    cr_referencia = ClienteReserva.objects.get(id=ids_passageiros[0])
    
    desc_extrato = f"Pagamento Parcial ({pagador})"
    desc_caixa = f"PAGAMENTO: {cr_referencia.cliente.nome} + {len(ids_passageiros)-1}".upper()

    p = Pagamento.objects.create(
        cliente_reserva=cr_referencia,
        valor=valor_total,
        forma_pg=forma_pg,
        recebedor=recebedor,
        descricao=desc_extrato,
        data_pagamento=data_pg,
    )
    
    if recebedor == 'LOJA':
        Caixa.objects.create(
            data=data_pg,
            tipo='ENTRADA',
            descricao=desc_caixa,
            forma_pg=forma_pg,
            valor=valor_total,
            pagamento_origem=p
        )


@transaction.atomic
def processar_acerto_comissao(dados_post):
    """
    Processa o acerto de contas em lote com um vendedor parceiro.
    Liquida as reservas selecionadas e lança o saldo no Livro Caixa automaticamente.
    """
    cr_ids_str = dados_post.get('cr_ids')
    data_acerto = dados_post.get('data_acerto')
    forma_pg_acerto = dados_post.get('forma_pg_acerto')
    
    if not cr_ids_str:
        return # Proteção caso venha vazio
        
    lista_ids = cr_ids_str.split(',')
    objetos = ClienteReserva.objects.filter(id__in=lista_ids)
    
    if not objetos.exists():
        return
        
    # Automação de Caixa (se saldo != 0)
    saldo_total = sum((o.neto_praticado - o.recebido_loja) for o in objetos)
    
    if saldo_total != 0:
        v_nome = objetos.first().reserva.vendedor.nome
        Caixa.objects.create(
            data=data_acerto,
            tipo='ENTRADA' if saldo_total > 0 else 'SAIDA',
            descricao=f"ACERTO COMISSÃO: {v_nome}".upper(),
            forma_pg=forma_pg_acerto,
            valor=abs(saldo_total)
        )

    # Marca todos os clientes selecionados como liquidados
    objetos.update(
        acerto_liquidado=True, 
        data_acerto=data_acerto, 
        forma_pg_acerto=forma_pg_acerto
    )



@transaction.atomic
def deletar_cliente_da_reserva(delete_id):
    """
    Remove um passageiro da reserva. Se a reserva ficar vazia, remove a reserva mãe.
    """
    if not delete_id:
        return
        
    try:
        cr = ClienteReserva.objects.get(id=delete_id)
        reserva = cr.reserva
        cr.delete() # Apaga o passageiro
        
        # Se a reserva ficou vazia, limpa o lixo do banco
        if reserva.passageiros.count() == 0:
            reserva.delete()
    except ClienteReserva.DoesNotExist:
        pass


@transaction.atomic
def deletar_pagamento_loja(pagamento_id):
    """ Deleta um pagamento e remove o lançamento do Livro Caixa atrelado a ele. """
    p = Pagamento.objects.filter(id=pagamento_id).first()
    if p:
        # Deleta do Caixa primeiro (se existir)
        Caixa.objects.filter(pagamento_origem=p).delete()
        # Deleta o pagamento
        p.delete()