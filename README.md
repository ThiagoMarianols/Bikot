# 🚲 Bikot (Bicicletário IoT Inteligente)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0%2B-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![IoT](https://img.shields.io/badge/IoT-ESP32-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

O **Bikot** é um sistema completo de controle de acesso, automação e monitoramento de vagas de bicicletários baseado em IoT (Internet das Coisas). A plataforma integra um backend em Django robusto com microcontroladores (como o **ESP32**) através de APIs REST seguras e comunicação em rede local ou nuvem (Wi-Fi), permitindo o gerenciamento e destravamento físico de vagas em tempo real via crachás RFID.

---

## 📋 Sumário

- [Visão Geral](#-visão-geral)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Principais Funcionalidades](#-principais-funcionalidades)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Como Executar o Projeto](#-como-executar-o-projeto)
- [Estrutura de Arquivos](#-estrutura-de-arquivos)
- [Documentação Detalhada](#-documentação-detalhada)

---

## 🔍 Visão Geral

No dia a dia, o **Bikot** elimina a necessidade de chaves físicas ou cadeados manuais. O fluxo é simples:
1. **Entrada:** O aluno aproxima seu crachá RFID de uma vaga disponível. O leitor físico valida as credenciais com o servidor Django. A garra física abre, a bicicleta é guardada e trancada com segurança. O sistema aloca a vaga ao aluno.
2. **Saída:** O aluno aproxima o crachá novamente na vaga. O servidor verifica que ele é o proprietário da bicicleta naquela vaga, destrava a garra física para a retirada e libera a vaga no banco de dados.

Cada usuário só pode ocupar **uma vaga por vez**, e administradores têm controle remoto absoluto do sistema através de um painel web dinâmico.

---

## 📐 Arquitetura do Sistema

O projeto funciona no formato de monolito utilizando o padrão **MVT (Model-View-Template)** do Django, expondo endpoints REST isentos de proteção CSRF e protegidos via tokens **JWT (JSON Web Token)** ou **API Keys** estruturadas para o microcontrolador ESP32.

```mermaid
graph TD
    subgraph Plataforma Web Django (Servidor na Nuvem/Local)
        Admin[Navegador Administrador / Web Admin]
        TV[Painel de Telemetria / TV]
        DB[(Banco de Dados SQLite / Postgres)]
        Views[Django Views & APIs]
    end

    subgraph Hardware IoT (Conectado via Wi-Fi/Internet)
        Hardware[ESP32 / Placa Física com RFID e Trava]
    end

    Admin -->|HTTP / HTML / AJAX| Views
    TV -->|HTTP / JSON polling| Views
    Views -->|Query / Save| DB

    Hardware -->|HTTP REST APIs - POST Scan / GET Status| Views
```

---

## 🌟 Principais Funcionalidades

### 💻 Painel do Administrador (Web)
* **Dashboard em Tempo Real:** Gráficos com o status das vagas (ocupadas, livres, bloqueadas) e logs recentes.
* **Gerenciamento de Usuários:** Cadastro completo de alunos, vinculação ágil de novos cartões RFID.
* **Controle de Vagas:** Bloqueio de vagas para manutenção e comando de **destravamento remoto** em casos de emergência.
* **Mural de Avisos Dinâmico:** Cadastro de anúncios com data de expiração, imagens customizáveis e links externos.

### 📺 Painel de Telemetria (TV Pública)
* Exibição do estado das vagas atualizado dinamicamente em tempo real (via polling AJAX).
* Slideshow automático de avisos administrativos.
* **Geração Dinâmica de QR Codes:** Se um aviso contiver link, um QR Code é gerado na tela da TV para que os alunos o escaneiem.

### 🔌 Integração IoT (ESP32)
* **Comunicação Segura:** Autenticação via `X-API-Key` no cabeçalho ou parâmetro das requisições HTTP.
* **Protocolo Baseado em Códigos de Sinalização:**
  * `1` — **Liberar Vaga:** Comando para abrir a garra física correspondente.
  * `2` — **Modo de Cadastro:** O leitor entra em modo de espera para vincular um crachá novo a um aluno na web.
  * `3` — **Acesso Negado / Erro:** Sinaliza erro (LED vermelho ou som do buzzer) por crachá inválido ou falta de vagas.

---

## 🛠 Tecnologias Utilizadas

* **Backend / Web App:** Python, Django 6.x
* **Banco de Dados:** SQLite (padrão de desenvolvimento) / PostgreSQL (suportado nativamente)
* **Segurança:** PyJWT (Autenticação JSON Web Token), API Key baseada em variáveis de ambiente
* **Integração Física:** ESP32 (Wi-Fi HTTP REST), Leitor RFID RC522 (ou compatível), Servomotores / Solenoides de trava
* **Comunicação Serial (Legado/Alternativo):** PySerial

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
* Python 3.10 ou superior instalado.

### Passo a Passo

1. **Clonar o Repositório:**
   ```bash
   git clone https://github.com/ThiagoMarianols/Bikot.git
   cd Bikot
   ```

2. **Criar e Ativar Ambiente Virtual:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instalar Dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar o Ambiente:**
   Crie um arquivo `.env` na raiz do projeto (utilize o modelo abaixo):
   ```env
   SECRET_KEY=sua-chave-secreta-django
   DEBUG=True
   ALLOWED_HOSTS="*"
   ESP32_API_KEY=dev-key-bikot-2026
   ```

5. **Rodar Migrações e Inicializar Banco de Dados:**
   ```bash
   python manage.py migrate
   ```

6. **Popular Dados de Teste (Opcional):**
   O sistema possui um comando personalizado para cadastrar rapidamente 10 vagas e 5 alunos com tags fictícias para teste:
   ```bash
   python manage.py setup_db
   ```

7. **Criar Administrador:**
   ```bash
   python manage.py createsuperuser
   ```

8. **Executar o Servidor:**
   ```bash
   python manage.py runserver
   ```
   Acesse a interface no navegador através de `http://127.0.0.1:8000/`.

---

## 📂 Estrutura de Arquivos

* `/bikot` - Arquivos de configuração global do projeto Django (configurações, URLs, WSGI/ASGI).
* `/core` - Módulo principal do sistema contendo modelos, views, rotas de API, templates HTML e arquivos estáticos (CSS/JS).
* `DOCUMENTACAO_TECNICA.md` - Detalhamento completo dos endpoints, modelagem e fluxos lógicos.
* `FUNCIONAMENTO_DO_SISTEMA.md` - Manual operacional do sistema e regras de negócio para usuários finais.

---

## 📚 Documentação Detalhada

Para informações detalhadas de desenvolvimento ou de funcionamento do negócio, consulte os guias dedicados:
* 🛠 **[Documentação Técnica do Projeto (APIs, Modelagem e Segurança)](DOCUMENTACAO_TECNICA.md)**
* 🚲 **[Manual de Funcionamento e Regras de Negócio](FUNCIONAMENTO_DO_SISTEMA.md)**

---
Desenvolvido por **[ThiagoMariano](https://github.com/ThiagoMarianols)**.
