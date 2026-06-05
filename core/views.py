import json
import jwt
from datetime import datetime, timedelta, timezone as dt_timezone
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User

from django.conf import settings
from .models import RFIDTag, Aluno, Vaga, RegistroMovimentacao, RFIDCadastroPendente, Aviso, Configuracao
from .forms import AlunoForm, VagaForm, AvisoForm

def generate_tokens(user):
    """
    Gera um token de acesso (access token) e um token de atualização (refresh token) para o usuário.
    """
    secret = getattr(settings, 'JWT_SECRET_KEY')
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    access_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60)
    refresh_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7)

    now = datetime.now(dt_timezone.utc)
    
    access_payload = {
        'token_type': 'access',
        'exp': now + timedelta(minutes=access_lifetime),
        'iat': now,
        'user_id': user.id,
        'username': user.username
    }
    
    refresh_payload = {
        'token_type': 'refresh',
        'exp': now + timedelta(days=refresh_lifetime),
        'iat': now,
        'user_id': user.id
    }
    
    access_token = jwt.encode(access_payload, secret, algorithm=algorithm)
    refresh_token = jwt.encode(refresh_payload, secret, algorithm=algorithm)
    
    return access_token, refresh_token

def decode_token(token, token_type='access'):
    """
    Decodifica e valida o token. Retorna o payload se for válido, ou levanta uma exceção apropriada.
    """
    secret = getattr(settings, 'JWT_SECRET_KEY')
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        if payload.get('token_type') != token_type:
            raise jwt.InvalidTokenError("Tipo de token inválido.")
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token expirado.")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Token inválido.")

def jwt_required(view_func):
    """
    Decorador que exige autenticação JWT (Bearer token).
    Retorna 401 Unauthorized em caso de token ausente, inválido ou expirado.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'success': False, 'message': 'Token de acesso ausente ou malformado.'}, status=401)
            
        token = auth_header.split(' ')[1]
        try:
            payload = decode_token(token, 'access')
            user_id = payload.get('user_id')
            if user_id:
                user = User.objects.filter(id=user_id).first()
                if user and user.is_active:
                    request.user = user
                    return view_func(request, *args, **kwargs)
            return JsonResponse({'success': False, 'message': 'Usuário inválido ou inativo.'}, status=401)
        except jwt.ExpiredSignatureError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=401)
            
    return _wrapped_view

def authenticate_jwt(request):
    """
    Tenta autenticar a requisição usando JWT no cabeçalho Authorization.
    Se o token for válido, associa o User a request.user e retorna True.
    Caso contrário, retorna False.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
        
    token = auth_header.split(' ')[1]
    try:
        payload = decode_token(token, 'access')
        user_id = payload.get('user_id')
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if user and user.is_active:
                request.user = user
                return True
    except jwt.InvalidTokenError:
        pass
    return False

def validate_api_key(request):
    """
    Valida se a chave de API fornecida no cabeçalho ou nos parâmetros da URL é válida,
    ou se a requisição está autenticada via JWT ou sessão ativa.
    """
    # 1. Tenta autenticação via JWT
    if authenticate_jwt(request):
        return True

    # 2. Tenta autenticação via Sessão Django (se já estiver logado no navegador)
    if request.user and request.user.is_authenticated:
        return True

    # 3. Tenta autenticação via chave de API (ESP32 tradicional)
    expected_key = getattr(settings, 'ESP32_API_KEY', None)
    if not expected_key:
        return True
    
    api_key = request.headers.get('X-API-Key') or request.GET.get('api_key') or request.POST.get('api_key')
    return api_key == expected_key



# ==========================================
# 1. AUTENTICAÇÃO (Login / Logout)
# ==========================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Bem-vindo(a), {username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Usuário ou senha inválidos.")
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Você saiu com sucesso.")
    return redirect('login')


# ==========================================
# 2. DASHBOARD PRINCIPAL & CONTROLES MANUAIS
# ==========================================

