# Manual de Funcionamento e Regras de Negócio do Bikot

Bem-vindo ao **Bikot**, o sistema inteligente de controle e monitoramento de vagas de bicicletário baseado em Internet das Coisas (IoT). 

Este manual explica, em linguagem simples e não técnica, como o sistema completo funciona, quais são as regras de uso do bicicletário e como a plataforma web se comunica com as vagas físicas.

---

## 1. O que é o Bikot?

O Bikot é um bicicletário inteligente automatizado. Em vez de usar cadeados comuns ou chaves físicas, os alunos utilizam seus crachás estudantis (com tecnologia de aproximação RFID) para abrir e travar as vagas das bicicletas. 

O sistema é composto por duas partes que conversam o tempo todo:
1. **O Sistema Web (Painel Administrativo)**: Onde a coordenação ou a equipe de segurança cadastra alunos, monitora quais vagas estão ocupadas, destrava vagas remotamente e publica avisos importantes.
2. **O Protótipo Físico (Placa Inteligente ESP32)**: O dispositivo eletrônico instalado no bicicletário que possui o leitor de crachá e os braços/garras físicas que trancam a bicicleta na vaga.

---

## 2. A Rotina do Aluno (Como usar no dia a dia)

O ciclo de uso do bicicletário pelo aluno é automatizado e extremamente simples.

### A) Guardando a Bicicleta (Entrada)
1. O aluno chega com sua bicicleta até uma vaga disponível no bicicletário.
2. Ele aproxima seu crachá do leitor da placa física.
3. O sistema verifica instantaneamente se o aluno é cadastrado e ativo:
   * Se o cadastro estiver correto, o sistema envia o sinal **1** (Liberar Vaga). 
   * A garra física abre, o aluno coloca a sua bicicleta na vaga e a garra se fecha, prendendo-a em segurança.
   * O sistema registra no banco de dados que o aluno acabou de guardar a bicicleta e que aquela vaga agora está **Ocupada**.

### B) Retirando a Bicicleta (Saída)
1. O aluno vai até a vaga onde sua bicicleta está trancada.
2. Ele aproxima o seu crachá do leitor físico.
3. O sistema reconhece que aquele crachá pertence ao aluno que está com a bicicleta presa naquela vaga específica.
4. O sistema envia o sinal **1** (Liberar Vaga).
5. A garra se abre, o aluno retira sua bicicleta e ela se fecha.
6. O sistema atualiza no banco de dados que a vaga voltou a estar **Disponível** para outros alunos usarem.

> [!NOTE]
> **Segurança nas Vagas**: Cada aluno só pode ocupar **uma vaga por vez**. Se um aluno que já tem uma bicicleta guardada aproximar o crachá em uma vaga vazia, o sistema não abrirá a nova vaga (ele só abrirá a vaga onde a bicicleta dele já está presa para retirada).

---

## 3. Cadastro de Crachás (Vincular Aluno e Cartão)

Para que um aluno consiga usar o bicicletário, ele precisa ter um crachá associado ao seu nome no sistema.

### Como funciona o fluxo de cadastro:
1. No sistema web, o administrador abre o cadastro de um aluno e clica em **"Vincular Leitor"**.
2. O sistema web entra em "modo de espera" e envia o sinal **2** para a placa física.
3. A placa física entra no modo de cadastro. O leitor físico fica aguardando a aproximação de qualquer crachá novo.
4. Ao aproximar o crachá da placa, a tag é lida e enviada para o sistema.
5. O sistema grava o crachá no nome do aluno selecionado e finaliza a operação com sucesso no painel web.

### Regra de Substituição/Troca de Crachás:
* Se um aluno perder o crachá e o administrador cadastrar um novo cartão para ele, o cartão antigo é excluído do sistema por segurança.
* **E se o crachá já estiver cadastrado em outra pessoa?** Caso o administrador registre para o Aluno B um crachá que antes pertencia ao Aluno A, o sistema é inteligente e **desvincula** automaticamente o crachá do Aluno A antes de passá-lo para o Aluno B. Isso evita que duas pessoas tenham acesso com o mesmo cartão.

---

