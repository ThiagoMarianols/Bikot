from django.core.management.base import BaseCommand
from core.models import Vaga, RFIDTag, Aluno

class Command(BaseCommand):
    help = "Inicializa o banco de dados com 10 vagas e cadastros de teste."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando configuração inicial do banco de dados...")
        
        # Garantir 10 vagas
        for i in range(1, 11):
            vaga, created = Vaga.objects.get_or_create(
                numero=i,
                defaults={'status': 'disponivel'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Vaga #{i} criada."))
            else:
                if i % 3 == 0 and vaga.status == 'disponivel':
                    vaga.status = 'ocupada'
                    vaga.save()

        # Cadastrar tags e alunos padrões para teste imediato
        tags_default = [
            ("01 02 03 04", "Pedro Silva", "20260001", "pedro@example.com"),
            ("11 22 33 44", "Ana Oliveira", "20260002", "ana@example.com"),
            ("55 66 77 88", "Carlos Santos", "20260003", "carlos@example.com"),
            ("04 11 22 33 44 55 66", "Julia Costa", "20260004", "julia@example.com"),
            ("C0 FF EE 99", "Bruno Souza", "20260005", "bruno@example.com")
        ]
        
        for uid, nome, matricula, email in tags_default:
            tag, created_tag = RFIDTag.objects.get_or_create(uid=uid, defaults={"ativo": True})
            if created_tag:
                self.stdout.write(self.style.SUCCESS(f"Tag RFID {uid} cadastrada."))
            
            if not Aluno.objects.filter(rfid=tag).exists() and not Aluno.objects.filter(matricula=matricula).exists():
                Aluno.objects.create(nome=nome, matricula=matricula, email=email, rfid=tag)
                self.stdout.write(self.style.SUCCESS(f"Aluno {nome} vinculado à tag {uid}."))
        
        self.stdout.write(self.style.SUCCESS("Configuração concluída com sucesso!"))
