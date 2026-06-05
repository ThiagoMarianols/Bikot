// Helper to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fade out alerts automatically after 4 seconds
document.addEventListener("DOMContentLoaded", function() {
    const alerts = document.querySelectorAll('.alert-float-container .alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = "opacity 0.6s ease";
            alert.style.opacity = "0";
            setTimeout(function() {
                alert.remove();
            }, 600);
        }, 4000);
    });
});

// AJAX Control Calls for Dashboard Vagas
function controleVaga(url, actionType) {
    const csrftoken = getCookie('csrftoken');
    
    // Mostra um spinner ou altera o estado do botão para indicar processamento
    Swal.fire({
        title: 'Processando...',
        html: 'Enviando comando para o servidor...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Sucesso',
                text: data.message,
                timer: 2000,
                showConfirmButton: false
            }).then(() => {
                // Recarrega a página para atualizar o status das vagas e logs
                window.location.reload();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: data.message || 'Ocorreu um erro ao executar a ação.'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro de Rede',
            text: 'Não foi possível conectar com o servidor.'
        });
    });
}

// AJAX Call to start RFID registration via reader
function iniciarCadastroRFID(alunoId, alunoNome) {
    const csrftoken = getCookie('csrftoken');
    
    // Iniciar a sessão de cadastro no servidor
    fetch(`/alunos/${alunoId}/rfid-register-start/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: data.message || 'Não foi possível iniciar o cadastro.'
            });
            return;
        }

        let pollInterval;
        let elapsedSeconds = 0;
        const timeoutSeconds = 60;
        
        Swal.fire({
            title: 'Aproxime o Crachá',
            html: `
                <div class="text-center my-4">
                    <div class="rfid-pulsar-container mb-4">
                        <i class="fa-solid fa-nfc-directional text-primary" style="font-size: 3.5rem; animation: pulse 1.5s infinite; display: inline-block;"></i>
                    </div>
                    <p class="mb-1 text-muted">Aguardando leitura do crachá para <strong>${alunoNome}</strong>...</p>
                    <small class="text-muted d-block mt-2">Encoste o crachá do aluno no leitor físico.</small>
                    <div class="mt-3 text-secondary" id="rfid-timer" style="font-size: 0.85rem;">Tempo restante: 60s</div>
                    <button type="button" id="btn-manual-uid" class="btn btn-sm btn-outline-secondary mt-4 py-1 px-3 d-flex align-items-center gap-1 mx-auto" style="font-size: 0.8rem;">
                        <i class="fa-solid fa-keyboard text-muted"></i> Digitar UID manualmente
                    </button>
                </div>
                <style>
                    @keyframes pulse {
                        0% { transform: scale(1); opacity: 0.6; text-shadow: 0 0 0 rgba(79, 70, 229, 0); }
                        50% { transform: scale(1.1); opacity: 1; text-shadow: 0 0 15px rgba(79, 70, 229, 0.5); }
                        100% { transform: scale(1); opacity: 0.6; text-shadow: 0 0 0 rgba(79, 70, 229, 0); }
                    }
                </style>
            `,
            showCancelButton: true,
            cancelButtonText: 'Cancelar',
            allowOutsideClick: false,
            allowEscapeKey: false,
            didOpen: () => {
                // Ocultar o botão "Confirmar" padrão
                const confirmBtn = Swal.getConfirmButton();
                if (confirmBtn) confirmBtn.style.display = 'none';

                // Listener para digitar manualmente
                const manualBtn = document.getElementById('btn-manual-uid');
                if (manualBtn) {
                    manualBtn.addEventListener('click', () => {
                        clearInterval(pollInterval);
                        
                        Swal.fire({
                            title: 'Digitar UID do Crachá',
                            input: 'text',
                            inputLabel: `UID do Crachá para ${alunoNome}`,
                            inputPlaceholder: 'Ex: A1B2C3D4',
                            showCancelButton: true,
                            confirmButtonText: 'Vincular',
                            cancelButtonText: 'Voltar',
                            confirmButtonColor: '#4f46e5',
                            cancelButtonColor: '#6c757d',
                            inputValidator: (value) => {
                                if (!value || !value.trim()) {
                                    return 'Você precisa digitar um UID!';
                                }
                            },
                            showLoaderOnConfirm: true,
                            preConfirm: (uid) => {
                                return fetch('/api/rfid/scan/', {
                                    method: 'POST',
                                    headers: {
                                        'X-CSRFToken': csrftoken,
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({ uid: uid.trim() })
                                })
                                .then(response => {
                                    if (!response.ok) {
                                        throw new Error('Erro ao registrar crachá.');
                                    }
                                    return response.json();
                                })
                                .catch(error => {
                                    Swal.showValidationMessage(`Erro: ${error.message}`);
                                });
                            },
                            allowOutsideClick: () => !Swal.isLoading()
                        }).then((result) => {
                            if (result.isConfirmed && result.value && (result.value.success || result.value.codigo === 2)) {
                                Swal.fire({
                                    icon: 'success',
                                    title: 'Crachá Cadastrado!',
                                    text: `O crachá foi associado com sucesso a ${alunoNome}.`,
                                    timer: 3000,
                                    confirmButtonColor: '#4f46e5',
                                    confirmButtonText: 'Ok'
                                }).then(() => {
                                    window.location.reload();
                                });
                            } else {
                                // Se cancelado ou falhado, reabrir a tela de aproximação
                                iniciarCadastroRFID(alunoId, alunoNome);
                            }
                        });
                    });
                }
                
                // Iniciar polling
                pollInterval = setInterval(() => {
                    elapsedSeconds += 1.5;
                    const timeLeft = Math.max(0, Math.round(timeoutSeconds - elapsedSeconds));
                    const timerEl = document.getElementById('rfid-timer');
                    if (timerEl) {
                        timerEl.textContent = `Tempo restante: ${timeLeft}s`;
                    }

                    if (elapsedSeconds >= timeoutSeconds) {
                        clearInterval(pollInterval);
                        Swal.fire({
                            icon: 'warning',
                            title: 'Tempo Esgotado',
                            text: 'Nenhum crachá foi aproximado do leitor no tempo limite.',
                            confirmButtonColor: '#4f46e5'
                        });
                        return;
                    }

                    fetch(`/alunos/${alunoId}/rfid-register-status/`)
                    .then(res => res.json())
                    .then(statusData => {
                        if (statusData.status === 'success') {
                            clearInterval(pollInterval);
                            Swal.fire({
                                icon: 'success',
                                title: 'Crachá Cadastrado!',
                                text: `O crachá com UID ${statusData.uid} foi associado com sucesso a ${alunoNome}.`,
                                timer: 3000,
                                showConfirmButton: true,
                                confirmButtonColor: '#4f46e5',
                                confirmButtonText: 'Ok'
                            }).then(() => {
                                window.location.reload();
                            });
                        } else if (statusData.status === 'failed') {
                            clearInterval(pollInterval);
                            Swal.fire({
                                icon: 'error',
                                title: 'Erro no Cadastro',
                                text: 'Ocorreu um erro ao processar o cadastro do crachá.',
                                confirmButtonColor: '#4f46e5'
                            });
                        }
                    })
                    .catch(err => console.error('Erro no polling:', err));
                }, 1500);
            },
            willClose: () => {
                clearInterval(pollInterval);
                // Informar ao backend que a operação foi cancelada ou encerrada
                fetch(`/alunos/${alunoId}/rfid-register-cancel/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json'
                    }
                });
            }
        });
    })
    .catch(error => {
        console.error('Erro:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro de Conexão',
            text: 'Não foi possível conectar ao servidor.'
        });
    });
}

