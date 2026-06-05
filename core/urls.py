from django.urls import path
from . import views

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Telemetria TV
    path('tv/', views.tv_dashboard, name='tv_dashboard'),
    
    # Controles Manuais (AJAX)
    path('vagas/<int:vaga_id>/destravar/', views.api_unlock_remote, name='vaga_destravar'),
    path('vagas/<int:vaga_id>/liberar/', views.api_liberar_vaga, name='vaga_liberar'),
    path('vagas/<int:vaga_id>/bloquear/', views.api_bloquear_vaga, name='vaga_bloquear'),
    path('vagas/<int:vaga_id>/desbloquear/', views.api_desbloquear_vaga, name='vaga_desbloquear'),
    
    # CRUD Alunos
    path('alunos/', views.aluno_list, name='aluno_list'),
    path('alunos/novo/', views.aluno_create, name='aluno_create'),
    path('alunos/<int:pk>/editar/', views.aluno_update, name='aluno_update'),
    path('alunos/<int:pk>/deletar/', views.aluno_delete, name='aluno_delete'),
    
    # Cadastro de RFID via Leitor (AJAX)
    path('alunos/<int:aluno_id>/rfid-register-start/', views.api_rfid_register_start, name='api_rfid_register_start'),
    path('alunos/<int:aluno_id>/rfid-register-status/', views.api_rfid_register_status, name='api_rfid_register_status'),
    path('alunos/<int:aluno_id>/rfid-register-cancel/', views.api_rfid_register_cancel, name='api_rfid_register_cancel'),
    

    # CRUD Vagas
    path('vagas/', views.vaga_list, name='vaga_list'),
    path('vagas/nova/', views.vaga_create, name='vaga_create'),
    path('vagas/<int:pk>/editar/', views.vaga_update, name='vaga_update'),
    path('vagas/<int:pk>/deletar/', views.vaga_delete, name='vaga_delete'),
    
    # Histórico de Logs
    path('logs/', views.logs_list, name='logs_list'),
    
    # JWT Authentication Endpoints
    path('api/token/', views.api_token_obtain, name='api_token_obtain'),
    path('api/token/refresh/', views.api_token_refresh, name='api_token_refresh'),

    # ESP32 REST APIs (Csrf Exempt)
    path('api/alunos/', views.api_get_alunos, name='api_get_alunos'),
    path('api/rfid/scan/', views.api_rfid_scan, name='api_rfid_scan'),
    path('api/rfid/scan', views.api_rfid_scan),
    path('api/vagas/', views.api_get_vagas, name='api_get_vagas'),
    path('api/esp/status/', views.api_esp_status, name='api_esp_status'),
    path('api/esp/status', views.api_esp_status),
    path('api/vagas/liberar/', views.api_liberar_vaga_post, name='api_liberar_vaga_post'),
    path('api/vagas/bloquear/', views.api_bloquear_vaga_post, name='api_bloquear_vaga_post'),
    
    # CRUD Avisos & API
    path('avisos/', views.aviso_list, name='aviso_list'),
    path('avisos/novo/', views.aviso_create, name='aviso_create'),
    path('avisos/<int:pk>/editar/', views.aviso_update, name='aviso_update'),
    path('avisos/<int:pk>/deletar/', views.aviso_delete, name='aviso_delete'),
    path('api/avisos/', views.api_get_avisos, name='api_get_avisos'),
]
