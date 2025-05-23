#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para web scraping do Portal Citius
Permite pesquisar por NIF/designação com intervalo de datas
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import argparse
import datetime
import os
import time
import logging
import json
from urllib.parse import urljoin

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("citius_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CitiusScraper:
    """Classe para fazer web scraping do Portal Citius"""
    
    def __init__(self, debug=False):
        """
        Inicializa o scraper com a URL base e headers
        
        Args:
            debug (bool): Se True, ativa o modo de debug com mais logs
        """
        self.base_url = "https://www.citius.mj.pt/portal/consultas/consultascire.aspx"
        self.results_url = "https://www.citius.mj.pt/portal/consultas/ConsultasCire.aspx"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            # Ativar logging para requests
            import http.client as http_client
            http_client.HTTPConnection.debuglevel = 1
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        
    def get_form_data(self):
        """
        Obtém os dados iniciais do formulário, incluindo campos ocultos
        
        Returns:
            dict: Dicionário com os dados do formulário ou None em caso de erro
        """
        try:
            logger.info("Obtendo dados iniciais do formulário...")
            response = self.session.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair os campos ocultos necessários para o POST
            viewstate = soup.find('input', {'id': '__VIEWSTATE'})
            eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})
            viewstategenerator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
            
            if not viewstate or not eventvalidation or not viewstategenerator:
                logger.error("Não foi possível encontrar todos os campos ocultos necessários")
                if not viewstate:
                    logger.error("Campo __VIEWSTATE não encontrado")
                if not eventvalidation:
                    logger.error("Campo __EVENTVALIDATION não encontrado")
                if not viewstategenerator:
                    logger.error("Campo __VIEWSTATEGENERATOR não encontrado")
                
                # Salvar HTML para debug
                with open("debug_form_page.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info("HTML da página salvo em debug_form_page.html para análise")
                
                return None
            
            form_data = {
                '__VIEWSTATE': viewstate.get('value', ''),
                '__EVENTVALIDATION': eventvalidation.get('value', ''),
                '__VIEWSTATEGENERATOR': viewstategenerator.get('value', ''),
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATEENCRYPTED': ''
            }
            
            logger.debug(f"Dados do formulário obtidos: {form_data}")
            return form_data
            
        except requests.RequestException as e:
            logger.error(f"Erro ao obter dados do formulário: {e}")
            return None
    
    def search(self, nif=None, designacao=None, data_inicio=None, data_fim=None, tribunal=None, grupo_actos=None, acto=None, dias=None, max_retries=3):
        """
        Realiza uma pesquisa no Portal Citius
        
        Args:
            nif (str): NIF/NIPC para pesquisa
            designacao (str): Designação para pesquisa
            data_inicio (str): Data de início no formato DD-MM-YYYY
            data_fim (str): Data de fim no formato DD-MM-YYYY
            tribunal (str): Tribunal para filtrar
            grupo_actos (str): Grupo de actos para filtrar
            acto (str): Acto específico para filtrar
            dias (str): Filtro de dias ('15', '30', 'todos')
            max_retries (int): Número máximo de tentativas em caso de erro
            
        Returns:
            list: Lista de resultados encontrados
        """
        # Validar parâmetros
        if not nif and not designacao:
            logger.error("É necessário fornecer NIF ou designação para pesquisa")
            return []
        
        # Obter dados do formulário com retry
        form_data = None
        for attempt in range(max_retries):
            form_data = self.get_form_data()
            if form_data:
                break
            logger.warning(f"Tentativa {attempt+1}/{max_retries} falhou. Tentando novamente...")
            time.sleep(2)  # Esperar antes de tentar novamente
        
        if not form_data:
            logger.error(f"Não foi possível obter dados do formulário após {max_retries} tentativas")
            return []
        
        # Preparar os dados para envio
        data = form_data.copy()
        
        # Adicionar parâmetros de pesquisa
        if nif:
            data['ctl00$ContentPlaceHolder1$txtPesquisa'] = nif
            data['ctl00$ContentPlaceHolder1$rblTipo'] = 'NIF/NIPC'
            logger.info(f"Pesquisando por NIF/NIPC: {nif}")
        elif designacao:
            data['ctl00$ContentPlaceHolder1$txtPesquisa'] = designacao
            data['ctl00$ContentPlaceHolder1$rblTipo'] = 'Designação'
            logger.info(f"Pesquisando por designação: {designacao}")
        
        # Adicionar datas se fornecidas
        if data_inicio:
            data['ctl00$ContentPlaceHolder1$txtCalendarDesde'] = data_inicio
            logger.info(f"Data início: {data_inicio}")
        if data_fim:
            data['ctl00$ContentPlaceHolder1$txtCalendarAte'] = data_fim
            logger.info(f"Data fim: {data_fim}")
            
        # Adicionar filtros adicionais
        if tribunal:
            if tribunal == 'nova':
                data['ctl00$ContentPlaceHolder1$rbtlTribunais'] = 'Nova Estrutura Judiciária'
            elif tribunal == 'extintos':
                data['ctl00$ContentPlaceHolder1$rbtlTribunais'] = 'Tribunais Extintos'
            logger.info(f"Filtro de tribunal: {tribunal}")
        
        if grupo_actos:
            data['ctl00$ContentPlaceHolder1$ddlGrupoActos'] = grupo_actos
            logger.info(f"Grupo de actos: {grupo_actos}")
        
        if acto:
            data['ctl00$ContentPlaceHolder1$ddlActos'] = acto
            logger.info(f"Acto específico: {acto}")
            
        # Configurar filtro de dias - Sempre usar "Todos"
        data['ctl00$ContentPlaceHolder1$rblDias'] = 'Todos'
        logger.info("Filtro de dias: Todos")
            
        # Adicionar botão de pesquisa
        data['ctl00$ContentPlaceHolder1$btnSearch'] = 'Pesquisar'
        
        try:
            # Enviar o formulário
            logger.info("Enviando formulário de pesquisa...")
            response = self.session.post(
                self.results_url,
                data=data,
                headers=self.headers,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Salvar HTML para debug
            with open("debug_results_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.debug("HTML da página de resultados salvo em debug_results_page.html")
            
            # Processar os resultados
            return self._parse_results(response.text)
        except requests.RequestException as e:
            logger.error(f"Erro ao realizar pesquisa: {e}")
            return []
    
    def _parse_results(self, html_content):
        """
        Analisa o HTML da página de resultados e extrai os dados
        
        Args:
            html_content (str): Conteúdo HTML da página de resultados
            
        Returns:
            list: Lista de dicionários com os resultados
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # Verificar se há mensagem de sem resultados
        no_results_msg = soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_lblNoResults'})
        if no_results_msg and no_results_msg.text.strip():
            logger.info(f"Mensagem de sem resultados encontrada: '{no_results_msg.text.strip()}'")
            return results
        
        # Verificar se há mensagem de total de documentos encontrados
        total_docs_div = soup.find('div', string=re.compile(r'\d+\s+documentos\s+encontrados'))
        if total_docs_div:
            total_docs_text = total_docs_div.text.strip()
            match = re.search(r'(\d+)', total_docs_text)
            if match:
                total_docs = int(match.group(1))
                logger.info(f"Total de documentos encontrados: {total_docs}")
        
        # Método 1: Tentar encontrar a tabela de resultados tradicional
        result_table = soup.find('table', {'id': 'ctl00_ContentPlaceHolder1_gvResults'})
        if result_table:
            logger.info("Tabela de resultados tradicional encontrada")
            return self._parse_table_results(result_table)
        
        # Método 2: Tentar encontrar resultados em formato de lista/div
        results_div = soup.find('div', {'id': 'ctl00_ContentPlaceHolder1_divResultados'})
        if results_div:
            logger.info("Div de resultados encontrada")
            return self._parse_div_results(results_div)
        
        # Método 3: Tentar encontrar resultados em formato de lista de dados
        results_list = soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_dlResultados'})
        if results_list:
            logger.info("Lista de resultados encontrada")
            return self._parse_list_results(results_list)
        
        # Método 4: Tentar encontrar resultados em formato de texto simples
        tribunais_section = soup.find(string=re.compile(r'Todos os tribunais'))
        if tribunais_section:
            parent_div = tribunais_section.find_parent('div')
            if parent_div:
                logger.info("Seção de tribunais encontrada, tentando extrair resultados")
                return self._parse_text_results(parent_div)
        
        # Se nenhum dos métodos acima encontrou resultados
        logger.warning("Nenhum formato de resultados reconhecido foi encontrado na página")
        
        # Verificar se há alguma mensagem de erro ou aviso na página
        error_msgs = soup.find_all(['div', 'span'], {'class': ['error', 'warning', 'alert']})
        for msg in error_msgs:
            if msg.text.strip():
                logger.warning(f"Mensagem encontrada na página: {msg.text.strip()}")
        
        return results
    
    def _parse_table_results(self, result_table):
        """
        Analisa resultados em formato de tabela
        
        Args:
            result_table (BeautifulSoup): Elemento da tabela de resultados
            
        Returns:
            list: Lista de dicionários com os resultados
        """
        results = []
        
        # Extrair cabeçalhos
        headers = []
        header_row = result_table.find('tr', {'class': 'GridHeader'})
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all('th')]
            logger.info(f"Cabeçalhos encontrados: {headers}")
        else:
            # Tentar encontrar qualquer linha de cabeçalho
            header_row = result_table.find('tr')
            if header_row:
                headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
                logger.info(f"Cabeçalhos alternativos encontrados: {headers}")
        
        if not headers:
            logger.error("Não foi possível encontrar cabeçalhos na tabela de resultados")
            return results
        
        # Extrair linhas de dados
        data_rows = result_table.find_all('tr', {'class': ['GridRow', 'GridAlternateRow']})
        if not data_rows:
            # Tentar encontrar qualquer linha que não seja de cabeçalho
            all_rows = result_table.find_all('tr')
            if len(all_rows) > 1:  # Se houver mais de uma linha (a primeira seria o cabeçalho)
                data_rows = all_rows[1:]  # Pegar todas as linhas exceto a primeira
                logger.info(f"Usando método alternativo para encontrar linhas de dados. Encontradas: {len(data_rows)}")
        
        logger.info(f"Total de linhas de dados encontradas: {len(data_rows)}")
        
        for row in data_rows:
            cells = row.find_all('td')
            if len(cells) >= len(headers):
                result = {}
                for i, header in enumerate(headers):
                    result[header] = cells[i].text.strip()
                    
                    # Verificar se há links para documentos
                    links = cells[i].find_all('a')
                    if links:
                        result[f"{header}_links"] = []
                        for link in links:
                            href = link.get('href', '')
                            if href:
                                result[f"{header}_links"].append(urljoin(self.base_url, href))
                
                results.append(result)
            else:
                logger.warning(f"Linha com número incorreto de células: {len(cells)} (esperado: {len(headers)})")
        
        return results
    
    def _parse_div_results(self, results_div):
        """
        Analisa resultados em formato de divs
        
        Args:
            results_div (BeautifulSoup): Elemento div contendo os resultados
            
        Returns:
            list: Lista de dicionários com os resultados
        """
        results = []
        
        # Procurar por divs de resultados individuais
        result_items = results_div.find_all('div', {'class': 'resultadocdital'})
        if not result_items:
            # Tentar encontrar qualquer div que possa conter resultados
            result_items = results_div.find_all('div')
        
        logger.info(f"Total de divs de resultados encontrados: {len(result_items)}")
        
        for item in result_items:
            result = {}
            
            # Método 1: Tentar extrair informações por IDs específicos
            # Processo
            processo_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblProcesso.*')})
            if processo_elem:
                result['Processo'] = processo_elem.text.strip()
            
            # Tribunal
            tribunal_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblTribunal.*')})
            if tribunal_elem:
                result['Tribunal'] = tribunal_elem.text.strip()
            
            # Data
            data_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblData.*')})
            if data_elem:
                result['Data'] = data_elem.text.strip()
            
            # Interveniente
            interv_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblInterveniente.*')})
            if interv_elem:
                result['Interveniente'] = interv_elem.text.strip()
            
            # NIF/NIPC
            nif_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblNIF.*')})
            if nif_elem:
                result['NIF/NIPC'] = nif_elem.text.strip()
            
            # Descrição/Texto
            desc_elem = item.find(['span', 'div'], {'id': re.compile(r'.*lblDescricao.*|.*lblTexto.*')})
            if desc_elem:
                result['Descrição'] = desc_elem.text.strip()
            
            # Método 2: Extrair por tags strong (para casos como o NIF 515755230)
            if not result or len(result) < 2:  # Se não encontrou campos ou encontrou poucos
                # Extrair pares de strong:texto
                strong_tags = item.find_all('strong')
                for tag in strong_tags:
                    field_name = tag.text.strip().rstrip(':')
                    # Pegar o texto após a tag strong até o próximo br
                    next_node = tag.next_sibling
                    field_value = ""
                    while next_node and not (hasattr(next_node, 'name') and next_node.name == 'br'):
                        if isinstance(next_node, str):
                            field_value += next_node
                        next_node = next_node.next_sibling if hasattr(next_node, 'next_sibling') else None
                    
                    result[field_name] = field_value.strip()
            
            # Verificar se há links para documentos
            links = item.find_all('a')
            if links:
                result['Links'] = []
                for link in links:
                    href = link.get('href', '')
                    if href:
                        result['Links'].append(urljoin(self.base_url, href))
            
            # Método 3: Se não encontrou nenhum campo específico, tentar extrair todo o texto
            if not result:
                all_text = item.get_text(separator=' ', strip=True)
                if all_text:
                    result['Conteúdo'] = all_text
            
            # Extrair todos os credores
            credores = []
            # Encontrar todos os spans que contêm credores
            spans = item.find_all('span')
            for span in spans:
                span_text = span.get_text(strip=True)
                # Verificar se o span contém informações de credor
                credor_match = re.search(r'Credor:\s*(.*?)(?:\s*NIF/NIPC:\s*(.*?))?$', span_text)
                if credor_match:
                    credor_nome = credor_match.group(1).strip() if credor_match.group(1) else ""
                    credor_nif = credor_match.group(2).strip() if credor_match.group(2) else ""
                    
                    if credor_nome:
                        credor_info = {"Nome": credor_nome}
                        if credor_nif:
                            credor_info["NIF/NIPC"] = credor_nif
                        credores.append(credor_info)
            
            # Adicionar lista de credores ao resultado
            if credores:
                result['Credores'] = credores
                # Adicionar o primeiro credor como campo separado para compatibilidade
                result['Credor'] = credores[0]['Nome']
                if 'NIF/NIPC' in credores[0]:
                    result['Credor NIF/NIPC'] = credores[0]['NIF/NIPC']
            
            # Só adicionar se tiver algum conteúdo
            if result:
                results.append(result)
        
        return results
    
    def _parse_list_results(self, results_list):
        """
        Analisa resultados em formato de lista (span/dl)
        
        Args:
            results_list (BeautifulSoup): Elemento span contendo a lista de resultados
            
        Returns:
            list: Lista de dicionários com os resultados
        """
        results = []
        
        # Procurar por itens de lista
        list_items = results_list.find_all('span', recursive=False)
        logger.info(f"Total de itens de lista encontrados: {len(list_items)}")
        
        for item in list_items:
            result = {}
            
            # Procurar por divs de resultado dentro do item
            result_div = item.find('div', {'class': 'resultadocdital'})
            if result_div:
                # Método 1: Extrair informações por IDs específicos
                # Processo
                processo_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblProcesso.*')})
                if processo_elem:
                    result['Processo'] = processo_elem.text.strip()
                
                # Tribunal
                tribunal_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblTribunal.*')})
                if tribunal_elem:
                    result['Tribunal'] = tribunal_elem.text.strip()
                
                # Data
                data_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblData.*')})
                if data_elem:
                    result['Data'] = data_elem.text.strip()
                
                # Interveniente
                interv_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblInterveniente.*')})
                if interv_elem:
                    result['Interveniente'] = interv_elem.text.strip()
                
                # NIF/NIPC
                nif_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblNIF.*')})
                if nif_elem:
                    result['NIF/NIPC'] = nif_elem.text.strip()
                
                # Descrição/Texto
                desc_elem = result_div.find(['span', 'div'], {'id': re.compile(r'.*lblDescricao.*|.*lblTexto.*')})
                if desc_elem:
                    result['Descrição'] = desc_elem.text.strip()
                
                # Método 2: Extrair por tags strong (para casos como o NIF 515755230)
                if not result or len(result) < 2:  # Se não encontrou campos ou encontrou poucos
                    # Extrair pares de strong:texto
                    strong_tags = result_div.find_all('strong')
                    for tag in strong_tags:
                        field_name = tag.text.strip().rstrip(':')
                        # Pegar o texto após a tag strong até o próximo br
                        next_node = tag.next_sibling
                        field_value = ""
                        while next_node and not (hasattr(next_node, 'name') and next_node.name == 'br'):
                            if isinstance(next_node, str):
                                field_value += next_node
                            next_node = next_node.next_sibling if hasattr(next_node, 'next_sibling') else None
                        
                        result[field_name] = field_value.strip()
                
                # Verificar se há links para documentos
                links = result_div.find_all('a')
                if links:
                    result['Links'] = []
                    for link in links:
                        href = link.get('href', '')
                        if href:
                            result['Links'].append(urljoin(self.base_url, href))
                
                # Método 3: Se não encontrou nenhum campo específico, tentar extrair todo o texto
                if not result:
                    all_text = result_div.get_text(separator=' ', strip=True)
                    if all_text:
                        result['Conteúdo'] = all_text
                
                # Extrair todos os credores
                credores = []
                # Encontrar todos os spans dentro do item
                spans = item.find_all('span')
                for span in spans:
                    span_text = span.get_text(strip=True)
                    # Verificar se o span contém informações de credor
                    if "Credor:" in span_text:
                        credor_match = re.search(r'Credor:\s*(.*?)(?:\s*NIF/NIPC:\s*(.*?))?$', span_text)
                        if credor_match:
                            credor_nome = credor_match.group(1).strip() if credor_match.group(1) else ""
                            credor_nif = credor_match.group(2).strip() if credor_match.group(2) else ""
                            
                            if credor_nome:
                                credor_info = {"Nome": credor_nome}
                                if credor_nif:
                                    credor_info["NIF/NIPC"] = credor_nif
                                credores.append(credor_info)
                
                # Adicionar lista de credores ao resultado
                if credores:
                    result['Credores'] = credores
                    # Adicionar o primeiro credor como campo separado para compatibilidade
                    result['Credor'] = credores[0]['Nome']
                    if 'NIF/NIPC' in credores[0]:
                        result['Credor NIF/NIPC'] = credores[0]['NIF/NIPC']
                
                # Só adicionar se tiver algum conteúdo
                if result:
                    results.append(result)
            
            # Se não encontrou div de resultado, tentar extrair informações diretamente do item
            elif not result_div:
                # Extrair todo o texto do item
                all_text = item.get_text(separator=' ', strip=True)
                if all_text and len(all_text) > 10:  # Ignorar itens muito pequenos
                    result['Conteúdo'] = all_text
                    
                    # Verificar se há links
                    links = item.find_all('a')
                    if links:
                        result['Links'] = []
                        for link in links:
                            href = link.get('href', '')
                            if href:
                                result['Links'].append(urljoin(self.base_url, href))
                    
                    # Só adicionar se tiver algum conteúdo
                    if result:
                        results.append(result)
        
        return results
    
    def _parse_text_results(self, parent_div):
        """
        Analisa resultados em formato de texto simples
        
        Args:
            parent_div (BeautifulSoup): Elemento div contendo os resultados em texto
            
        Returns:
            list: Lista de dicionários com os resultados
        """
        results = []
        
        # Procurar por texto que indica o número de documentos encontrados
        docs_found_text = parent_div.find(string=re.compile(r'\d+\s+documentos\s+encontrados'))
        if docs_found_text:
            logger.info(f"Texto de documentos encontrados: {docs_found_text.strip()}")
        
        # Procurar por todos os processos na página
        # Cada processo geralmente começa com "Tribunal:" e termina antes do próximo "Tribunal:"
        text_content = parent_div.get_text()
        
        # Dividir o texto em processos individuais
        process_sections = re.split(r'(?=Tribunal:)', text_content)
        
        # Remover a primeira seção se não contiver informações de processo
        if process_sections and not re.search(r'Tribunal:', process_sections[0]):
            process_sections = process_sections[1:]
        
        logger.info(f"Total de seções de processo encontradas: {len(process_sections)}")
        
        for section in process_sections:
            if not section.strip():
                continue
                
            # Criar um novo resultado para este processo
            result = {}
            
            # Extrair campos comuns usando expressões regulares
            tribunal_match = re.search(r'Tribunal:\s*([^\n]+)', section)
            if tribunal_match:
                result['Tribunal'] = tribunal_match.group(1).strip()
            
            ato_match = re.search(r'Ato:\s*([^\n]+)', section)
            if ato_match:
                result['Ato'] = ato_match.group(1).strip()
            
            referencia_match = re.search(r'Referência:\s*([^\n]+)', section)
            if referencia_match:
                result['Referência'] = referencia_match.group(1).strip()
            
            processo_match = re.search(r'Processo:\s*([^\n]+)', section)
            if processo_match:
                result['Processo'] = processo_match.group(1).strip()
            
            especie_match = re.search(r'Espécie:\s*([^\n]+)', section)
            if especie_match:
                result['Espécie'] = especie_match.group(1).strip()
            
            data_match = re.search(r'Data:\s*([^\n]+)', section)
            if data_match:
                result['Data'] = data_match.group(1).strip()
            
            data_propositura_match = re.search(r'Data da propositura da ação:\s*([^\n]+)', section)
            if data_propositura_match:
                result['Data da propositura da ação'] = data_propositura_match.group(1).strip()
            
            # Extrair informações do insolvente
            insolvente_match = re.search(r'Insolvente:\s*([^\n]+)', section)
            if insolvente_match:
                result['Insolvente'] = insolvente_match.group(1).strip()
            
            insolvente_nif_match = re.search(r'Insolvente:.*?NIF/NIPC:\s*([^\n]+)', section, re.DOTALL)
            if insolvente_nif_match:
                result['NIF/NIPC'] = insolvente_nif_match.group(1).strip()
            
            # Extrair informações do administrador de insolvência
            admin_match = re.search(r'Administrador Insolvência:\s*([^\n]+)', section)
            if admin_match:
                result['Administrador Insolvência'] = admin_match.group(1).strip()
            
            admin_nif_match = re.search(r'Administrador Insolvência:.*?NIF/NIPC:\s*([^\n]+)', section, re.DOTALL)
            if admin_nif_match:
                result['Administrador NIF/NIPC'] = admin_nif_match.group(1).strip()
            
            # Extrair todos os credores
            credores = []
            credor_matches = re.finditer(r'Credor:\s*([^\n]+)(?:\s*NIF/NIPC:\s*([^\n]+))?', section)
            
            for match in credor_matches:
                credor_nome = match.group(1).strip() if match.group(1) else ""
                credor_nif = match.group(2).strip() if match.group(2) else ""
                
                if credor_nome:
                    credor_info = {"Nome": credor_nome}
                    if credor_nif:
                        credor_info["NIF/NIPC"] = credor_nif
                    credores.append(credor_info)
            
            # Adicionar lista de credores ao resultado
            if credores:
                result['Credores'] = credores
                # Adicionar o primeiro credor como campo separado para compatibilidade
                result['Credor'] = credores[0]['Nome']
                if 'NIF/NIPC' in credores[0]:
                    result['Credor NIF/NIPC'] = credores[0]['NIF/NIPC']
            
            # Só adicionar se tiver algum conteúdo
            if result:
                results.append(result)
        
        return results
    
    def save_to_csv(self, results, output_file):
        """
        Salva os resultados em um arquivo CSV
        
        Args:
            results (list): Lista de resultados
            output_file (str): Caminho do arquivo de saída
        """
        if not results:
            logger.warning("Nenhum resultado para salvar.")
            return
        
        try:
            # Processar os resultados para lidar com campos complexos como listas de credores
            processed_results = []
            
            for result in results:
                processed_result = result.copy()
                
                # Se houver uma lista de credores, converter para formato JSON para o CSV
                if 'Credores' in processed_result:
                    processed_result['Credores_JSON'] = json.dumps(processed_result['Credores'], ensure_ascii=False)
                    del processed_result['Credores']
                
                # Se houver uma lista de links, converter para formato JSON para o CSV
                if 'Links' in processed_result and isinstance(processed_result['Links'], list):
                    processed_result['Links'] = json.dumps(processed_result['Links'], ensure_ascii=False)
                
                processed_results.append(processed_result)
            
            # Obter todos os cabeçalhos únicos
            headers = set()
            for result in processed_results:
                headers.update(result.keys())
            
            headers = sorted(list(headers))
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(processed_results)
                
            logger.info(f"Resultados salvos em {output_file}")
            
            # Salvar também um arquivo JSON para preservar a estrutura completa
            json_output_file = output_file.replace('.csv', '.json')
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Resultados completos salvos em {json_output_file}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")

def format_date(date_str):
    """
    Converte uma data no formato YYYY-MM-DD para DD-MM-YYYY
    
    Args:
        date_str (str): Data no formato YYYY-MM-DD
        
    Returns:
        str: Data no formato DD-MM-YYYY
    """
    if not date_str:
        return None
    
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d-%m-%Y')
    except ValueError:
        return date_str

def print_manual():
    """
    Exibe o manual de utilização do script
    """
    manual = """
NOME
    citius_scraper.py - Web scraping do Portal Citius

SINOPSE
    citius_scraper.py [OPÇÕES]

DESCRIÇÃO
    Ferramenta para extrair informações do Portal Citius (https://www.citius.mj.pt/portal/consultas/consultascire.aspx),
    permitindo pesquisas por NIF/NIPC ou designação com intervalo de datas.

OPÇÕES
    --nif NIF
        NIF/NIPC para pesquisa. Deve ser fornecido se --designacao não for usado.

    --designacao DESIGNACAO
        Designação para pesquisa. Deve ser fornecido se --nif não for usado.

    --data-inicio DATA_INICIO
        Data de início no formato YYYY-MM-DD.

    --data-fim DATA_FIM
        Data de fim no formato YYYY-MM-DD.

    --tribunal {nova,extintos}
        Tipo de tribunal (nova estrutura ou extintos).

    --grupo-actos GRUPO_ACTOS
        ID do grupo de actos.

    --acto ACTO
        ID do acto específico.

    --output OUTPUT
        Arquivo de saída (CSV). Por padrão: resultados_citius.csv.

    --debug
        Ativar modo de debug com mais logs.

    --man
        Exibe este manual de utilização.

    -h, --help
        Exibe a ajuda resumida.

EXEMPLOS
    Pesquisa por NIF:
        python citius_scraper.py --nif 515755230 --output resultados.csv

    Pesquisa por designação:
        python citius_scraper.py --designacao "Nome da Empresa" --output resultados.csv

    Filtrar por intervalo de datas:
        python citius_scraper.py --nif 515755230 --data-inicio 2023-01-01 --data-fim 2023-12-31 --output resultados.csv

    Ativar modo de debug:
        python citius_scraper.py --nif 515755230 --debug --output resultados.csv

ARQUIVOS
    resultados_citius.csv
        Arquivo CSV padrão para saída dos resultados.

    resultados_citius.json
        Arquivo JSON gerado automaticamente com a estrutura completa dos resultados.

    citius_scraper.log
        Arquivo de log gerado durante a execução.

    debug_form_page.html, debug_results_page.html
        Arquivos HTML salvos no modo de debug para análise.

NOTAS
    - O script sempre usa a opção "Todos" para o filtro de dias, garantindo que todos os resultados sejam encontrados.
    - Os resultados são exportados em dois formatos: CSV e JSON.
    - O formato JSON preserva a estrutura completa dos dados, incluindo listas de credores.

AUTOR
    Desenvolvido para extração de dados do Portal Citius.

BUGS
    Nenhum bug conhecido. Reporte problemas em https://github.com/Raam977/citius-scraper/issues
"""
    print(manual)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Web scraping do Portal Citius',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  Pesquisa por NIF:
    python %(prog)s --nif 515755230 --output resultados.csv

  Pesquisa por designação:
    python %(prog)s --designacao "Nome da Empresa" --output resultados.csv

  Filtrar por intervalo de datas:
    python %(prog)s --nif 515755230 --data-inicio 2023-01-01 --data-fim 2023-12-31 --output resultados.csv

  Ativar modo de debug:
    python %(prog)s --nif 515755230 --debug --output resultados.csv

  Exibir manual completo:
    python %(prog)s --man
"""
    )
    
    # Verificar se --man foi passado
    if '--man' in sys.argv:
        print_manual()
        return
    
    # Grupo de argumentos mutuamente exclusivos para NIF ou designação
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--nif', help='NIF/NIPC para pesquisa')
    group.add_argument('--designacao', help='Designação para pesquisa')
    group.add_argument('--man', action='store_true', help='Exibe o manual de utilização completo')
    
    # Argumentos para datas
    parser.add_argument('--data-inicio', help='Data de início no formato YYYY-MM-DD')
    parser.add_argument('--data-fim', help='Data de fim no formato YYYY-MM-DD')
    
    # Argumentos para filtros adicionais
    parser.add_argument('--tribunal', choices=['nova', 'extintos'], help='Tipo de tribunal (nova estrutura ou extintos)')
    parser.add_argument('--grupo-actos', help='ID do grupo de actos')
    parser.add_argument('--acto', help='ID do acto específico')
    
    # Argumento para arquivo de saída
    parser.add_argument('--output', default='resultados_citius.csv', help='Arquivo de saída (CSV)')
    
    # Argumento para modo debug
    parser.add_argument('--debug', action='store_true', help='Ativar modo de debug com mais logs')
    
    args = parser.parse_args()
    
    # Formatar datas
    data_inicio = format_date(args.data_inicio)
    data_fim = format_date(args.data_fim)
    
    # Inicializar o scraper
    scraper = CitiusScraper(debug=args.debug)
    
    # Realizar a pesquisa
    results = scraper.search(
        nif=args.nif,
        designacao=args.designacao,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tribunal=args.tribunal,
        grupo_actos=args.grupo_actos,
        acto=args.acto,
        dias='todos'  # Sempre usar 'todos'
    )
    
    # Salvar resultados
    scraper.save_to_csv(results, args.output)
    
    logger.info(f"Total de resultados encontrados: {len(results)}")

if __name__ == "__main__":
    import sys
    main()
