# BikoT — Backend Django · Gerenciamento e Nuvem do Bicicletário Inteligente

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0.5-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Swarm-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%2B%20Aurora%20RDS-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> **Projeto Integrador — Foco em IoT**  
> CST em Análise e Desenvolvimento de Sistemas — 4º Período | Faculdade Senac PE | Prof. Arnott  
> Este repositório contém o **backend Django e a infraestrutura de nuvem**. Para o firmware ESP32, acesse → [github.com/felipereis13/Project-BikoT](https://github.com/felipereis13/Project-BikoT)

---

## 🔗 Links de Acesso

| Recurso | Link |
|---|---|
| 📦 Este repositório (Backend) | [github.com/ThiagoMarianols/Bikot](https://github.com/ThiagoMarianols/Bikot) |
| 📦 Repositório Firmware (ESP32) | [github.com/felipereis13/Project-BikoT](https://github.com/felipereis13/Project-BikoT) |
| 🌐 Aplicação no ar (Dashboard) | IP fornecido ao vivo na apresentação — instância AWS com IP dinâmico |
| 🎞️ Apresentação (Slides) | [canva.link/95tnmyahvu62uhs](https://canva.link/95tnmyahvu62uhs) |
| 🎥 Demonstração | Ao vivo no auditório (conforme opção prevista nas diretrizes) |
| 🔬 Simulação Wokwi | [wokwi.com/projects/462387775512093697](https://wokwi.com/projects/462387775512093697) |

---

## 📋 Identificação

| Campo | Informação |
|---|---|
| **Projeto** | BikoT — Bicicletário Inteligente com RFID |
| **Repositório** | Backend Django + Infraestrutura Cloud (este) |
| **Equipe** | Claudio Eduardo · Daniela Lopes · Felipe Reis · João Brayner · José Tacyto · Thiago Mariano |
| **Turma / Período** | 4º Período — CST ADS — Faculdade Senac PE |
| **UCs evidenciadas** | Cloud Computing · Engenharia de Software & APIs · Segurança da Informação & LGPD · Comportamento do Consumidor · Inglês |

---

## Abstract (English)

This repository contains the cloud backend for the BikoT smart bicycle parking system. Built with Django 6 and Python 3.12, the backend exposes a REST API consumed by an ESP32 microcontroller and a web administration dashboard for the institution's staff.

The application is deployed in a Docker Swarm cluster on an AWS EC2 instance, managed through Portainer. The database is AWS Aurora RDS with the PostgreSQL engine — a fully managed, high-availability relational service with automatic backups and failover. Infrastructure observability is provided by a monitoring stack composed of Prometheus, Grafana, cAdvisor, and Node Exporter, enabling real-time visibility into container and host-level metrics.

Authentication is multi-layered: JWT tokens (60-minute access, 7-day refresh) protect the web interface, while an `X-API-Key` header authenticates the physical ESP32 device on every request. A public TV dashboard polls the API every 2 seconds to display real-time parking space availability. All credentials are loaded exclusively from environment variables — never hardcoded — and the system follows LGPD data minimization principles.

---

## 1. Sobre Este Repositório

Este repositório é a **camada de nuvem e aplicação** do ecossistema BikoT. Contém:

- **API REST** consumida pelo ESP32 para validação de acesso RFID
- **Dashboard Administrativo** para cadastro de alunos, vagas e controle remoto
- **Dashboard TV** com disponibilidade de vagas em tempo real
- **Banco de dados** (Aurora RDS) com histórico completo de acessos
- **Infraestrutura containerizada** na AWS com monitoramento

O firmware do ESP32 (leitor RFID, servo motor, LEDs, buzzer) está no repositório [felipereis13/Project-BikoT](https://github.com/felipereis13/Project-BikoT).

---

## 2. Requisitos do MVP — Backend e Cloud

### Requisitos Funcionais

| ID | Requisito |
|---|---|
| RF01 | O backend deve receber UIDs RFID do ESP32 e retornar código de acesso (1/2/3) |
| RF02 | O administrador deve poder cadastrar e remover alunos e cartões RFID via painel web |
| RF03 | O sistema deve registrar log de todos os eventos com timestamp, aluno, vaga e ação |
| RF04 | O painel TV deve exibir vagas disponíveis atualizadas a cada 2 segundos |
| RF05 | O administrador deve poder travar, destravar e liberar vagas remotamente |
| RF06 | O sistema deve suportar fluxo de cadastro de novo cartão RFID via interface web + ESP32 |
| RF07 | O painel TV deve exibir avisos com texto, imagem e QR code gerado dinamicamente |

### Requisitos Não Funcionais

| ID | Requisito | Métrica |
|---|---|---|
| RNF01 | Tempo de resposta da API para ESP32 | ≤ 5 segundos |
| RNF02 | Atualização do Dashboard TV | A cada 2 segundos (polling HTTP) |
| RNF03 | Credenciais | Nunca hardcoded — carregadas de variáveis de ambiente |
| RNF04 | Portabilidade | Deploy containerizado com Docker |
| RNF05 | Disponibilidade do banco | AWS Aurora RDS com failover automático |
| RNF06 | Observabilidade | Métricas de containers e host via Prometheus/Grafana |
| RNF07 | Deploy automatizado | GitHub Actions → GHCR → Swarm |

---

## 3. Mapeamento de UCs — Backend

| Conceito Mobilizado | UC | Onde está evidenciado |
|---|---|---|
| Backend Django em Docker Swarm na AWS EC2, Aurora RDS (engine PostgreSQL) como banco gerenciado, Portainer para orquestração, GitHub Actions CI/CD, stack Prometheus/Grafana/cAdvisor/Node Exporter | **Cloud Computing** | `Dockerfile`, `docker-compose.yml`, `.github/workflows/docker-publish.yml`, seção 8 |
| API RESTful HTTP com endpoints estruturados, payload JSON, autenticação em camadas (JWT, Session, X-API-Key), CSRF, contratos request/response documentados | **Engenharia de Software & APIs** | `core/views.py`, `core/urls.py`, seção 6 |
| Credenciais em `.env` (nunca no código), JWT para web, X-API-Key para ESP32, CSRF ativo, HTTPS em produção, minimização de dados LGPD | **Segurança da Informação & LGPD** | `bikot/settings.py`, seção 9 |
| Persona mapeada (estudante ciclista), Dashboard TV para consulta pública de vagas, jornada do usuário, modelos `Vaga` e `RegistroMovimentacao` respondem à dor identificada | **Comportamento do Consumidor** | `core/templates/core/tv.html`, seção 5 (modelos) |
| Abstract em inglês, nomes de modelos e funções consistentes, documentação técnica bilíngue | **Inglês** | Abstract deste README, `core/models.py` |

---

## 4. Arquitetura — Camada de Nuvem

```
┌───────────────────────────────────────────────────────────────┐
│                      AWS EC2 (instância)                       │
│                                                               │
│  ┌─ Docker Swarm ────────────────────────────────────────┐   │
│  │                                                        │   │
│  │  ┌──────────────┐   ┌──────────────────────────────┐  │   │
│  │  │  Portainer   │   │  BikoT — Django + Gunicorn   │  │   │
│  │  │  (UI gestão) │   │  porta 8000                  │  │   │
│  │  └──────────────┘   └──────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐   │   │
│  │  │           Stack de Monitoramento               │   │   │
│  │  │  cAdvisor ──┐                                  │   │   │
│  │  │             ├──► Prometheus ──► Grafana         │   │   │
│  │  │  Node Exporter ─┘                              │   │   │
│  │  └────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────┘   │
│                            │                                  │
└────────────────────────────┼──────────────────────────────────┘
                             │ conexão gerenciada pela AWS
┌────────────────────────────▼──────────────────────────────────┐
│               AWS Aurora RDS — engine PostgreSQL               │
│   Alta disponibilidade · Failover automático                  │
│   Backups diários automáticos · Gerenciado pela AWS           │
└───────────────────────────────────────────────────────────────┘

Entrada externa:
  ESP32 ──► POST /api/rfid/scan/ (X-API-Key) ──► Django Views
  Admin ──► Dashboard Web (JWT / Session)    ──► Django Views
  TV    ──► GET /api/vagas/ (polling 2s)     ──► Django Views

CI/CD:
  GitHub Actions ──► build Docker ──► push GHCR ──► deploy Swarm
```

---

## 5. Modelos de Dados

| Modelo | Campos principais | Relações |
|---|---|---|
| `RFIDTag` | `uid` (único), `ativo` | 1:1 com `Aluno` |
| `Aluno` | `nome`, `matricula` (único), `email`, `rfid` | 1:1 com `RFIDTag` |
| `Vaga` | `numero` (único), `status`, `aluno_atual`, `pending_unlock` | FK → `Aluno` |
| `RegistroMovimentacao` | `aluno`, `rfid_uid`, `vaga`, `acao`, `timestamp` | FK → `Aluno` + `Vaga` |
| `RFIDCadastroPendente` | `aluno`, `status`, `scanned_uid`, `timestamp` | 1:1 com `Aluno` |
| `Aviso` | `titulo`, `texto`, `link`, `foto`, `data_expiracao`, `ativo` | — |
| `Configuracao` | `chave` (único), `valor` | — |

**Status possíveis de `Vaga`:** `disponivel` · `ocupada` · `bloqueada`

**Ações registradas em `RegistroMovimentacao`:**  
`entrada` · `saida` · `liberacao_manual` · `bloqueio` · `desbloqueio` · `destravamento_remoto`

---

## 6. Endpoints REST

| Método | Endpoint | Descrição | Autenticação |
|---|---|---|---|
| `POST` | `/api/rfid/scan/` | Valida UID RFID → retorna código 1, 2 ou 3 | X-API-Key |
| `GET` | `/api/esp/status/` | Polling de comandos pendentes para o ESP32 | X-API-Key |
| `GET` | `/api/vagas/` | Lista vagas com status e `pending_unlock` | JWT / API Key |
| `GET` | `/api/alunos/` | Lista alunos cadastrados | JWT / API Key |
| `GET` | `/api/avisos/` | Avisos ativos para o Dashboard TV | Público |
| `POST` | `/api/vagas/liberar/` | Libera vaga manualmente | JWT |
| `POST` | `/api/vagas/bloquear/` | Bloqueia vaga manualmente | JWT |
| `POST` | `/api/token/` | Gera par de tokens JWT | Credenciais |
| `POST` | `/api/token/refresh/` | Renova token de acesso | Refresh Token |

**Payload RFID (ESP32 → Backend):**
```json
POST /api/rfid/scan/
Content-Type: application/json
X-API-Key: <chave>

{"uid": "01 02 03 04"}
```

**Resposta:**
```json
{"codigo": 1}
```
`1` = acesso liberado · `2` = cartão cadastrado · `3` = acesso negado

**Fluxo de cadastro RFID via web:**
```
POST /alunos/{id}/rfid-register-start/    → inicia sessão de leitura no ESP32
GET  /alunos/{id}/rfid-register-status/   → aguarda o ESP32 aproximar cartão
POST /alunos/{id}/rfid-register-cancel/   → cancela sessão
```

---

## 7. Autenticação

| Camada | Usado por | Implementação |
|---|---|---|
| **JWT Bearer Token** | Interface web | `Authorization: Bearer <token>` — acesso 60 min, refresh 7 dias |
| **Django Session** | Navegador após login | Cookie de sessão gerenciado pelo Django |
| **X-API-Key** | ESP32 e integrações | Header `X-API-Key` ou query param `?api_key=` |

**Prioridade de validação:** JWT → Session → API Key  
**CSRF:** Ativo nas views HTML; exempt nos endpoints REST

---

## 8. Infraestrutura de Produção

### Componentes

**AWS EC2**  
Instância de computação que hospeda o Docker Swarm. O IP é dinâmico — atribuído a cada inicialização da instância. O endereço de acesso é compartilhado com a equipe e informado na apresentação presencial.

**AWS Aurora RDS — engine PostgreSQL**  
Banco de dados relacional totalmente gerenciado pela AWS. Oferece failover automático, backups diários automáticos e escalabilidade sem necessidade de gerenciar o servidor de banco de dados diretamente. A aplicação Django conecta via variável `DB_HOST` no `.env`.

**Docker Swarm + Portainer**  
O Swarm orquestra os serviços na EC2 com reinicialização automática em caso de falha. O Portainer fornece interface web visual para gerenciar stacks, inspecionar containers, visualizar logs e publicar novas versões sem acesso SSH direto.

**CI/CD — GitHub Actions → GHCR**  
A cada push para `main`, o GitHub Actions compila a imagem Docker e a publica no GitHub Container Registry (`ghcr.io/thiagomarianols/bikot:latest`). O deploy no Swarm é feito pelo Portainer apontando para essa imagem.

### Stack de Monitoramento

| Ferramenta | Função |
|---|---|
| **cAdvisor** | Coleta métricas dos containers (CPU, memória, rede, I/O por container) |
| **Node Exporter** | Coleta métricas do host EC2 (CPU total, RAM, disco, uptime) |
| **Prometheus** | Agrega e armazena métricas em série temporal (scraping de cAdvisor e Node Exporter) |
| **Grafana** | Visualiza métricas em dashboards configuráveis — gráficos históricos, alertas, saúde do sistema |

### Sequência de Inicialização (`entrypoint.sh`)

```bash
# 1. Aguarda Aurora RDS ficar disponível (até 30 tentativas, intervalo 2s)
# 2. Aplica migrações
python manage.py migrate --noinput
# 3. Coleta estáticos (WhiteNoise)
python manage.py collectstatic --noinput
# 4. Inicia servidor de aplicação
gunicorn bikot.wsgi:application --bind 0.0.0.0:8000
```

---

## 9. Segurança e LGPD

### Proteção de Credenciais

- Todas as variáveis sensíveis são carregadas via `os.environ` — nenhuma hardcoded
- `.env` está no `.gitignore`; `.env.example` documenta as variáveis com valores fictícios
- CSRF ativo nas views HTML; exempt somente nos endpoints REST com API Key
- HTTPS obrigatório em produção

### Conformidade LGPD

| Princípio | Aplicação no Bikot |
|---|---|
| **Minimização de dados** | Coleta apenas: UID do cartão, matrícula, timestamp, resultado do acesso |
| **Finalidade** | Dados usados exclusivamente para controle de acesso ao bicicletário |
| **Sem dados sensíveis** | Sem biometria, imagem pessoal, localização ou dados de saúde |
| **Rastreabilidade** | Todos os eventos logados em `RegistroMovimentacao` com timestamp |
| **Direito de exclusão** | Administrador pode remover aluno e todos os seus dados pelo painel |

---

## 10. Dossiê de Evidências

> Adicione abaixo as mídias de evidência do projeto.

### Dashboard Administrativo

| Evidência | Arquivo/Link |
|---|---|
| Print do Dashboard Admin — visão geral de vagas | [INSERIR PRINT] |
| Print do cadastro de aluno com RFID | [INSERIR PRINT] |
| Print do histórico de logs de acesso | [INSERIR PRINT] |

### Dashboard TV

| Evidência | Arquivo/Link |
|---|---|
| Print do Dashboard TV — vagas em tempo real | [INSERIR PRINT] |
| Print do slideshow de avisos com QR code | [INSERIR PRINT] |

### Infraestrutura e Monitoramento

| Evidência | Arquivo/Link |
|---|---|
| Print do Grafana — métricas de containers | [INSERIR PRINT] |
| Print do Portainer — stack em execução no Swarm | [INSERIR PRINT] |
| Print do Aurora RDS — console AWS | [INSERIR PRINT] |

---

## 11. Instruções de Execução

### Desenvolvimento Local

**Pré-requisitos:** Python 3.12+

```bash
# 1. Clonar o repositório
git clone https://github.com/ThiagoMarianols/Bikot.git
cd Bikot

# 2. Criar e ativar ambiente virtual
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com valores para desenvolvimento local

# 5. Aplicar migrações e popular dados de teste
python manage.py migrate
python manage.py setup_db      # cria 10 vagas e 5 alunos de teste

# 6. Criar superusuário
python manage.py createsuperuser

# 7. Iniciar servidor
python manage.py runserver
# Acesse: http://127.0.0.1:8000
```

### Produção com Docker

**Pré-requisitos:** Docker e Docker Compose

```bash
# 1. Clonar e configurar
git clone https://github.com/ThiagoMarianols/Bikot.git
cd Bikot
cp .env.example .env
# Editar .env com credenciais de produção (Aurora RDS, API Key, etc.)

# 2. Subir com Docker Compose
docker-compose up -d

# Acesse:
# Dashboard Admin: http://localhost:8000
# Dashboard TV:    http://localhost:8000/tv/
# API:             http://localhost:8000/api/
```

### Variáveis de Ambiente (`.env.example`)

```env
SECRET_KEY=django-secret-key-forte-aqui
DEBUG=False
ALLOWED_HOSTS=seu-dominio.com,localhost
ESP32_API_KEY=chave-secreta-esp32
JWT_SECRET_KEY=chave-jwt-secreta
DB_NAME=bikot
DB_USER=bikot
DB_PASSWORD=senha-do-banco
DB_HOST=<aurora-rds-endpoint>
DB_PORT=5432
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=senha-admin
```

---

## 12. Marcas Formativas Senac

| Marca | Evidência neste repositório |
|---|---|
| **Domínio técnico-científico** | Backend Django estruturado com MVT; 7 modelos de dados bem definidos; API REST com contratos claros; banco Aurora RDS configurado em produção com failover |
| **Resolução de problemas com autonomia digital** | Integração com ESP32 via API Key; fluxo de cadastro RFID em tempo real; deploy automatizado via CI/CD; stack de monitoramento configurada na AWS |
| **Visão crítica, ética e segurança** | Credenciais protegidas via variáveis de ambiente; JWT + API Key + CSRF; conformidade LGPD com minimização de dados; HTTPS em produção |
| **Comunicação e colaboração** | Repositório organizado e público; CI/CD configurado; documentação técnica em `docs/`; README bilíngue com equipe completa |
| **Atitude empreendedora e inovadora** | Sistema completo em produção na AWS; monitoramento com Grafana; Dashboard TV público; solução demonstrável para um problema real da faculdade |

---

## 13. Uso de Inteligência Artificial Generativa

Este projeto utilizou IA generativa (Claude da Anthropic) como **ferramenta de apoio** no desenvolvimento do backend e da documentação. Todo o código foi revisado, compreendido e validado pelos membros da equipe. A banca pode questionar qualquer trecho — todos os integrantes estão aptos a explicar as decisões técnicas tomadas.

---

*Faculdade Senac PE · CST Análise e Desenvolvimento de Sistemas · 4º Período · 2026*
