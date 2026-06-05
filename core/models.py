from django.db import models

class RFIDTag(models.Model):
    uid = models.CharField(max_length=50, unique=True, verbose_name="UID do Crachá")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Tag RFID"
        verbose_name_plural = "Tags RFID"
        ordering = ['uid']

    def __str__(self):
        status_str = "Ativo" if self.ativo else "Inativo"
        return f"{self.uid} ({status_str})"

class Aluno(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome")
    matricula = models.CharField(max_length=50, unique=True, verbose_name="Matrícula")
    email = models.EmailField(verbose_name="E-mail")
    rfid = models.OneToOneField(
        RFIDTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aluno",
        verbose_name="RFID / Crachá"
    )

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.matricula})"

class Vaga(models.Model):
    STATUS_CHOICES = [
        ('disponivel', 'Disponível'),
        ('ocupada', 'Ocupada'),
        ('bloqueada', 'Bloqueada'),
    ]

    numero = models.IntegerField(unique=True, verbose_name="Número da Vaga")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='disponivel',
        verbose_name="Status"
    )
    aluno_atual = models.ForeignKey(
        Aluno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vaga_atual",
        verbose_name="Aluno Atual"
    )
    pending_unlock = models.BooleanField(default=False, verbose_name="Destravamento Pendente")

    class Meta:
        verbose_name = "Vaga"
        verbose_name_plural = "Vagas"
        ordering = ['numero']

    def __str__(self):
        return f"Vaga #{self.numero} ({self.get_status_display()})"

class RegistroMovimentacao(models.Model):
    ACAO_CHOICES = [
        ('entrada', 'Entrada (Estacionar)'),
        ('saida', 'Saída (Retirar)'),
        ('liberacao_manual', 'Liberação Manual'),
        ('bloqueio', 'Bloqueio'),
        ('desbloqueio', 'Desbloqueio'),
        ('destravamento_remoto', 'Destravamento Remoto'),
    ]

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_movimentacao",
        verbose_name="Aluno"
    )
    rfid_uid = models.CharField(max_length=50, verbose_name="UID do RFID")
    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_movimentacao",
        verbose_name="Vaga"
    )
    acao = models.CharField(
        max_length=30,
        choices=ACAO_CHOICES,
        verbose_name="Ação"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Registro de Movimentação"
        verbose_name_plural = "Registros de Movimentação"
        ordering = ['-timestamp']

    def __str__(self):
        vaga_str = f" na Vaga #{self.vaga.numero}" if self.vaga else ""
        aluno_str = self.aluno.nome if self.aluno else f"RFID: {self.rfid_uid}"
        return f"{self.get_acao_display()} - {aluno_str}{vaga_str} em {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

class RFIDCadastroPendente(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('success', 'Sucesso'),
        ('failed', 'Falhou'),
    ]
    aluno = models.OneToOneField(
        Aluno,
        on_delete=models.CASCADE,
        related_name="cadastro_pendente",
        verbose_name="Aluno"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    scanned_uid = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="UID Escaneado"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora de Início")

    class Meta:
        verbose_name = "Cadastro Pendente de RFID"
        verbose_name_plural = "Cadastros Pendentes de RFID"

    def __str__(self):
        return f"Cadastro {self.get_status_display()} para {self.aluno.nome}"


class Aviso(models.Model):
    titulo = models.CharField(max_length=150, verbose_name="Título")
    texto = models.TextField(verbose_name="Texto do Aviso")
    link = models.URLField(blank=True, null=True, verbose_name="Link (Gera QR Code)")
    foto = models.FileField(upload_to='avisos/', blank=True, null=True, verbose_name="Foto/Anúncio")
    FIT_CHOICES = [
        ('cover', 'Preencher (Pode cortar bordas)'),
        ('contain', 'Ajustar (Não corta, pode deixar bordas)'),
    ]
    foto_fit = models.CharField(
        max_length=10,
        choices=FIT_CHOICES,
        default='cover',
        verbose_name="Ajuste da Foto na TV"
    )
    data_expiracao = models.DateTimeField(blank=True, null=True, verbose_name="Data/Hora de Expiração")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora de Criação")

    class Meta:
        verbose_name = "Aviso"
        verbose_name_plural = "Avisos"
        ordering = ['-timestamp']

    def __str__(self):
        return self.titulo


class Configuracao(models.Model):
    chave = models.CharField(max_length=100, unique=True, verbose_name="Chave")
    valor = models.CharField(max_length=255, verbose_name="Valor")

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"

    def __str__(self):
        return f"{self.chave}: {self.valor}"


