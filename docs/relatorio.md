# Relatório do Projeto Social: Contas Abertas

**Aluno:** Daniel Tokunaga
**Disciplina:** Projeto Integrador
**Repositório:** https://github.com/Tokmogi/contas-abertas
**Post no LinkedIn:** ✏️ link

> Os trechos marcados com ✏️ precisam ser completados com informações suas.

---

## 1. Introdução

Este relatório descreve o desenvolvimento do **Contas Abertas**, um sistema web gratuito e de código
aberto que ajuda organizações sociais pequenas a controlar suas finanças e a prestar contas de forma
transparente aos doadores e à comunidade.

### 1.1 Motivação pessoal

✏️ Conte por que escolheu este tema: experiência com voluntariado, alguma ONG conhecida, sua relação com
contabilidade e programação. Explique por que esse projeto te deixa feliz.

## 2. Identificação do problema social

Organizações da sociedade civil pequenas funcionam, em sua maioria, sem funcionários e com orçamento
reduzido. Sem contador e sem ferramentas adequadas, elas têm dificuldade para:

- mostrar aos doadores como o dinheiro foi utilizado, o que reduz a confiança e as doações;
- organizar comprovantes e montar prestações de contas exigidas por editais;
- gastar o tempo dos voluntários com a atividade-fim em vez de com papelada.

✏️ Acrescente dados (por exemplo, do Mapa das OSCs/IPEA) e, se possível, o relato de uma organização
com que você conversou.

## 3. Conceituação do projeto

### 3.1 Objetivo geral

Facilitar a prestação de contas de organizações sociais pequenas e aumentar a confiança de doadores e
da comunidade.

### 3.2 Objetivos específicos

1. Permitir o registro de receitas e despesas em linguagem simples.
2. Guardar comprovantes vinculados a cada gasto.
3. Gerar uma página pública de transparência com gráficos.
4. Exportar uma planilha para prestação de contas em editais.
5. Proteger dados pessoais, conforme a LGPD.

### 3.3 Público beneficiado

- Organizações sociais pequenas, que ganham gestão simples e credibilidade.
- Doadores, que passam a ver como sua doação foi usada.
- Comunidade atendida, que se beneficia de organizações com mais recursos.

### 3.4 Impacto social esperado

Espera-se que organizações usuárias reduzam o tempo gasto com prestação de contas, aumentem o
percentual de gastos comprovados e conquistem mais doações e editais por demonstrarem transparência.

## 4. Metodologia

O projeto foi conduzido em ciclos curtos (abordagem ágil), com tarefas organizadas em issues e num
quadro kanban do GitHub. Etapas:

1. Pesquisa sobre o problema e definição do público.
2. Levantamento de requisitos (histórias de usuário).
3. Criação do repositório e da documentação inicial.
4. Desenvolvimento do produto mínimo viável (MVP).
5. Testes automatizados e teste com usuário.
6. Divulgação no LinkedIn e coleta de sugestões.
7. Melhorias e relatório final.

## 5. Desenvolvimento técnico

### 5.1 Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3 e Flask | Aplicação web |
| SQLAlchemy | Banco de dados (SQLite / PostgreSQL) |
| HTML, CSS e Chart.js | Telas responsivas e gráficos |
| Pytest e GitHub Actions | Testes automáticos a cada envio de código |
| Docker | Facilitar a publicação |
| Git e GitHub | Versionamento, documentação e colaboração |

### 5.2 Arquitetura

O sistema tem três partes: (1) **cadastro e login**; (2) **painel da organização**, onde os
lançamentos e comprovantes são registrados; e (3) **portal público**, que mostra os totais, gráficos e
a lista de movimentações. Os detalhes e o modelo de dados estão em `docs/04-arquitetura.md`.

### 5.3 Funcionalidades entregues

- Cadastro de organização com endereço público próprio (ex.: `/transparencia/instituto-mao-amiga`).
- Registro, edição e exclusão de entradas e saídas, com categorias simples.
- Envio de comprovante em PDF ou foto, inclusive pela câmera do celular.
- Painel com saldo, gráficos por categoria e por mês e percentual de gastos comprovados.
- Página pública de transparência, que pode ser tornada privada.
- Exportação de planilha (CSV, abre no Excel) para prestação de contas.
- Isolamento dos dados entre organizações e senhas protegidas por hash.
- Convite de voluntários por link de uso único (vale 7 dias), fácil de enviar por WhatsApp.
- Relatório de prestação de contas por período, com saldo inicial e final, totais por categoria e
  linhas de assinatura, pronto para imprimir ou salvar em PDF.
- Proteção contra CSRF em todos os formulários.
- Interface pensada para o celular: menu recolhível, lançamentos em cartões, botão flutuante de
  "novo lançamento", botões grandes de entrada/saída e foto do comprovante direto da câmera.
- Filtro por mês e por tipo no painel, aviso de saídas sem comprovante e página pública com botão de
  compartilhar no WhatsApp.
- Segurança reforçada: proteção contra redirecionamento malicioso no login, cabeçalhos contra
  clickjacking e comprovantes servidos sem permitir execução de scripts.
- Datas no horário de Brasília, mesmo com o servidor em outro fuso.
- 38 testes automatizados executados no GitHub Actions.

✏️ Insira aqui as capturas de tela (`docs/prototipos/`).

### 5.4 Desafios e soluções

| Desafio | Solução |
|---|---|
| Voluntários sem conhecimento contábil | Linguagem simples ("entrada", "saída") e categorias prontas |
| Comprovantes podem ter dados pessoais | Arquivos ficam privados; a página pública mostra só se o gasto foi comprovado |
| Arredondamento de valores em dinheiro | Uso do tipo `Decimal` em vez de números de ponto flutuante |
| Uso pelo celular | Layout responsivo e envio de foto direto da câmera |
| Valores digitados como "1.500" (ponto de milhar) | Leitura do valor reconhece o padrão brasileiro, com teste automático |
| Garantir que uma ONG não veja dados de outra | Todas as consultas filtradas pela organização do usuário, com teste automático |

✏️ Acrescente desafios que você enfrentou e como os professores ou colegas ajudaram.

## 6. Repositório no GitHub

O repositório contém o código, a documentação (problema, proposta, requisitos, arquitetura e
cronograma), licença MIT, guia de contribuição, código de conduta, modelos de issue e testes
automáticos. Link: https://github.com/Tokmogi/contas-abertas

## 7. Divulgação no LinkedIn

✏️ Cole o link da publicação, a data e um resumo do retorno: número de reações e comentários, sugestões
recebidas e organizações interessadas. O texto usado está em `docs/post-linkedin.md`.

## 8. Resultados

✏️ Descreva o que foi alcançado: ONG piloto (se houver), opinião dos usuários, indicadores de
`docs/02-proposta-e-objetivos.md`.

## 9. Próximos passos

- Metas de arrecadação e botão de doação por Pix na página pública.
- Publicação em um servidor gratuito.
- Teste com mais organizações e incorporação das sugestões do LinkedIn.

## 10. Conclusão

✏️ O que você aprendeu (técnico e comportamental), como se sentiu como "profissional fazedor" e qual
impacto espera que o projeto tenha.

## Referências

- IPEA. *Mapa das Organizações da Sociedade Civil.* https://mapaosc.ipea.gov.br
- Lei nº 13.019/2014 (Marco Regulatório das Organizações da Sociedade Civil).
- Lei nº 13.709/2018 (Lei Geral de Proteção de Dados, LGPD).
- Documentação do Flask: https://flask.palletsprojects.com