@login_required
def dashboard_view(request):
    vagas = Vaga.objects.all()
    total_vagas = vagas.count()
    vagas_disponiveis = vagas.filter(status='disponivel').count()
    vagas_ocupadas = vagas.filter(status='ocupada').count()
    vagas_bloqueadas = vagas.filter(status='bloqueada').count()
    
    alunos = Aluno.objects.all()
    tags = RFIDTag.objects.all()
    
    recent_logs = RegistroMovimentacao.objects.select_related('aluno', 'vaga').all()[:10]
    
    context = {
        'vagas': vagas,
        'total_vagas': total_vagas,
        'vagas_disponiveis': vagas_disponiveis,
        'vagas_ocupadas': vagas_ocupadas,
        'vagas_bloqueadas': vagas_bloqueadas,
        'recent_logs': recent_logs,
        'total_alunos': alunos.count(),
        'total_tags': tags.count(),
    }
    return render(request, 'core/dashboard.html', context)

# Controles Manuais do Painel (Chamadas AJAX via JS)

@login_required
def api_unlock_remote(request, vaga_id):
    if request.method == 'POST':
        vaga = get_object_or_404(Vaga, id=vaga_id)
        vaga.pending_unlock = True
        vaga.save()
        
        # Log da ação
        aluno = vaga.aluno_atual
        uid = aluno.rfid.uid if (aluno and aluno.rfid) else "N/A"
        RegistroMovimentacao.objects.create(
            aluno=aluno,
            rfid_uid=uid,
            vaga=vaga,
            acao='destravamento_remoto'
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Comando de destravamento enviado para a Vaga #{vaga.numero}."
        })
    return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

@login_required
def api_liberar_vaga(request, vaga_id):
    if request.method == 'POST':
        vaga = get_object_or_404(Vaga, id=vaga_id)
        aluno = vaga.aluno_atual
        uid = aluno.rfid.uid if (aluno and aluno.rfid) else "N/A"
        
        vaga.status = 'disponivel'
        vaga.aluno_atual = None
        vaga.pending_unlock = False
        vaga.save()
        
        RegistroMovimentacao.objects.create(
            aluno=aluno,
            rfid_uid=uid,
            vaga=vaga,
            acao='liberacao_manual'
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Vaga #{vaga.numero} liberada com sucesso."
        })
    return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

@login_required
def api_bloquear_vaga(request, vaga_id):
    if request.method == 'POST':
        vaga = get_object_or_404(Vaga, id=vaga_id)
        # Se houver aluno ocupando, liberamos a vaga antes de bloquear
        aluno = vaga.aluno_atual
        uid = aluno.rfid.uid if (aluno and aluno.rfid) else "N/A"
        
        vaga.status = 'bloqueada'
        vaga.aluno_atual = None
        vaga.pending_unlock = False
        vaga.save()
        
        RegistroMovimentacao.objects.create(
            aluno=aluno,
            rfid_uid=uid,
            vaga=vaga,
            acao='bloqueio'
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Vaga #{vaga.numero} bloqueada com sucesso."
        })
    return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

@login_required
def api_desbloquear_vaga(request, vaga_id):
    if request.method == 'POST':
        vaga = get_object_or_404(Vaga, id=vaga_id)
        vaga.status = 'disponivel'
        vaga.save()
        
        RegistroMovimentacao.objects.create(
            aluno=None,
            rfid_uid="N/A",
            vaga=vaga,
            acao='desbloqueio'
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Vaga #{vaga.numero} desbloqueada com sucesso."
        })
    return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)


# ==========================================
# 3. CRUD ALUNOS
# ==========================================

@login_required
def aluno_list(request):
    alunos = Aluno.objects.select_related('rfid').all().order_by('nome')
    paginator = Paginator(alunos, 10)  # 10 alunos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/alunos_list.html', {'page_obj': page_obj})