// AJAX Call to fetch students and select one for RFID registration
function selecionarAlunoParaCadastro() {
    Swal.fire({
        title: 'Carregando Alunos...',
        html: 'Buscando lista de alunos no servidor...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch('/api/alunos/')
    .then(response => response.json())
    .then(alunos => {
        if (!alunos || alunos.length === 0) {
            Swal.fire({
                icon: 'warning',
                title: 'Nenhum Aluno',
                text: 'Não há alunos cadastrados no sistema no momento.',
                confirmButtonColor: '#4f46e5'
            });
            return;
        }

        // Criar as opções de alunos
        let optionsHtml = '<option value="" disabled selected>Selecione um aluno...</option>';
        alunos.forEach(aluno => {
            const hasRfidText = aluno.rfid ? ' [Substituir crachá]' : '';
            optionsHtml += `<option value="${aluno.id}">${aluno.nome} (${aluno.matricula})${hasRfidText}</option>`;
        });

        Swal.fire({
            title: 'Vincular Crachá a Aluno',
            html: `
                <div class="text-start my-3">
                    <label for="select-aluno-cadastro" class="form-label text-muted fw-semibold mb-2">Aluno Destinatário:</label>
                    <select id="select-aluno-cadastro" class="form-select">
                        ${optionsHtml}
                    </select>
                    <small class="text-muted d-block mt-2">Selecione o aluno que receberá a nova tag RFID aproximada do leitor.</small>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Avançar <i class="fa-solid fa-arrow-right ms-1"></i>',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#4f46e5',
            cancelButtonColor: '#6c757d',
            allowOutsideClick: false,
            preConfirm: () => {
                const selectEl = document.getElementById('select-aluno-cadastro');
                if (!selectEl || !selectEl.value) {
                    Swal.showValidationMessage('Por favor, selecione um aluno.');
                    return false;
                }
                const selectedOption = selectEl.options[selectEl.selectedIndex];
                let rawNome = selectedOption.text.split(' (')[0];
                return {
                    id: selectEl.value,
                    nome: rawNome
                };
            }
        }).then(result => {
            if (result.isConfirmed) {
                // Chamar a tela de espera de RFID com o aluno selecionado
                iniciarCadastroRFID(result.value.id, result.value.nome);
            }
        });
    })
    .catch(error => {
        console.error('Erro ao buscar alunos:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro de Conexão',
            text: 'Não foi possível buscar a lista de alunos do servidor.'
        });
    });
}


