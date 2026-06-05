from django.contrib import admin
from .models import RFIDTag, Aluno, Vaga, RegistroMovimentacao, RFIDCadastroPendente, Aviso

@admin.register(RFIDTag)
class RFIDTagAdmin(admin.ModelAdmin):
    list_display = ('uid', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('uid',)

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'matricula', 'email', 'rfid')
    search_fields = ('nome', 'matricula', 'email')

@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'status', 'aluno_atual', 'pending_unlock')
    list_filter = ('status', 'pending_unlock')

@admin.register(RegistroMovimentacao)
class RegistroMovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'acao', 'aluno', 'rfid_uid', 'vaga')
    list_filter = ('acao', 'timestamp')
    search_fields = ('rfid_uid', 'aluno__nome')

@admin.register(RFIDCadastroPendente)
class RFIDCadastroPendenteAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'status', 'scanned_uid', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('aluno__nome', 'scanned_uid')

@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'ativo', 'timestamp')
    list_filter = ('ativo', 'timestamp')
    search_fields = ('titulo', 'texto')