@login_required
def aluno_create(request):
    if request.method == 'POST':
        form = AlunoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno cadastrado com sucesso.")
            return redirect('aluno_list')
        else:
            messages.error(request, "Erro ao cadastrar aluno. Verifique os dados.")
    else:
        form = AlunoForm()
    return render(request, 'core/alunos_form.html', {'form': form, 'title': 'Cadastrar Aluno'})

@login_required
def aluno_update(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        form = AlunoForm(request.POST, instance=aluno)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno atualizado com sucesso.")
            return redirect('aluno_list')
        else:
            messages.error(request, "Erro ao atualizar aluno. Verifique os dados.")
    else:
        form = AlunoForm(instance=aluno)
    return render(request, 'core/alunos_form.html', {'form': form, 'title': 'Editar Aluno', 'aluno': aluno})

@login_required
def aluno_delete(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        aluno.delete()
        messages.success(request, "Aluno removido com sucesso.")
        return redirect('aluno_list')
    return render(request, 'core/alunos_confirm_delete.html', {'aluno': aluno})




# ==========================================
# 5. CRUD VAGAS
# ==========================================

@login_required
def vaga_list(request):
    vagas = Vaga.objects.select_related('aluno_atual').all().order_by('numero')
    paginator = Paginator(vagas, 10)  # 10 vagas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/vagas_list.html', {'page_obj': page_obj})

@login_required
def vaga_create(request):
    if request.method == 'POST':
        form = VagaForm(request.POST)
        if form.is_valid():
            vaga = form.save(commit=False)
            # Se a vaga estiver ocupada, ela precisa ter um aluno associado
            if vaga.status == 'ocupada' and not vaga.aluno_atual:
                messages.error(request, "Uma vaga com status 'Ocupada' precisa ter um aluno associado.")
            elif vaga.status in ['disponivel', 'bloqueada'] and vaga.aluno_atual:
                vaga.aluno_atual = None
                vaga.save()
                messages.success(request, "Vaga cadastrada. Aluno desassociado automaticamente pois a vaga não está ocupada.")
                return redirect('vaga_list')
            else:
                vaga.save()
                messages.success(request, "Vaga cadastrada com sucesso.")
                return redirect('vaga_list')
        else:
            messages.error(request, "Erro ao cadastrar vaga. Verifique os dados.")
    else:
        form = VagaForm()
    return render(request, 'core/vagas_form.html', {'form': form, 'title': 'Cadastrar Vaga'})

@login_required
def vaga_update(request, pk):
    vaga = get_object_or_404(Vaga, pk=pk)
    if request.method == 'POST':
        form = VagaForm(request.POST, instance=vaga)
        if form.is_valid():
            vaga = form.save(commit=False)
            if vaga.status == 'ocupada' and not vaga.aluno_atual:
                messages.error(request, "Uma vaga com status 'Ocupada' precisa ter um aluno associado.")
            elif vaga.status in ['disponivel', 'bloqueada'] and vaga.aluno_atual:
                vaga.aluno_atual = None
                vaga.save()
                messages.success(request, "Vaga atualizada. Aluno desassociado automaticamente.")
                return redirect('vaga_list')
            else:
                vaga.save()
                messages.success(request, "Vaga atualizada com sucesso.")
                return redirect('vaga_list')
        else:
            messages.error(request, "Erro ao atualizar vaga.")
    else:
        form = VagaForm(instance=vaga)
    return render(request, 'core/vagas_form.html', {'form': form, 'title': 'Editar Vaga', 'vaga': vaga})

@login_required
def vaga_delete(request, pk):
    vaga = get_object_or_404(Vaga, pk=pk)
    if request.method == 'POST':
        vaga.delete()
        messages.success(request, "Vaga removida com sucesso.")
        return redirect('vaga_list')
    return render(request, 'core/vagas_confirm_delete.html', {'vaga': vaga})


# ==========================================
# 6. HISTÓRICO DE LOGS
# ==========================================

@login_required
def logs_list(request):
    logs_qs = RegistroMovimentacao.objects.select_related('aluno', 'vaga').all()
    # Adicionar busca/filtro opcional
    search_query = request.GET.get('search', '').strip()
    if search_query:
        logs_qs = logs_qs.filter(
            Q(aluno__nome__icontains=search_query) |
            Q(rfid_uid__icontains=search_query) |
            Q(acao__icontains=search_query)
        )
    
    paginator = Paginator(logs_qs, 15)  # 15 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/logs_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


# ==========================================
# 7. TELEMETRIA / DASHBOARD TV
# ==========================================

def tv_dashboard(request):
    return render(request, 'core/tv.html')


# ==========================================
# 8. REST API ENDPOINTS PARA ESP32 (CSRF ISENTO)
# ==========================================
@csrf_exempt
def api_rfid_scan(request):
    """
    POST /api/rfid/scan/
    Payload: {"uid": "A1B2C3D4"}
    """
    if not validate_api_key(request):
        return JsonResponse({'success': False, 'message': 'Não autorizado. Chave de API inválida ou ausente.'}, status=401)

    if request.method not in ['POST', 'GET']:
        return JsonResponse({'success': False, 'message': 'Apenas requisições POST e GET são permitidas.'}, status=405)

    uid = None
    format_type = None
    # 1. Tentar ler do JSON body
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            uid = data.get('uid', '').strip()
            format_type = data.get('format', '').strip()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    
    # 2. Tentar ler do POST form data ou GET query string como fallback
    if not uid:
        raw_uid = request.POST.get('uid') or request.GET.get('uid')
        if raw_uid:
            uid = raw_uid.strip()

    if not format_type:
        raw_format = request.POST.get('format') or request.GET.get('format')
        if raw_format:
            format_type = raw_format.strip()

    is_format_text = (format_type == 'text')

    if not uid:
        return JsonResponse({'success': False, 'message': 'O campo "uid" é obrigatório.'}, status=400)

    # Normalização e busca flexível de tags (com ou sem espaços)
    norm_uid = uid.replace(" ", "").upper()
    tag = RFIDTag.objects.filter(uid=uid).first()
    if not tag:
        for t in RFIDTag.objects.all():
            if t.uid.replace(" ", "").upper() == norm_uid:
                tag = t
                uid = t.uid  # Manter o formato já gravado no DB
                break

    pending_session = RFIDCadastroPendente.objects.filter(status='pending').order_by('-timestamp').first()
    if pending_session:
        aluno = pending_session.aluno
        old_rfid = aluno.rfid

        # Buscar ou criar o novo crachá RFID
        if not tag:
            tag, created = RFIDTag.objects.get_or_create(uid=uid, defaults={'ativo': True})
        else:
            tag.ativo = True
            tag.save()

        # Se a tag estava associada a outro aluno, desassociá-la
        try:
            other_aluno = tag.aluno
            if other_aluno != aluno:
                other_aluno.rfid = None
                other_aluno.save()
        except Aluno.DoesNotExist:
            pass

        # Associar ao aluno atual
        aluno.rfid = tag
        aluno.save()

        # Se havia um crachá antigo associado e for diferente do novo, excluí-lo
        if old_rfid and old_rfid != tag:
            old_rfid.delete()

        # Atualizar a sessão para sucesso
        pending_session.status = 'success'
        pending_session.scanned_uid = uid
        pending_session.save()

        if is_format_text:
            return HttpResponse("2", content_type="text/plain")
        return JsonResponse({'codigo': 2})

    # 1. Validar Tag RFID
    if not tag:
        # Registrar movimentação sem aluno associado para fins de segurança/auditoria
        RegistroMovimentacao.objects.create(
            aluno=None,
            rfid_uid=uid,
            vaga=None,
            acao='entrada'  # Tentativa
        )
        if is_format_text:
            return HttpResponse("3", content_type="text/plain", status=403)
        return JsonResponse({'codigo': 3}, status=403)

    if not tag.ativo:
        if is_format_text:
            return HttpResponse("3", content_type="text/plain", status=403)
        return JsonResponse({'codigo': 3}, status=403)

    # 2. Validar Aluno Associado
    try:
        aluno = tag.aluno
    except Aluno.DoesNotExist:
        if is_format_text:
            return HttpResponse("3", content_type="text/plain", status=403)
        return JsonResponse({'codigo': 3}, status=403)

    # 3. Verificar se o aluno já tem uma bicicleta estacionada (Session ativa)
    vaga_ocupada = Vaga.objects.filter(aluno_atual=aluno, status='ocupada').first()

    if vaga_ocupada:
        # AÇÃO: RETIRADA (SAÍDA)
        vaga_numero = vaga_ocupada.numero
        
        # Liberar a vaga
        vaga_ocupada.status = 'disponivel'
        vaga_ocupada.aluno_atual = None
        vaga_ocupada.pending_unlock = True  # Sinalizar ao hardware para abrir a trava
        vaga_ocupada.save()

        # Registrar Log
        RegistroMovimentacao.objects.create(
            aluno=aluno,
            rfid_uid=uid,
            vaga=vaga_ocupada,
            acao='saida'
        )

        if is_format_text:
            return HttpResponse("1", content_type="text/plain")
        return JsonResponse({'codigo': 1})
    else:
        # AÇÃO: ESTACIONAR (ENTRADA)
        # Procurar primeira vaga disponível
        vaga_disponivel = Vaga.objects.filter(status='disponivel').first()

        if not vaga_disponivel:
            if is_format_text:
                return HttpResponse("3", content_type="text/plain", status=400)
            return JsonResponse({'codigo': 3}, status=400)

        # Ocupar a vaga
        vaga_disponivel.status = 'ocupada'
        vaga_disponivel.aluno_atual = aluno
        vaga_disponivel.pending_unlock = True  # Sinalizar ao hardware para abrir a trava correspondente
        vaga_disponivel.save()

        # Registrar Log
        RegistroMovimentacao.objects.create(
            aluno=aluno,
            rfid_uid=uid,
            vaga=vaga_disponivel,
            acao='entrada'
        )

        if is_format_text:
            return HttpResponse("1", content_type="text/plain")
        return JsonResponse({'codigo': 1})

@csrf_exempt
def api_get_alunos(request):
    """
    GET /api/alunos/
    Retorna a lista de todos os alunos cadastrados para associação no frontend.
    """
    if not validate_api_key(request):
        return JsonResponse({'success': False, 'message': 'Não autorizado. Chave de API ou JWT inválido.'}, status=401)

    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    alunos = Aluno.objects.select_related('rfid').all()
    alunos_data = []

    for aluno in alunos:
        rfid_uid = aluno.rfid.uid if aluno.rfid else None
        alunos_data.append({
            'id': aluno.id,
            'nome': aluno.nome,
            'matricula': aluno.matricula,
            'rfid': rfid_uid
        })

    return JsonResponse(alunos_data, safe=False)

@csrf_exempt
def api_get_vagas(request):
    """
    GET /api/vagas/
    Retorna a lista de todas as vagas.
    Como o ESP32 consome este endpoint, se houver 'pending_unlock=True', 
    capturamos e limpamos a flag para que a abertura física seja processada uma única vez.
    """
    authenticate_jwt(request)  # Opcional: autenticar se houver Bearer token

    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    vagas = Vaga.objects.all()
    vagas_data = []

    for vaga in vagas:
        aluno_nome = vaga.aluno_atual.nome if vaga.aluno_atual else None
        vagas_data.append({
            'id': vaga.id,
            'numero': vaga.numero,
            'status': vaga.status,
            'aluno': aluno_nome,
            'pending_unlock': vaga.pending_unlock
        })
        
        # Limpar o estado de pending_unlock para que o hardware processe apenas uma vez
        if vaga.pending_unlock:
            vaga.pending_unlock = False
            vaga.save()

    return JsonResponse(vagas_data, safe=False)

@csrf_exempt
def api_esp_status(request):
    """
    GET /api/esp/status/
    Endpoint para que a ESP32 verifique o status do sistema e se há comandos pendentes:
    - Retorna 2 (ou {'codigo': 2}) se houver cadastro pendente.
    - Retorna 1 (ou {'codigo': 1}) se houver destravamento pendente em alguma vaga (e limpa a flag pending_unlock).
    - Retorna 0 (ou {'codigo': 0}) caso contrário.
    """
    if not validate_api_key(request):
        return JsonResponse({'success': False, 'message': 'Não autorizado. Chave de API inválida ou ausente.'}, status=401)

    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Apenas requisições GET são permitidas.'}, status=405)

    is_format_text = request.GET.get('format') == 'text'

    # 1. Verificar se há cadastro pendente
    pending_session = RFIDCadastroPendente.objects.filter(status='pending').exists()
    if pending_session:
        if is_format_text:
            return HttpResponse("2", content_type="text/plain")
        return JsonResponse({'codigo': 2, 'mensagem': 'Modo cadastro ativo'})

    # 2. Verificar se há vaga com destravamento pendente
    vaga_pendente = Vaga.objects.filter(pending_unlock=True).first()
    if vaga_pendente:
        vaga_numero = vaga_pendente.numero
        # Limpar o status de pending_unlock para que o hardware processe apenas uma vez
        vaga_pendente.pending_unlock = False
        vaga_pendente.save()
        
        if is_format_text:
            return HttpResponse("1", content_type="text/plain")
        return JsonResponse({'codigo': 1, 'mensagem': 'Destravamento pendente', 'vaga': vaga_numero})

    # 3. Caso contrário
    if is_format_text:
        return HttpResponse("0", content_type="text/plain")
    return JsonResponse({'codigo': 0, 'mensagem': 'Sem comandos pendentes'})


@csrf_exempt
def api_liberar_vaga_post(request):
    """
    POST /api/vagas/liberar/
    Payload: {"vaga_id": X} ou {"numero": X}
    """
    if not validate_api_key(request):
        return JsonResponse({'success': False, 'message': 'Não autorizado. Chave de API inválida ou ausente.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    try:
        data = json.loads(request.body)
        vaga_id = data.get('vaga_id')
        numero = data.get('numero')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)

    if vaga_id:
        vaga = get_object_or_404(Vaga, id=vaga_id)
    elif numero:
        vaga = get_object_or_404(Vaga, numero=numero)
    else:
        return JsonResponse({'success': False, 'message': 'É necessário enviar "vaga_id" ou "numero".'}, status=400)

    aluno = vaga.aluno_atual
    uid = aluno.rfid.uid if (aluno and aluno.rfid) else "N/A"
    
    vaga.status = 'disponivel'
    vaga.aluno_atual = None
    vaga.pending_unlock = False
    vaga.save()

    RegistroMovimentacao.objects.create(
        aluno=aluno,
        rfid_uid=uid,
        vaga=vaga,
        acao='liberacao_manual'
    )

    return JsonResponse({'success': True, 'message': f'Vaga #{vaga.numero} liberada via API.'})

@csrf_exempt
def api_bloquear_vaga_post(request):
    """
    POST /api/vagas/bloquear/
    Payload: {"vaga_id": X} ou {"numero": X}
    """
    if not validate_api_key(request):
        return JsonResponse({'success': False, 'message': 'Não autorizado. Chave de API inválida ou ausente.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    try:
        data = json.loads(request.body)
        vaga_id = data.get('vaga_id')
        numero = data.get('numero')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)

    if vaga_id:
        vaga = get_object_or_404(Vaga, id=vaga_id)
    elif numero:
        vaga = get_object_or_404(Vaga, numero=numero)
    else:
        return JsonResponse({'success': False, 'message': 'É necessário enviar "vaga_id" ou "numero".'}, status=400)

    aluno = vaga.aluno_atual
    uid = aluno.rfid.uid if (aluno and aluno.rfid) else "N/A"

    vaga.status = 'bloqueada'
    vaga.aluno_atual = None
    vaga.pending_unlock = False
    vaga.save()

    RegistroMovimentacao.objects.create(
        aluno=aluno,
        rfid_uid=uid,
        vaga=vaga,
        acao='bloqueio'
    )

    return JsonResponse({'success': True, 'message': f'Vaga #{vaga.numero} bloqueada via API.'})

# ==========================================
# 9. ENDPOINTS DE CADASTRO RFID VIA LEITOR
# ==========================================

@login_required
@csrf_exempt
def api_rfid_register_start(request, aluno_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)
        
    aluno = get_object_or_404(Aluno, id=aluno_id)
    
    # Limpar qualquer outra sessão pendente para evitar inconsistências
    RFIDCadastroPendente.objects.all().delete()
    
    # Criar nova sessão
    RFIDCadastroPendente.objects.create(aluno=aluno, status='pending')
    
    return JsonResponse({
        'success': True,
        'message': f'Aguardando aproximação do crachá para o aluno {aluno.nome}.'
    })

@login_required
def api_rfid_register_status(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    session = RFIDCadastroPendente.objects.filter(aluno=aluno).first()
    
    if not session:
        return JsonResponse({'status': 'not_found'})
        
    if session.status == 'success':
        uid = session.scanned_uid
        # Excluir a sessão após ler o sucesso
        session.delete()
        return JsonResponse({'status': 'success', 'uid': uid})
        
    elif session.status == 'failed':
        session.delete()
        return JsonResponse({'status': 'failed'})
        
    return JsonResponse({'status': 'pending'})

@login_required
@csrf_exempt
def api_rfid_register_cancel(request, aluno_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)
        
    aluno = get_object_or_404(Aluno, id=aluno_id)
    # Deletar sessão pendente para o aluno
    RFIDCadastroPendente.objects.filter(aluno=aluno).delete()
    
    return JsonResponse({'success': True, 'message': 'Operação cancelada.'})


# ==========================================
# 10. CRUD AVISOS & API DE AVISOS
# ==========================================

@login_required
def aviso_list(request):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'update_interval':
        try:
            tempo = int(request.POST.get('tempo_exibicao', 6))
            if tempo < 1:
                tempo = 6
        except (ValueError, TypeError):
            tempo = 6
        
        config, created = Configuracao.objects.get_or_create(
            chave='tempo_exibicao_avisos',
            defaults={'valor': str(tempo)}
        )
        if not created:
            config.valor = str(tempo)
            config.save()
            
        messages.success(request, f"Intervalo de transição dos avisos atualizado para {tempo} segundos.")
        return redirect('aviso_list')

    # Obter o tempo de exibição atual ou usar o padrão de 6 segundos
    config_tempo = Configuracao.objects.filter(chave='tempo_exibicao_avisos').first()
    tempo_exibicao = int(config_tempo.valor) if config_tempo else 6

    avisos = Aviso.objects.all().order_by('-timestamp')
    paginator = Paginator(avisos, 10)  # 10 avisos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'tempo_exibicao': tempo_exibicao
    }
    return render(request, 'core/aviso_list.html', context)

@login_required
def aviso_create(request):
    if request.method == 'POST':
        form = AvisoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Aviso cadastrado com sucesso.")
            return redirect('aviso_list')
        else:
            messages.error(request, "Erro ao cadastrar aviso. Verifique os dados.")
    else:
        form = AvisoForm()
    return render(request, 'core/aviso_form.html', {'form': form, 'title': 'Cadastrar Aviso'})

@login_required
def aviso_update(request, pk):
    aviso = get_object_or_404(Aviso, pk=pk)
    if request.method == 'POST':
        form = AvisoForm(request.POST, request.FILES, instance=aviso)
        if form.is_valid():
            form.save()
            messages.success(request, "Aviso atualizado com sucesso.")
            return redirect('aviso_list')
        else:
            messages.error(request, "Erro ao atualizar aviso.")
    else:
        form = AvisoForm(instance=aviso)
    return render(request, 'core/aviso_form.html', {'form': form, 'title': 'Editar Aviso', 'aviso': aviso})

@login_required
def aviso_delete(request, pk):
    aviso = get_object_or_404(Aviso, pk=pk)
    if request.method == 'POST':
        aviso.delete()
        messages.success(request, "Aviso removido com sucesso.")
        return redirect('aviso_list')
    return render(request, 'core/aviso_confirm_delete.html', {'aviso': aviso})

@csrf_exempt
def api_get_avisos(request):
    """
    GET /api/avisos/
    Retorna a lista de todos os avisos ativos e não expirados para o painel da TV,
    junto com o tempo de exibição configurado.
    """
    authenticate_jwt(request)  # Opcional: autenticar se houver Bearer token

    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    agora = timezone.now()
    avisos = Aviso.objects.filter(
        Q(ativo=True) &
        (Q(data_expiracao__isnull=True) | Q(data_expiracao__gt=agora))
    )
    
    config_tempo = Configuracao.objects.filter(chave='tempo_exibicao_avisos').first()
    tempo_exibicao = int(config_tempo.valor) if config_tempo else 6

    avisos_data = []
    for aviso in avisos:
        foto_url = None
        if aviso.foto:
            foto_url = request.build_absolute_uri(aviso.foto.url)
            
        avisos_data.append({
            'id': aviso.id,
            'titulo': aviso.titulo,
            'texto': aviso.texto,
            'link': aviso.link,
            'foto': foto_url,
            'foto_fit': aviso.foto_fit,
            'data_expiracao': aviso.data_expiracao.isoformat() if aviso.data_expiracao else None
        })
    
    response_data = {
        'tempo_exibicao': tempo_exibicao,
        'avisos': avisos_data
    }
    return JsonResponse(response_data)

@csrf_exempt
def api_token_obtain(request):
    """
    POST /api/token/
    Recebe username e password, autentica e retorna access e refresh tokens JWT.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido. Utilize POST.'}, status=405)
        
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'JSON inválido no corpo da requisição.'}, status=400)
        
    if not username or not password:
        return JsonResponse({'success': False, 'message': 'Os campos "username" e "password" são obrigatórios.'}, status=400)
        
    user = authenticate(username=username, password=password)
    if user is not None:
        if not user.is_active:
            return JsonResponse({'success': False, 'message': 'Este usuário está inativo.'}, status=403)
            
        access_token, refresh_token = generate_tokens(user)
        return JsonResponse({
            'success': True,
            'access': access_token,
            'refresh': refresh_token
        })
    else:
        return JsonResponse({'success': False, 'message': 'Credenciais de acesso inválidas.'}, status=401)

@csrf_exempt
def api_token_refresh(request):
    """
    POST /api/token/refresh/
    Recebe um refresh token e gera um novo access token e refresh token.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido. Utilize POST.'}, status=405)
        
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'JSON inválido no corpo da requisição.'}, status=400)
        
    if not refresh_token:
        return JsonResponse({'success': False, 'message': 'O campo "refresh" é obrigatório.'}, status=400)
        
    try:
        payload = decode_token(refresh_token, 'refresh')
        user_id = payload.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'Token de atualização inválido.'}, status=401)
            
        user = User.objects.filter(id=user_id).first()
        if not user or not user.is_active:
            return JsonResponse({'success': False, 'message': 'Usuário inativo ou inexistente.'}, status=401)
            
        access_token, new_refresh_token = generate_tokens(user)
        return JsonResponse({
            'success': True,
            'access': access_token,
            'refresh': new_refresh_token
        })
    except jwt.ExpiredSignatureError as e:
        return JsonResponse({'success': False, 'message': f'Token expirado: {str(e)}'}, status=401)
    except jwt.InvalidTokenError as e:
        return JsonResponse({'success': False, 'message': f'Token inválido: {str(e)}'}, status=401)