## 4. O Sistema de Sinalização Física (Os Códigos 1, 2 e 3)

Para que a placa física (ESP32) saiba exatamente o que fazer de forma rápida, o sistema web responde a cada aproximação de crachá enviando apenas um número de comando (**1**, **2** ou **3**):

*   **Número `1` — Libera Vaga**:
    *   *O que significa*: O crachá aproximado pertence a um aluno cadastrado e ativo.
    *   *O que a placa física faz*: Aciona o motor/trava para abrir a garra física correspondente da vaga para colocar ou retirar a bicicleta.
*   **Número `2` — Modo de Cadastro**:
    *   *O que significa*: O administrador abriu a tela de cadastro na web e o sistema está aguardando ler um crachá novo para registrá-lo.
    *   *O que a placa física faz*: Sinaliza ao operador (ex: pisca um LED azul ou emite um som) informando que a próxima tag que encostar ali será gravada para cadastro e **não** abrirá garras de vagas.
*   **Número `3` — Acesso Negado / Erro**:
    *   *O que significa*: O crachá aproximado não está cadastrado, está inativo/bloqueado, ou não há vagas disponíveis no estacionamento.
    *   *O que a placa física faz*: Sinaliza ao usuário que ocorreu um erro de leitura ou que o acesso foi recusado (ex: acende um LED vermelho ou emite um bipe de erro com o buzzer).

---

## 5. O Painel Web do Administrador

A equipe administrativa gerencia todo o bicicletário através de uma página web moderna com as seguintes telas:

1. **Painel Geral (Dashboard)**: Exibe gráficos rápidos de quantas vagas estão livres, ocupadas ou interditadas (bloqueadas para manutenção), além do histórico recente de quem entrou e saiu.
2. **Gerenciamento de Alunos**: Lista com todos os alunos, permitindo cadastrar novos usuários, alterar dados e gerenciar crachás via leitor físico.
3. **Visualização das Vagas**: Permite bloquear uma vaga defeituosa (impedindo que ela abra ou seja alocada a novos alunos) ou clicar em "Destravar" para liberar uma vaga manualmente de forma remota em caso de emergência.
4. **Mural de Avisos**: Tela para cadastrar avisos e imagens que aparecem no painel público (TV) do bicicletário.
5. **Histórico de Logs**: Lista de auditoria mostrando o dia e a hora exata de cada entrada, saída, tentativa frustrada (acesso negado) e liberação manual.

---

## 6. Recursos Avançados do Mural de Avisos e Segurança

O mural de avisos foi aprimorado para fornecer uma comunicação mais flexível e atrativa com os usuários do bicicletário.

### A) Mídias e Códigos QR nos Avisos
Ao cadastrar um aviso, o administrador pode fornecer elementos adicionais que serão exibidos no painel da TV:
*   **Fotos e Banners**: É possível carregar um arquivo de imagem (banner informativo) para exibição. O administrador pode definir se a imagem deve **Preencher** a tela inteira (cortando bordas se necessário) ou se deve ser **Ajustada** (preservando as proporções sem cortes).
*   **Redirecionamento via QR Code**: Se um link externo (URL) for fornecido no cadastro do aviso, a tela de telemetria (TV) gerará dinamicamente um QR Code ao lado do aviso, permitindo que os alunos leiam com seus celulares para acessar o conteúdo.
*   **Data de Expiração**: Os avisos podem ser agendados para expirar. Ao atingir o prazo configurado, o aviso deixa de aparecer na TV automaticamente.

### B) Tempo de Exibição Dinâmico
Na tela do painel de avisos, o administrador pode configurar o tempo de transição (em segundos) entre cada aviso. A tela de telemetria da TV lê essa configuração diretamente do banco de dados e ajusta o slideshow automaticamente para a velocidade configurada.

### C) Integração Segura com APIs
A plataforma suporta chaves individuais seguras baseadas em tokens JWT (JSON Web Tokens). Isso permite que sistemas adicionais, aplicativos móveis ou painéis customizados se comuniquem de forma independente e auditada com o backend do Bikot, com tokens que expiram periodicamente para garantir a máxima segurança dos acessos.
