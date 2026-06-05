import sys
import time
import serial
from django.core.management.base import BaseCommand
from core.models import Vaga, RFIDTag, Aluno, RegistroMovimentacao, RFIDCadastroPendente

class Command(BaseCommand):
    help = "Monitores serial output from the ESP32 to synchronize Vaga #1 with physical state."

    def add_arguments(self, parser):
        parser.add_argument("port", type=str, help="The COM/Serial port name (e.g. COM3 or /dev/ttyUSB0)")
        parser.add_argument("--baudrate", type=int, default=115200, help="Baud rate (default 115200)")

    def handle(self, *args, **options):
        # 1. SETUP DE DADOS
        self.stdout.write("Iniciando configuração inicial do banco de dados...")
        
        # Garantir 10 vagas no sistema (1 a 10)
        for i in range(1, 11):
            vaga, created = Vaga.objects.get_or_create(
                numero=i,
                defaults={'status': 'disponivel'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Vaga #{i} criada com sucesso."))
            else:
                # Vagas de 2 a 10 podem ser mantidas mockadas. A Vaga 1 será controlada pela ESP32
                if i != 1 and vaga.status == 'disponivel' and i % 3 == 0:
                    vaga.status = 'ocupada'
                    vaga.save()

        # Cadastrar as tags padrões da ESP32 com alunos fictícios para simulação imediata
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
                self.stdout.write(self.style.SUCCESS(f"Tag RFID {uid} pré-cadastrada."))
            
            if not Aluno.objects.filter(rfid=tag).exists() and not Aluno.objects.filter(matricula=matricula).exists():
                Aluno.objects.create(nome=nome, matricula=matricula, email=email, rfid=tag)
                self.stdout.write(self.style.SUCCESS(f"Aluno {nome} vinculado à tag {uid}."))

        # 2. INICIAR COMUNICAÇÃO SERIAL
        port = options["port"]
        baudrate = options["baudrate"]
        
        self.stdout.write(self.style.SUCCESS(f"Tentando abrir conexão serial em {port} ({baudrate} bps)..."))
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao conectar na porta serial {port}: {e}"))
            self.stdout.write(self.style.WARNING("Certifique-se de que a placa está conectada ou o simulador está redirecionando para esta porta."))
            sys.exit(1)
            
        self.stdout.write(self.style.SUCCESS("Conexão serial estabelecida! Aguardando dados da ESP32..."))
        
        last_seen_uid = None
        last_db_check = 0
        cadastro_notificado = False
        
        try:
            while True:
                # 1. Polling de status do Banco de Dados para notificar cadastro na Serial
                now = time.time()
                if now - last_db_check > 1.0:
                    last_db_check = now
                    try:
                        pending_session = RFIDCadastroPendente.objects.filter(status='pending').exists()
                        if pending_session:
                            if not cadastro_notificado:
                                ser.write(b"2\n")
                                cadastro_notificado = True
                                self.stdout.write(self.style.WARNING("Enviado '2' via Serial: Modo cadastro ativo no sistema."))
                        else:
                            cadastro_notificado = False
                    except Exception as db_err:
                        self.stdout.write(self.style.ERROR(f"Erro no polling de cadastro (BD/Serial): {db_err}"))

                # 2. Leitura da Serial
                if ser.in_waiting:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                    except Exception as parse_err:
                        continue
                        
                    if not line:
                        continue
                    
                    self.stdout.write(f"[RAW SERIAL] {line}")
                    
                    # Extrair UID com suporte flexível
                    uid = None
                    if "[RFID] UID detectado: " in line:
                        uid = line.split("[RFID] UID detectado: ")[1].strip()
                    elif "[RFID] UID nao cadastrado: " in line:
                        uid = line.split("[RFID] UID nao cadastrado: ")[1].strip()
                    elif "UID: " in line:
                        uid = line.split("UID: ")[1].strip()
                    else:
                        # Tentar verificar se é um UID cru (apenas hexadecimais e espaços)
                        cleaned_line = line.replace(" ", "")
                        if len(cleaned_line) >= 8 and len(cleaned_line) <= 20 and all(c in "0123456789ABCDEFabcdef" for c in cleaned_line):
                            uid = line.strip()

                    if uid:
                        last_seen_uid = uid
                        norm_uid = uid.replace(" ", "").upper()
                        
                        # A. Verificar fluxo de cadastro pendente
                        pending_session = RFIDCadastroPendente.objects.filter(status='pending').order_by('-timestamp').first()
                        if pending_session:
                            aluno = pending_session.aluno
                            old_rfid = aluno.rfid
                            
                            tag = RFIDTag.objects.filter(uid=uid).first()
                            if not tag:
                                for t in RFIDTag.objects.all():
                                    if t.uid.replace(" ", "").upper() == norm_uid:
                                        tag = t
                                        break
                            
                            if not tag:
                                tag = RFIDTag.objects.create(uid=uid, defaults={'ativo': True})
                            else:
                                tag.ativo = True
                                tag.save()

                            # Desvincular de outro aluno se necessário
                            try:
                                other_aluno = tag.aluno
                                if other_aluno != aluno:
                                    other_aluno.rfid = None
                                    other_aluno.save()
                                    self.stdout.write(self.style.WARNING(f"Tag {uid} desvinculada do aluno antigo {other_aluno.nome}."))
                            except Aluno.DoesNotExist:
                                pass

                            aluno.rfid = tag
                            aluno.save()
                            
                            if old_rfid and old_rfid != tag:
                                old_rfid.delete()
                                
                            pending_session.status = 'success'
                            pending_session.scanned_uid = uid
                            pending_session.save()
                            
                            self.stdout.write(self.style.SUCCESS(f"SUCESSO: Crachá {uid} cadastrado e associado ao aluno {aluno.nome} via Serial!"))
                            
                            # Escreve 2 via Serial
                            try:
                                ser.write(b"2\n")
                                self.stdout.write("Enviado '2' via Serial: Cadastro realizado.")
                            except Exception as write_err:
                                self.stdout.write(self.style.ERROR(f"Erro ao escrever na Serial: {write_err}"))
                        
                        # B. Fluxo normal de validação de acesso
                        else:
                            tag = RFIDTag.objects.filter(uid=uid).first()
                            if not tag:
                                for t in RFIDTag.objects.all():
                                    if t.uid.replace(" ", "").upper() == norm_uid:
                                        tag = t
                                        break
                                        
                            aluno = None
                            if tag and tag.ativo:
                                try:
                                    aluno = tag.aluno
                                except Aluno.DoesNotExist:
                                    pass

                            if aluno:
                                vaga = Vaga.objects.get(numero=1)
                                if vaga.status == 'ocupada' and vaga.aluno_atual == aluno:
                                    vaga.status = 'disponivel'
                                    vaga.aluno_atual = None
                                    vaga.save()
                                    RegistroMovimentacao.objects.create(
                                        aluno=aluno,
                                        rfid_uid=uid,
                                        vaga=vaga,
                                        acao='saida'
                                    )
                                    self.stdout.write(self.style.SUCCESS(f"Vaga #1 LIBERADA (Retirada por {aluno.nome})"))
                                else:
                                    vaga.status = 'ocupada'
                                    vaga.aluno_atual = aluno
                                    vaga.save()
                                    RegistroMovimentacao.objects.create(
                                        aluno=aluno,
                                        rfid_uid=uid,
                                        vaga=vaga,
                                        acao='entrada'
                                    )
                                    self.stdout.write(self.style.SUCCESS(f"Vaga #1 OCUPADA por {aluno.nome} (UID: {uid})"))

                                # Escreve 1 via Serial
                                try:
                                    ser.write(b"1\n")
                                    self.stdout.write("Enviado '1' via Serial: Liberação de Vaga.")
                                except Exception as write_err:
                                    self.stdout.write(self.style.ERROR(f"Erro ao escrever na Serial: {write_err}"))
                            
                            else:
                                # Acesso negado
                                RegistroMovimentacao.objects.create(
                                    aluno=None,
                                    rfid_uid=uid,
                                    vaga=Vaga.objects.get(numero=1),
                                    acao='bloqueio'
                                )
                                self.stdout.write(self.style.WARNING(f"ACESSO NEGADO na Vaga #1 para a tag: {uid}"))
                                
                                # Escreve 3 via Serial
                                try:
                                    ser.write(b"3\n")
                                    self.stdout.write("Enviado '3' via Serial: Acesso Negado.")
                                except Exception as write_err:
                                    self.stdout.write(self.style.ERROR(f"Erro ao escrever na Serial: {write_err}"))

                    # Fallbacks para suporte a comandos antigos e sincronizações de estado directas
                    else:
                        # Entrada da bicicleta na Vaga 1 (comando direto antigo)
                        if "[ENTRADA] UID vinculado a bike: " in line:
                            val_uid = line.split("[ENTRADA] UID vinculado a bike: ")[1].strip()
                            norm_val_uid = val_uid.replace(" ", "").upper()
                            tag_obj = None
                            for t in RFIDTag.objects.all():
                                if t.uid.replace(" ", "").upper() == norm_val_uid:
                                    tag_obj = t
                                    break
                            aluno_obj = tag_obj.aluno if (tag_obj and hasattr(tag_obj, 'aluno')) else None
                            
                            vaga = Vaga.objects.get(numero=1)
                            vaga.status = 'ocupada'
                            vaga.aluno_atual = aluno_obj
                            vaga.save()
                            RegistroMovimentacao.objects.create(
                                aluno=aluno_obj,
                                rfid_uid=val_uid,
                                vaga=vaga,
                                acao='entrada'
                            )
                            self.stdout.write(self.style.SUCCESS(f"Vaga #1 OCUPADA via comando legado por {aluno_obj}"))
                        
                        # Saída da bicicleta na Vaga 1 (comando direto antigo)
                        elif "[SAIDA] Mesmo cartao detectado" in line:
                            vaga = Vaga.objects.get(numero=1)
                            aluno_obj = vaga.aluno_atual
                            val_uid = aluno_obj.rfid.uid if (aluno_obj and aluno_obj.rfid) else "N/A"
                            vaga.status = 'disponivel'
                            vaga.aluno_atual = None
                            vaga.save()
                            RegistroMovimentacao.objects.create(
                                aluno=aluno_obj,
                                rfid_uid=val_uid,
                                vaga=vaga,
                                acao='saida'
                            )
                            self.stdout.write(self.style.SUCCESS("Vaga #1 LIBERADA via comando legado."))
                        
                        # IDLE (Vaga Livre)
                        elif "[ESTADO] IDLE: vaga livre" in line:
                            vaga = Vaga.objects.get(numero=1)
                            if vaga.status != 'disponivel' or vaga.aluno_atual is not None:
                                vaga.status = 'disponivel'
                                vaga.aluno_atual = None
                                vaga.save()
                                self.stdout.write(self.style.SUCCESS("Vaga #1 sincronizada como DISPONÍVEL."))
                        
                        # Bike Trancada
                        elif "[ESTADO] BIKE_TRANCADA: bike presa" in line:
                            vaga = Vaga.objects.get(numero=1)
                            if vaga.status != 'ocupada':
                                vaga.status = 'ocupada'
                                vaga.save()
                                self.stdout.write(self.style.SUCCESS("Vaga #1 sincronizada como OCUPADA (Bike Trancada)."))
                        
                        # Logs de Acesso Negado (antigo)
                        elif "[ACESSO NEGADO]" in line:
                            reason = line.split("[ACESSO NEGADO]")[1].strip()
                            self.stdout.write(self.style.WARNING(f"Acesso Negado Legado: {reason}"))
                            RegistroMovimentacao.objects.create(
                                aluno=None,
                                rfid_uid=last_seen_uid or "N/A",
                                vaga=Vaga.objects.get(numero=1),
                                acao='bloqueio'
                            )

                time.sleep(0.01)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nConexão encerrada pelo usuário."))
            ser.close()
        except Exception as run_err:
            self.stdout.write(self.style.ERROR(f"Erro durante a execução: {run_err}"))
            ser.close()
