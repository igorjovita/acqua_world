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
    neto_bat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Neto Batismo (BAT)")
    neto_acp = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Neto Acompanhante (ACP)")
    neto_tur = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Neto Turismo (TUR)")

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
    nome = models.CharField(max_length=100)
    apelido = models.CharField(max_length=15, help_text="Ex: BAT, TUR1, OWD, ACP")
    valor_padrao = models.DecimalField(max_digits=10, decimal_places=2)

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
    comissao_calculada = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)

    acerto_liquidado = models.BooleanField(default=False)
    data_acerto = models.DateField(null=True, blank=True) 
    forma_pg_acerto = models.CharField(max_length=50, null=True, blank=True)

    # 1. Pega o valor Neto correto dependendo da atividade (Ex: Batismo, Turismo)
    @property
    def neto_atividade(self):
        if not self.atividade or not self.reserva.vendedor:
            return Decimal('0.00')
            
        sigla = self.atividade.apelido.upper()
        vendedor = self.reserva.vendedor
        
        if sigla == 'BAT': return vendedor.neto_bat
        elif sigla == 'ACP': return vendedor.neto_acp
        elif sigla == 'TUR': return vendedor.neto_tur
        return Decimal('0.00')

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
        # Passo A: Verifica se o cliente ainda deve o passeio
        pago_pelo_cliente = self.recebido_loja + self.retido_vendedor
        saldo_cliente = self.valor_cobrado - pago_pelo_cliente

        if saldo_cliente > 0:
            return f"CLIENTE DEVE: R$ {saldo_cliente:.2f}"

        # Passo B: Se o acerto já foi dado como liquidado/transferido no sistema
        if self.acerto_liquidado:
            return "PAGO (FINALIZADO)"

        # Passo C: Encontro de Contas (Acqua vs Vendedor)
        # O objetivo da Acqua é ficar exatamente com o valor do NETO.
        saldo_acerto = self.neto_atividade - self.recebido_loja

        if saldo_acerto > 0:
            return f"RECEBER DO VENDEDOR: R$ {saldo_acerto:.2f}"
        elif saldo_acerto < 0:
            return f"PAGAR COMISSÃO: R$ {abs(saldo_acerto):.2f}"
        else:
            return "PAGO (FINALIZADO)" # Deu zero redondo (cada um com sua parte)

    def save(self, *args, **kwargs):
        # Lógica para calcular a comissão automaticamente baseada no Vendedor e na Atividade
        if self.reserva and self.atividade:
            vendedor = self.reserva.vendedor
            sigla = self.atividade.apelido.upper()
            
            # Define qual valor 'neto' usar
            if 'BAT' in sigla:
                neto = vendedor.neto_bat
            elif 'ACP' in sigla:
                neto = vendedor.neto_acp
            elif 'TUR' in sigla:
                neto = vendedor.neto_tur
            else:
                neto = self.valor_cobrado # Se não for comissionado, não gera comissão
                
            # Comissão = Valor Cobrado do Cliente - Valor Neto (que fica para a loja)
            self.comissao_calculada = self.valor_cobrado - neto
            
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