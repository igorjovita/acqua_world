from decimal import Decimal
from django.db.models import Sum
from django.db import models
from django.core.exceptions import ValidationError

class Cliente(models.Model):
    nome = models.CharField(max_length=150)
    documento = models.CharField(max_length=50, blank=True, null=True, help_text="RG, CPF ou Passaporte")
    telefone = models.CharField(max_length=30, blank=True, null=True)
    # Substitui a coluna "ROUPA" da planilha (ex: 1,88/88)
    altura = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text="Em metros (ex: 1.88)")
    peso = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Em KG (ex: 88.00)")
    
    def __str__(self):
        return self.nome

class Vendedor(models.Model):
    """Refere-se aos 'Comissários' das planilhas (ex: Temporada Hostel, Don Juan)"""
    nome = models.CharField(max_length=100)
    # Valores líquidos acordados com cada vendedor/parceiro
    neto_bat = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    neto_acp = models.DecimalField(max_digits=10, decimal_places=2, default=80.00)
    neto_turismo_1 = models.DecimalField(max_digits=10, decimal_places=2, default=330.00)
    neto_turismo_2 = models.DecimalField(max_digits=10, decimal_places=2, default=380.00)
    neto_scuba = models.DecimalField(max_digits=10, decimal_places=2, default=480.00)

    # Porcentagem fixa para cursos (ex: OWD, ADV) - pode ser ajustada conforme necessidade
    neto_curso = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    def __str__(self):
        return self.nome

class Funcionario(models.Model):
    """Para preencher as colunas 'DM' e 'FOTO' da planilha de operação"""
    FUNCAO_CHOICES = [
        ('INSTRUTOR', 'Instrutor / DM'),
        ('FOTOGRAFO', 'Fotógrafo'),
        ('STAFF', 'Staff Geral'),
        ('LOJA', 'Atendimento de Loja')
    ]
    nome = models.CharField(max_length=100)
    funcao = models.CharField(max_length=20, choices=FUNCAO_CHOICES)

    def __str__(self):
        return f"{self.nome} ({self.get_funcao_display()})"

class Atividade(models.Model):
    CATEGORIAS = [
        ('BATISMO', 'Batismo'),
        ('ACOMPANHANTE', 'Acompanhante'),
        ('TURISMO_1', 'Turismo 1 Queda'),
        ('TURISMO_2', 'Turismo 2 Quedas'),
        ('SCUBA_REVIEW', 'Scuba Review'),
        ('CURSO', 'Curso'),
    ]
    nome = models.CharField(max_length=100)
    apelido = models.CharField(max_length=15, help_text="Ex: BAT, TUR1, OWD, ACP")
    valor_padrao = models.DecimalField(max_digits=10, decimal_places=2)
    categoria_comissao = models.CharField(max_length=20, choices=CATEGORIAS)

    def __str__(self):
        return self.apelido

class Reserva(models.Model):
    SITUACAO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
    ]
    data = models.DateField(help_text="Data da operação")
    horario = models.TimeField(blank=True, null=True)
    embarcacao = models.CharField(max_length=100, default="Acqua World")
    vendedor = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name="reservas")
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default='PENDENTE')
    observacao_geral = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.embarcacao} ({self.vendedor.nome})"

