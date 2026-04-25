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
        
        # Cria ou Atualiza o ClienteReserva
        if cr_id_atual.strip():
            cr = ClienteReserva.objects.get(id=int(cr_id_atual))
            cr.cliente = cliente
            cr.atividade = atividade
            cr.valor_cobrado = valor_c
            cr.save() # A comissão já é calculada automaticamente lá no models.py!
        else:
            cr = ClienteReserva.objects.create(
                reserva=reserva,
                cliente=cliente,
                atividade=atividade,
                valor_cobrado=valor_c
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