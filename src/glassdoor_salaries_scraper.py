import json
from typing import List

import pandas as pd
import requests as r
from bs4 import BeautifulSoup, PageElement

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 '
                  'Safari/537.36'}
companies_filename = 'companies'
delta = 20


def main() -> None:
    companies = get_companies()
    companies_jobs_infos = get_companies_jobs_infos(companies)
    generate_companies_jobs_infos_excel(companies_jobs_infos)


def get_companies() -> List[dict]:
    with open(f'{companies_filename}.json') as f:
        companies = json.load(f)

    print(f'{companies=}')
    return companies


def get_companies_jobs_infos(companies) -> List[dict]:
    companies_jobs_infos = []

    for company in companies:
        jobs_infos = get_company_jobs_infos(company)
        companies_jobs_infos += jobs_infos

    # print(f'{companies_jobs_infos=}')
    return companies_jobs_infos


def get_company_jobs_infos(company: dict) -> List[dict]:
    company_jobs_infos = []
    number_of_company_jobs_infos_pages = get_number_of_company_jobs_infos_pages(company)

    for company_jobs_infos_page in range(1, number_of_company_jobs_infos_pages + 1):
        company_jobs_infos += get_company_page_jobs_infos(company, company_jobs_infos_page)

    print(f'{company_jobs_infos=}')
    return company_jobs_infos


def get_number_of_company_jobs_infos_pages(company) -> int:
    company_glassdoor_first_page_url = get_company_glassdoor_url(company)
    company_glassdoor_first_page_content = r.get(company_glassdoor_first_page_url, headers=headers).content

    jobs_infos_number = scrape_number_of_company_jobs_infos_pages(company_glassdoor_first_page_content)
    pages_number = get_pages_number_from_jobs_infos_number(jobs_infos_number)

    return pages_number


def scrape_number_of_company_jobs_infos_pages(company_glassdoor_content: bytes) -> int:
    soup = BeautifulSoup(company_glassdoor_content, 'html.parser')
    number_of_items = int(soup.find('div', class_='paginationFooter').text.strip().split(' ')[-1])

    print(f'{number_of_items=}')
    return number_of_items


def get_pages_number_from_jobs_infos_number(jobs_infos_number: int) -> int:
    pages_number = jobs_infos_number // delta
    if jobs_infos_number % delta:
        pages_number += 1

    print(f'{pages_number=}')
    return pages_number


def get_company_page_jobs_infos(company: dict, company_jobs_infos_page: int) -> List[dict]:
    company_glassdoor_url = get_company_glassdoor_url(company, company_jobs_infos_page)
    company_glassdoor_content = r.get(company_glassdoor_url, headers=headers).content

    return scrape_company_page_jobs_infos(company_glassdoor_content)


def get_company_glassdoor_url(company: dict, page: int = 1) -> str:
    company_name = company.get('name')
    company_code = company.get('code')
    glassdoor_url = f'https://www.glassdoor.com.br/Salário/{company_name}-Salários-E{company_code}_P{page}.htm?filter' \
                    f'.payPeriod=MONTHLY'

    print(f'{glassdoor_url=}')
    return glassdoor_url


def scrape_company_page_jobs_infos(company_glassdoor_content: bytes) -> List[dict]:
    soup = BeautifulSoup(company_glassdoor_content, 'html.parser')
    company_readable_name = soup.find('p', class_='employerName').text
    jobs_infos_htmls = list(soup.find(id='SalariesRef').children)
    return list(map(lambda job_infos_html: scrape_job_infos(company_readable_name, job_infos_html), jobs_infos_htmls))


def scrape_job_infos(company_readable_name: str, job_infos_html: PageElement) -> dict:
    jobs_infos_strong_tags = job_infos_html('strong')
    filted_jobs_infos_strong_tags = list(filter(
        lambda jobs_infos_strong_tag: 'Adicione seu salário.' not in jobs_infos_strong_tag.text,
        jobs_infos_strong_tags))

    return {
        'Empresa': company_readable_name,
        'Cargo': filted_jobs_infos_strong_tags[0].text,
        **scrape_job_salary_infos(jobs_infos_strong_tags),
        'Número de salários coletados': int(filted_jobs_infos_strong_tags[-2].text.split()[0]),
    }


def scrape_job_salary_infos(jobs_infos_strong_tags: List[PageElement]) -> dict:
    currency_jobs_infos_strong_tags = list(filter(lambda jobs_infos_strong_tag: 'R$' in jobs_infos_strong_tag.text,
                                                  jobs_infos_strong_tags))
    unique_currency_jobs_infos_strong_tags = remove_currency_jobs_infos_strong_tags_duplicates(
        currency_jobs_infos_strong_tags)
    job_salary_infos_len = len(unique_currency_jobs_infos_strong_tags)
    return {
        'Pagamento total médio': unique_currency_jobs_infos_strong_tags[0].text if job_salary_infos_len > 0 else '',
        'Salário base': unique_currency_jobs_infos_strong_tags[1].text if job_salary_infos_len > 1 else '',
        'Remuneração variável': unique_currency_jobs_infos_strong_tags[2].text if job_salary_infos_len > 2 else ''
    }


def remove_currency_jobs_infos_strong_tags_duplicates(
        currency_jobs_infos_strong_tags: List[PageElement]) -> List[PageElement]:
    if len(currency_jobs_infos_strong_tags) > 3:
        return currency_jobs_infos_strong_tags[::2]
    return currency_jobs_infos_strong_tags


def generate_companies_jobs_infos_excel(companies_jobs_infos: List[dict]) -> None:
    df = pd.DataFrame(companies_jobs_infos)
    writer = pd.ExcelWriter('glassdoor_jobs_infox.xlsx', engine='xlsxwriter')

    df.to_excel(writer, sheet_name='Salários', index=False)
    writer.save()


if __name__ == 'main' or True:
    main()