class ClienteReserva(models.Model):
    """
    Representa CADA LINHA da planilha de Operação.
    Liga o Cliente específico à Reserva, definindo o que ele vai fazer e quem vai atendê-lo.
    """
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="passageiros")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    atividade = models.ForeignKey(Atividade, on_delete=models.PROTECT)
    
    # Operacional (Colunas 'DM', 'FOTO' e 'OBS')
    dm_responsavel = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name="mergulhos_guiados")
    pacote_foto = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: F10, VIDEO, CART")
    observacao = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: PRECISA ROUPA COLETE E REGULADOR")
    
    # Financeiro Individual
    valor_cobrado = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor final vendido para este cliente")
    neto_praticado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=True, help_text="Valor neto congelado no dia da venda")
    comissao_calculada = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)

    acerto_liquidado = models.BooleanField(default=False)
    data_acerto = models.DateField(null=True, blank=True) 
    forma_pg_acerto = models.CharField(max_length=50, null=True, blank=True)

    status_checkin = models.CharField(
        max_length=15, 
        choices=[('LOJA', 'Loja'), ('PIER', 'Pier')], 
        null=True, blank=True
    )


    # 2. Soma tudo que caiu no Caixa da Loja para este cliente
    @property
    def recebido_loja(self):
        total = self.pagamentos.filter(recebedor='LOJA').aggregate(Sum('valor'))['valor__sum']
        return total or Decimal('0.00')

    # 3. Soma tudo que ficou retido com o Vendedor para este cliente
    @property
    def retido_vendedor(self):
        total = self.pagamentos.filter(recebedor='VENDEDOR').aggregate(Sum('valor'))['valor__sum']
        return total or Decimal('0.00')

    # 4. A MÁGICA: O Status que processa a regra de negócio completa
    @property
    def status_financeiro(self):
        # 1. Verifica se o cliente pagou tudo (independente de com quem está o dinheiro)
        pago_total = self.recebido_loja + self.retido_vendedor
        if pago_total < self.valor_cobrado:
            deve = self.valor_cobrado - pago_total
            return f"CLIENTE DEVE: R$ {deve:.2f}"

        if self.acerto_liquidado:
            return "PAGO (FINALIZADO)"

        neto = self.neto_praticado if self.neto_praticado is not None else Decimal('0.00')
        saldo_acerto = neto - self.recebido_loja

        if saldo_acerto > 0:
            return f"RECEBER DO VENDEDOR: R$ {saldo_acerto:.2f}"
        elif saldo_acerto < 0:
            return f"PAGAR COMISSÃO: R$ {abs(saldo_acerto):.2f}"
        
        return "PAGO (FINALIZADO)"

    def save(self, *args, **kwargs):
        """
        1) Tira a "foto" do neto do vendedor no momento da criação e congela no banco.
        2) Calcula e persiste a comissão no banco de dados.
        """
        if self.reserva and self.atividade:
            # Só calcula o neto se ele ainda não existir (ou seja, quando a reserva for criada)
            # Assim, se o vendedor mudar a taxa no futuro, as vendas velhas ficam intactas.
            if self.neto_praticado is None:
                vendedor = self.reserva.vendedor
                categoria = self.atividade.categoria_comissao
                
                if categoria == 'BATISMO':
                    self.neto_praticado = vendedor.neto_bat
                elif categoria == 'ACOMPANHANTE':
                    self.neto_praticado = vendedor.neto_acp
                elif categoria == 'TURISMO_1':
                    self.neto_praticado = vendedor.neto_turismo_1
                elif categoria == 'TURISMO_2':
                    self.neto_praticado = vendedor.neto_turismo_2
                elif categoria == 'SCUBA_REVIEW':
                    self.neto_praticado = vendedor.neto_scuba
                elif categoria == 'CURSO':
                    comissao_curso = self.valor_cobrado * (vendedor.neto_curso / Decimal('100.00'))
                    self.neto_praticado = self.valor_cobrado - comissao_curso
                else:
                    self.neto_praticado = self.valor_cobrado # Sem categoria = Neto integral
            
            # A comissão é sempre: (Valor que o cliente pagou) - (O que a loja retém congelado)
            self.comissao_calculada = self.valor_cobrado - self.neto_praticado
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente.nome} - {self.atividade.apelido}"

class Pagamento(models.Model):
    FORMA_PG_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'PIX'),
        ('DEBITO', 'Cartão de Débito'),
        ('CREDITO', 'Cartão de Crédito'),
        ('DEPOSITO', 'Depósito'),
        ('VOUCHER', 'Voucher'),
    ]
    RECEBEDOR_CHOICES = [
        ('LOJA', 'Acqua World (Loja)'),
        ('VENDEDOR', 'Vendedor/Comissário'),
    ]
    
    cliente_reserva = models.ForeignKey(ClienteReserva, on_delete=models.CASCADE, related_name="pagamentos")
    data_pagamento = models.DateField(auto_now_add=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pg = models.CharField(max_length=20, choices=FORMA_PG_CHOICES)
    recebedor = models.CharField(max_length=20, choices=RECEBEDOR_CHOICES, default='LOJA', help_text="Quem está com o dinheiro/recebeu o PIX?")
    descricao = models.CharField(max_length=150, blank=True, null=True, help_text="Ex: pg efferim, deposito antecipado")

    def __str__(self):
        return f"R$ {self.valor} ({self.forma_pg}) - {self.cliente_reserva.cliente.nome}"

class Caixa(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída')
    ]
    data = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255, help_text="Ex: SANGRIA ALE, LETICIA E ANDRESSA")
    forma_pg = models.CharField(max_length=50, blank=True, null=True, help_text="PIX, Débito, etc.")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Campo opcional para linkar uma entrada de caixa diretamente a um pagamento efetuado
    pagamento_origem = models.OneToOneField(Pagamento, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_caixa")

    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} - {self.descricao}"