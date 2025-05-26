# Citius Web Scraper

Um scraper em Python para extrair informações do Portal Citius (https://www.citius.mj.pt/portal/consultas/consultascire.aspx), permitindo pesquisas por NIF/NIPC ou designação com intervalo de datas.


## Nova Versão

Foi lançada uma nova versão em [Citius Selenium Scraper]([https://www.citius.mj.pt/](https://github.com/Raam977/citius-selenium-scraper.git))  onde é utilizado o Selenium WebDriver para ultrupassar problemas de limitações de reitrada
## Características

- Pesquisa por NIF/NIPC ou designação
- Filtro por intervalo de datas
- Extração de todos os credores associados a processos
- Exportação para CSV e JSON
- Modo de debug para diagnóstico
- Suporte a diferentes formatos de apresentação de resultados
- Sem necessidade de captcha ou autenticação


https://github.com/user-attachments/assets/80b48231-b4cd-4799-b6a3-9a9498f66d1b


## Requisitos

- Python 3.6+
- Bibliotecas: requests, beautifulsoup4, rich (para interface visual)

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/Raam977/citius-scraper.git
cd citius-scraper

# Instalar dependências
pip install -r requirements.txt
```

## Utilização

### Pesquisa por NIF/NIPC

```bash
python citius_scraper_final_v2.py --nif 12345678 --output resultados.csv
```

### Pesquisa por designação

```bash
python citius_scraper_final_v2.py --designacao "Nome da Empresa" --output resultados.csv
```

### Filtrar por intervalo de datas

```bash
python citius_scraper_final_v2.py --nif 12345678 --data-inicio 2023-01-01 --data-fim 2023-12-31 --output resultados.csv
```

### Ativar modo de debug

```bash
python citius_scraper_final_v2.py --nif 12345678 --debug --output resultados.csv
```

## Estrutura dos Resultados

Os resultados são exportados em dois formatos:

1. **CSV**: Para uso em Excel ou outras ferramentas de planilha
2. **JSON**: Preserva a estrutura completa dos dados, incluindo listas de credores

### Exemplo de estrutura JSON

```json
[
  {
    "Tribunal": "Comarca do Porto Este - Amarante",
    "Ato": "Edital (Verificação de Créditos) - Portal Citius",
    "Referência": "98732152",
    "Processo": "1705/24.*****AMT-E, Juízo de Comércio de Amarante - Juiz 1",
    "Espécie": "Verificação ulterior créditos/outros direitos (CIRE)",
    "Data": "20/05/2025",
    "Data da propositura da ação": "15/05/2025",
    "Insolvente": "* ***, Lda.",
    "NIF/NIPC": "515755230",
    "Administrador Insolvência": "Maria *****",
    "Credores": [
      {
        "Nome": " *****, Lda.",
        "NIF/NIPC": "517*****"
      },
      {
        "Nome": "*****, Lda - Armazém de Cabedais",
        "NIF/NIPC": "5037********"
      },
      // ... mais credores
    ],
    "Credor": "*******, Lda.",
    "Links": []
  }
]
```

## Arquivos Incluídos

- `citius_scraper_final_v2.py`: Script principal com todas as funcionalidades
- `requirements.txt`: Dependências do projeto
- `README.md`: Documentação do projeto

## Limitações

- O site pode mudar sua estrutura HTML, exigindo atualizações no parser
- Pesquisas muito amplas podem retornar muitos resultados e demorar mais tempo
- O site pode implementar limitações de taxa de requisições no futuro

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## Aviso Legal

Este script é fornecido apenas para fins educacionais e de pesquisa. O uso deste script deve estar em conformidade com os termos de serviço do Portal Citius e todas as leis aplicáveis. O autor não se responsabiliza pelo uso indevido deste script.
