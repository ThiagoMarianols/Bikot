from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
import json

from .models import RFIDTag, Aluno, Vaga, RegistroMovimentacao, RFIDCadastroPendente, Aviso

@override_settings(ESP32_API_KEY='test-key')
class BikotTests(TestCase):
    def setUp(self):
        # Criar usuário de testes para autenticação
        self.user = User.objects.create_user(username='testadmin', password='testpassword')
        self.client = Client()

        # Criar Tags RFID
        self.tag_ativa = RFIDTag.objects.create(uid="A1B2C3D4", ativo=True)
        self.tag_inativa = RFIDTag.objects.create(uid="E5F6G7H8", ativo=False)
        self.tag_sem_aluno = RFIDTag.objects.create(uid="99999999", ativo=True)

        # Criar Alunos
        self.aluno1 = Aluno.objects.create(
            nome="Joao Silva",
            matricula="20210001",
            email="joao@example.com",
            rfid=self.tag_ativa
        )
        self.aluno_sem_vaga = Aluno.objects.create(
            nome="Maria Souza",
            matricula="20210002",
            email="maria@example.com",
            rfid=self.tag_inativa # Tag inativa
        )

        # Criar Vagas
        self.vaga1 = Vaga.objects.create(numero=1, status='disponivel')
        self.vaga2 = Vaga.objects.create(numero=2, status='disponivel')
        self.vaga_bloqueada = Vaga.objects.create(numero=3, status='bloqueada')

    def test_api_rfid_scan_invalid_tag(self):
        # Testar tag inexistente
        response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": "00000000"}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['codigo'], 3)

    def test_api_rfid_scan_inactive_tag(self):
        # Testar tag inativa
        response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_inativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['codigo'], 3)

    def test_api_rfid_scan_tag_without_aluno(self):
        # Testar tag sem aluno
        response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_sem_aluno.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['codigo'], 3)

    def test_api_rfid_scan_estacionar_e_retirar(self):
        # --- 1. Entrada (Estacionar) ---
        response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['codigo'], 1)

        # Verificar se a vaga foi atualizada
        vaga = Vaga.objects.get(numero=self.vaga1.numero)
        self.assertEqual(vaga.status, 'ocupada')
        self.assertEqual(vaga.aluno_atual, self.aluno1)
        self.assertTrue(vaga.pending_unlock)

        # Verificar se registrou a movimentação
        log = RegistroMovimentacao.objects.first()
        self.assertEqual(log.aluno, self.aluno1)
        self.assertEqual(log.rfid_uid, self.tag_ativa.uid)
        self.assertEqual(log.vaga, vaga)
        self.assertEqual(log.acao, 'entrada')

        # --- 2. Saída (Retirar) ---
        # Escanear novamente o mesmo crachá
        response2 = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(data2['codigo'], 1)

        # Verificar se a vaga foi liberada
        vaga.refresh_from_db()
        self.assertEqual(vaga.status, 'disponivel')
        self.assertIsNone(vaga.aluno_atual)
        self.assertTrue(vaga.pending_unlock)

        # Verificar se registrou a saída
        log2 = RegistroMovimentacao.objects.first()
        self.assertEqual(log2.aluno, self.aluno1)
        self.assertEqual(log2.vaga, vaga)
        self.assertEqual(log2.acao, 'saida')

    def test_api_get_vagas_clears_pending_unlock(self):
        # Forçar uma vaga com pending_unlock = True
        self.vaga1.status = 'ocupada'
        self.vaga1.aluno_atual = self.aluno1
        self.vaga1.pending_unlock = True
        self.vaga1.save()

        # Consumir o endpoint GET /api/vagas/
        response = self.client.get(reverse('api_get_vagas'), HTTP_X_API_KEY='test-key')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar se retornou a vaga com pending_unlock = True
        vaga1_data = next(vaga for vaga in data if vaga['numero'] == self.vaga1.numero)
        self.assertTrue(vaga1_data['pending_unlock'])

        # Verificar se limpou o flag no banco de dados após a leitura
        self.vaga1.refresh_from_db()
        self.assertFalse(self.vaga1.pending_unlock)

    def test_api_liberar_bloquear_vaga(self):
        # 1. Liberar vaga
        response = self.client.post(
            reverse('api_liberar_vaga_post'),
            data=json.dumps({"numero": self.vaga1.numero}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 200)
        
        # 2. Bloquear vaga
        response = self.client.post(
            reverse('api_bloquear_vaga_post'),
            data=json.dumps({"numero": self.vaga1.numero}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 200)
        self.vaga1.refresh_from_db()
        self.assertEqual(self.vaga1.status, 'bloqueada')

    def test_rfid_registration_flow(self):
        # Autenticar cliente para acessar endpoints protegidos
        self.client.login(username='testadmin', password='testpassword')

        # 1. Iniciar cadastro de RFID para aluno1
        response = self.client.post(
            reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno1.id})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Verificar se a sessão pendente foi criada no DB
        session_exists = RFIDCadastroPendente.objects.filter(aluno=self.aluno1, status='pending').exists()
        self.assertTrue(session_exists)

        # 2. Consultar status (deve estar pendente)
        response = self.client.get(
            reverse('api_rfid_register_status', kwargs={'aluno_id': self.aluno1.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'pending')

        # Guardar UID antigo para verificar se foi removido
        old_uid = self.tag_ativa.uid

        # 3. Simular o leitor escaneando um novo UID
        new_uid = "NEW12345"
        scan_response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": new_uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(scan_response.status_code, 200)
        scan_data = scan_response.json()
        self.assertEqual(scan_data['codigo'], 2)

        # 4. Verificar se o novo crachá foi criado e associado ao aluno1
        self.aluno1.refresh_from_db()
        self.assertIsNotNone(self.aluno1.rfid)
        self.assertEqual(self.aluno1.rfid.uid, new_uid)

        # Verificar se o crachá antigo foi excluído do DB
        self.assertFalse(RFIDTag.objects.filter(uid=old_uid).exists())

        # 5. Consultar status novamente (deve retornar sucesso com o novo UID)
        response_success = self.client.get(
            reverse('api_rfid_register_status', kwargs={'aluno_id': self.aluno1.id})
        )
        self.assertEqual(response_success.status_code, 200)
        status_data = response_success.json()
        self.assertEqual(status_data['status'], 'success')
        self.assertEqual(status_data['uid'], new_uid)

        # Verificar se a sessão pendente foi removida após a leitura de sucesso
        self.assertFalse(RFIDCadastroPendente.objects.filter(aluno=self.aluno1).exists())

    def test_rfid_registration_cancel(self):
        self.client.login(username='testadmin', password='testpassword')

        # 1. Iniciar cadastro
        self.client.post(reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno1.id}))

        # 2. Cancelar cadastro
        response = self.client.post(
            reverse('api_rfid_register_cancel', kwargs={'aluno_id': self.aluno1.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verificar se a sessão pendente foi deletada
        self.assertFalse(RFIDCadastroPendente.objects.filter(aluno=self.aluno1).exists())

    def test_api_get_alunos(self):
        self.client.login(username='testadmin', password='testpassword')
        response = self.client.get(reverse('api_get_alunos'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 2)
        # Verificar se os dados do aluno1 e aluno_sem_vaga estão corretos
        aluno1_data = next(aluno for aluno in data if aluno['id'] == self.aluno1.id)
        self.assertEqual(aluno1_data['nome'], self.aluno1.nome)
        self.assertEqual(aluno1_data['matricula'], self.aluno1.matricula)
        self.assertEqual(aluno1_data['rfid'], self.tag_ativa.uid)

    def test_api_rfid_scan_query_param_and_no_slash(self):
        # Testar chamada POST sem barra final e passando UID via query params
        response = self.client.post(
            '/api/rfid/scan?uid=teste123&api_key=test-key'
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['codigo'], 3)

    def test_api_rfid_scan_get_request(self):
        # Testar chamada GET passando UID e api_key via query params
        response = self.client.get(
            '/api/rfid/scan?uid=teste123&api_key=test-key'
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['codigo'], 3)

    def test_api_unauthorized_access(self):
        # Testar acessos sem chave de API nos endpoints protegidos (deve retornar 401)
        response_post = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json"
        )
        self.assertEqual(response_post.status_code, 401)
        self.assertFalse(response_post.json()['success'])

    def test_public_tv_and_vagas_api(self):
        # Tela da TV e API de vagas devem ser públicas (status 200 sem autenticação)
        response_tv = self.client.get(reverse('tv_dashboard'))
        self.assertEqual(response_tv.status_code, 200)

        response_vagas = self.client.get(reverse('api_get_vagas'))
        self.assertEqual(response_vagas.status_code, 200)

    def test_avisos_crud_auth_required(self):
        # Acesso sem login à lista de avisos deve redirecionar (302)
        response = self.client.get(reverse('aviso_list'))
        self.assertEqual(response.status_code, 302)

        # Acesso logado à lista de avisos deve retornar 200
        self.client.login(username='testadmin', password='testpassword')
        response_auth = self.client.get(reverse('aviso_list'))
        self.assertEqual(response_auth.status_code, 200)

    def test_api_get_avisos_public(self):
        # Criar aviso ativo e inativo
        Aviso.objects.create(titulo="Aviso Teste 1", texto="Conteúdo do aviso 1", ativo=True)
        Aviso.objects.create(titulo="Aviso Teste 2", texto="Conteúdo do aviso 2", ativo=False)

        # GET público no endpoint de avisos
        response = self.client.get(reverse('api_get_avisos'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Deve retornar apenas 1 aviso (o ativo) na lista de avisos
        avisos = data.get('avisos', [])
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]['titulo'], "Aviso Teste 1")
        self.assertEqual(data.get('tempo_exibicao'), 6)

    def test_api_rfid_scan_codigos_in_json(self):
        # 1. Liberação de Vaga (Código 1)
        response1 = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['codigo'], 1)

        # 2. Cadastro de RFID (Código 2)
        self.client.login(username='testadmin', password='testpassword')
        self.client.post(reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno1.id}))
        response2 = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": "NEWRFID999"}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['codigo'], 2)

        # 3. Acesso Negado (Código 3)
        response3 = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": "INVALID999"}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response3.status_code, 403)
        self.assertEqual(response3.json()['codigo'], 3)

    def test_api_rfid_scan_format_text(self):
        # 1. Liberação de Vaga (Código 1)
        response1 = self.client.post(
            reverse('api_rfid_scan') + "?format=text",
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.content.decode('utf-8'), "1")
        self.assertEqual(response1['Content-Type'], "text/plain")

        # 2. Cadastro de RFID (Código 2)
        self.client.login(username='testadmin', password='testpassword')
        self.client.post(reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno1.id}))
        response2 = self.client.post(
            reverse('api_rfid_scan') + "?format=text",
            data=json.dumps({"uid": "NEWRFID888"}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.content.decode('utf-8'), "2")

        # 3. Acesso Negado (Código 3)
        response3 = self.client.post(
            reverse('api_rfid_scan') + "?format=text",
            data=json.dumps({"uid": "INVALID888"}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response3.status_code, 403)
        self.assertEqual(response3.content.decode('utf-8'), "3")

    def test_api_rfid_scan_desassociacao_outro_aluno(self):
        # aluno1 está associado a tag_ativa. aluno_sem_vaga tem tag_inativa (inativa).
        # Vamos cadastrar a tag_ativa para o aluno_sem_vaga (ele deve herdar a tag, e aluno1 deve ficar sem)
        self.client.login(username='testadmin', password='testpassword')
        self.client.post(reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno_sem_vaga.id}))
        
        response = self.client.post(
            reverse('api_rfid_scan'),
            data=json.dumps({"uid": self.tag_ativa.uid}),
            content_type="application/json",
            HTTP_X_API_KEY='test-key'
        )
        self.assertEqual(response.status_code, 200)
        
        # aluno_sem_vaga agora possui a tag_ativa
        self.aluno_sem_vaga.refresh_from_db()
        self.assertEqual(self.aluno_sem_vaga.rfid, self.tag_ativa)
        
        # aluno1 foi desvinculado (rfid = None)
        self.aluno1.refresh_from_db()
        self.assertIsNone(self.aluno1.rfid)

    def test_api_esp_status(self):
        # 1. Sem comandos pendentes (Código 0)
        response1 = self.client.get(reverse('api_esp_status'), HTTP_X_API_KEY='test-key')
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['codigo'], 0)

        # Sem comandos pendentes em formato texto
        response1_text = self.client.get(reverse('api_esp_status') + "?format=text", HTTP_X_API_KEY='test-key')
        self.assertEqual(response1_text.status_code, 200)
        self.assertEqual(response1_text.content.decode('utf-8'), "0")

        # 2. Cadastro pendente ativo (Código 2)
        self.client.login(username='testadmin', password='testpassword')
        self.client.post(reverse('api_rfid_register_start', kwargs={'aluno_id': self.aluno1.id}))
        
        response2 = self.client.get(reverse('api_esp_status'), HTTP_X_API_KEY='test-key')
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['codigo'], 2)

        response2_text = self.client.get(reverse('api_esp_status') + "?format=text", HTTP_X_API_KEY='test-key')
        self.assertEqual(response2_text.status_code, 200)
        self.assertEqual(response2_text.content.decode('utf-8'), "2")

        # Remover cadastro pendente
        self.client.post(reverse('api_rfid_register_cancel', kwargs={'aluno_id': self.aluno1.id}))

        # 3. Destravamento pendente ativo (Código 1)
        self.vaga1.pending_unlock = True
        self.vaga1.save()

        response3 = self.client.get(reverse('api_esp_status'), HTTP_X_API_KEY='test-key')
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(response3.json()['codigo'], 1)
        self.assertEqual(response3.json()['vaga'], self.vaga1.numero)

        # Verificar se limpou o status do pending_unlock no banco
        self.vaga1.refresh_from_db()
        self.assertFalse(self.vaga1.pending_unlock)

        # Destravamento em formato texto
        self.vaga1.pending_unlock = True
        self.vaga1.save()
        response3_text = self.client.get(reverse('api_esp_status') + "?format=text", HTTP_X_API_KEY='test-key')
        self.assertEqual(response3_text.status_code, 200)
        self.assertEqual(response3_text.content.decode('utf-8'), "1")

    def test_api_get_avisos_filtering_and_fields(self):
        from django.utils import timezone
        from datetime import timedelta
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Limpar avisos existentes para evitar conflitos nos testes
        Aviso.objects.all().delete()

        # 1. Criar aviso ativo e sem expiração
        aviso_normal = Aviso.objects.create(
            titulo="Aviso Normal",
            texto="Texto do aviso normal",
            link="https://google.com",
            ativo=True
        )

        # 2. Criar aviso ativo que já expirou
        aviso_expirado = Aviso.objects.create(
            titulo="Aviso Expirado",
            texto="Texto do aviso expirado",
            ativo=True,
            data_expiracao=timezone.now() - timedelta(hours=1)
        )

        # 3. Criar aviso ativo que vai expirar no futuro
        aviso_futuro = Aviso.objects.create(
            titulo="Aviso Futuro",
            texto="Texto do aviso futuro",
            ativo=True,
            data_expiracao=timezone.now() + timedelta(hours=1)
        )

        # 4. Criar aviso inativo
        aviso_inativo = Aviso.objects.create(
            titulo="Aviso Inativo",
            texto="Texto do aviso inativo",
            ativo=False
        )

        # 5. Criar aviso com foto
        foto_mock = SimpleUploadedFile(
            name='test_ad.jpg',
            content=b'fake_image_content',
            content_type='image/jpeg'
        )
        aviso_com_foto = Aviso.objects.create(
            titulo="Aviso Foto",
            texto="Texto do aviso foto",
            foto=foto_mock,
            ativo=True
        )

        # Consumir o endpoint GET /api/avisos/
        response = self.client.get(reverse('api_get_avisos'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        avisos = data.get('avisos', [])

        # Deve conter 3 avisos: aviso_normal, aviso_futuro e aviso_com_foto
        # aviso_expirado e aviso_inativo devem ser filtrados fora
        self.assertEqual(len(avisos), 3)

        # Mapear títulos para validação rápida
        titulos = [aviso['titulo'] for aviso in avisos]
        self.assertIn("Aviso Normal", titulos)
        self.assertIn("Aviso Futuro", titulos)
        self.assertIn("Aviso Foto", titulos)
        self.assertNotIn("Aviso Expirado", titulos)
        self.assertNotIn("Aviso Inativo", titulos)

        # Validar conteúdo do aviso normal (deve retornar link e foto=None)
        aviso_norm_data = next(a for a in avisos if a['titulo'] == "Aviso Normal")
        self.assertEqual(aviso_norm_data['link'], "https://google.com")
        self.assertIsNone(aviso_norm_data['foto'])

        # Validar conteúdo do aviso com foto (deve retornar foto_url)
        aviso_foto_data = next(a for a in avisos if a['titulo'] == "Aviso Foto")
        self.assertIsNotNone(aviso_foto_data['foto'])
        self.assertIn('/media/avisos/test_ad', aviso_foto_data['foto'])

        # Deletar arquivo físico criado pelo teste
        if aviso_com_foto.foto:
            aviso_com_foto.foto.delete(save=False)

    def test_jwt_auth_flow(self):
        # 1. Obter token com credenciais válidas
        response = self.client.post(
            reverse('api_token_obtain'),
            data=json.dumps({
                'username': 'testadmin',
                'password': 'testpassword'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        
        access_token = data['access']
        refresh_token = data['refresh']

        # 2. Obter token com credenciais inválidas
        response_invalid = self.client.post(
            reverse('api_token_obtain'),
            data=json.dumps({
                'username': 'testadmin',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        self.assertEqual(response_invalid.status_code, 401)
        self.assertFalse(response_invalid.json()['success'])

        # 3. Acessar endpoint protegido com access token válido
        response_protected = self.client.get(
            reverse('api_get_alunos'),
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        self.assertEqual(response_protected.status_code, 200)

        # 4. Acessar endpoint protegido com token inválido
        response_unauthorized = self.client.get(
            reverse('api_get_alunos'),
            HTTP_AUTHORIZATION='Bearer invalidtoken'
        )
        self.assertEqual(response_unauthorized.status_code, 401)

        # 5. Atualizar token usando refresh token válido
        response_refresh = self.client.post(
            reverse('api_token_refresh'),
            data=json.dumps({
                'refresh': refresh_token
            }),
            content_type='application/json'
        )
        self.assertEqual(response_refresh.status_code, 200)
        refresh_data = response_refresh.json()
        self.assertTrue(refresh_data['success'])
        self.assertIn('access', refresh_data)
        
        new_access_token = refresh_data['access']

        # 6. Testar novo token gerado pelo refresh
        response_new_access = self.client.get(
            reverse('api_get_alunos'),
            HTTP_AUTHORIZATION=f'Bearer {new_access_token}'
        )
        self.assertEqual(response_new_access.status_code, 200)

        # 7. Atualizar token usando refresh token inválido
        response_refresh_invalid = self.client.post(
            reverse('api_token_refresh'),
            data=json.dumps({
                'refresh': 'invalidrefreshtoken'
            }),
            content_type='application/json'
        )
        self.assertEqual(response_refresh_invalid.status_code, 401)
        self.assertFalse(response_refresh_invalid.json()['success'])

    def test_aluno_form_email_validation(self):
        from core.forms import AlunoForm
        # 1. Email válido
        form_valid = AlunoForm(data={
            'nome': 'Carlos Silva',
            'matricula': '20219999',
            'email': 'carlos@dominio.com'
        })
        self.assertTrue(form_valid.is_valid())

        # 2. Email inválido (sem domínio correto ou malformado)
        form_invalid1 = AlunoForm(data={
            'nome': 'Carlos Silva',
            'matricula': '20219999',
            'email': 'carlos@dominio'
        })
        self.assertFalse(form_invalid1.is_valid())
        self.assertIn('email', form_invalid1.errors)

        form_invalid2 = AlunoForm(data={
            'nome': 'Carlos Silva',
            'matricula': '20219999',
            'email': 'carlos.com'
        })
        self.assertFalse(form_invalid2.is_valid())
        self.assertIn('email', form_invalid2.errors)






