# 4. Arquitetura

## Visão geral

```mermaid
flowchart LR
    V[Voluntário / gestor] -- login --> P[Painel<br/>painel.py]
    D[Doador / comunidade] --> T[Página de transparência<br/>publico.py]
    P --> DB[(Banco de dados<br/>SQLite / PostgreSQL)]
    T --> DB
    P --> C[Comprovantes<br/>pasta privada]
    P --> X[Planilha CSV]
```

## Modelo de dados

```mermaid
erDiagram
    ORGANIZACAO ||--o{ USUARIO : tem
    ORGANIZACAO ||--o{ LANCAMENTO : registra
    ORGANIZACAO ||--o{ CONVITE : envia
    ORGANIZACAO {
        string nome
        string slug "endereço público"
        string cnpj
        string causa
        bool publico
    }
    USUARIO {
        string nome
        string email
        string senha_hash
    }
    LANCAMENTO {
        string tipo "receita ou despesa"
        date data
        string descricao
        string categoria
        decimal valor
        string comprovante
    }
    CONVITE {
        string token "link de uso único, vale 7 dias"
        datetime usado_em
    }
```

## Decisões

| Decisão | Motivo |
|---|---|
| Flask (Python) | Simples, leve e fácil de aprender: bom para contribuidores iniciantes |
| Sem framework JavaScript | Menos complexidade; páginas rápidas em celulares simples |
| SQLite → PostgreSQL | Começa sem instalar nada; escala quando precisar |
| Valores em `Decimal` | Evita erros de arredondamento com dinheiro |
| Comprovantes fora da página pública | Podem conter CPF, endereço etc. (LGPD) |
| Categorias fixas e simples | Voluntários não precisam saber contabilidade |
| Convite por link, sem e-mail | Não exige servidor de e-mail; voluntários já usam WhatsApp |
| Relatório em HTML com "Imprimir / salvar em PDF" | Sem biblioteca extra; o navegador gera o PDF |
| CSRF próprio (token na sessão) | Protege formulários sem adicionar dependência |
