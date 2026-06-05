from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Aluno, RFIDTag, Vaga, Aviso

class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ['nome', 'matricula', 'email', 'rfid']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matrícula'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-mail'}),
            'rfid': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *value, **kwargs):
        super(AlunoForm, self).__init__(*value, **kwargs)
        # Exibir apenas tags RFID que não estão associadas a nenhum aluno,
        # ou a tag que já está associada a este aluno (no caso de edição)
        available_tags = RFIDTag.objects.filter(aluno__isnull=True)
        if self.instance and self.instance.pk and self.instance.rfid:
            available_tags = available_tags | RFIDTag.objects.filter(pk=self.instance.rfid.pk)
        
        self.fields['rfid'].queryset = available_tags.distinct()
        self.fields['rfid'].empty_label = "Selecione um crachá (Opcional)"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Por favor, insira um endereço de e-mail válido.")
            
            # Garantir formato completo (ex: nome@dominio.com)
            parts = email.split('@')
            if len(parts) == 2:
                domain = parts[1]
                if '.' not in domain or domain.endswith('.') or domain.startswith('.'):
                    raise ValidationError("O domínio do e-mail é inválido (deve conter '.' e um TLD válido).")
        return email


class VagaForm(forms.ModelForm):
    class Meta:
        model = Vaga
        fields = ['numero', 'status', 'aluno_atual']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número da vaga'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'aluno_atual': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(VagaForm, self).__init__(*args, **kwargs)
        self.fields['aluno_atual'].empty_label = "Nenhum (Disponível / Bloqueado)"


class AvisoForm(forms.ModelForm):
    class Meta:
        model = Aviso
        fields = ['titulo', 'texto', 'link', 'foto', 'foto_fit', 'data_expiracao', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título do aviso'}),
            'texto': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Texto detalhado do aviso', 'rows': 4}),
            'link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'foto_fit': forms.Select(attrs={'class': 'form-select'}),
            'data_expiracao': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
