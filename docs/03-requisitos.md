# 3. Requisitos

## Histórias de usuário

| # | Como... | quero... | para... | Situação |
|---|---|---|---|---|
| 1 | gestor(a) da ONG | cadastrar minha organização | começar a usar sem custo | ✅ feito |
| 2 | voluntário(a) | registrar uma doação recebida | manter o caixa atualizado | ✅ feito |
| 3 | voluntário(a) | registrar um gasto com foto da nota | comprovar o uso do dinheiro | ✅ feito |
| 4 | gestor(a) | ver saldo e gráficos | acompanhar as finanças | ✅ feito |
| 5 | doador(a) | ver a página pública da ONG | saber para onde foi minha doação | ✅ feito |
| 6 | gestor(a) | exportar uma planilha | prestar contas em editais | ✅ feito |
| 7 | gestor(a) | tornar a página privada | controlar o que é publicado | ✅ feito |
| 8 | gestor(a) | convidar outros voluntários | dividir o trabalho | ✅ feito |
| 9 | gestor(a) | gerar relatório em PDF | anexar em editais | ✅ feito |
| 10 | gestor(a) | definir metas (ex.: arrecadar R$ 5 mil) | engajar doadores | 💡 ideia |
| 11 | doador(a) | doar por Pix direto da página | facilitar a doação | 💡 ideia |

## Requisitos não funcionais

- Funcionar bem no celular (muitos voluntários não têm computador).
- Linguagem simples, sem termos contábeis.
- Dados de cada organização isolados das demais.
- Senhas guardadas com hash; comprovantes acessíveis só pela organização.
- Formulários protegidos contra CSRF.
- Código aberto (licença MIT), com testes automáticos.
