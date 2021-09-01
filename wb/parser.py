import csv
import json
import math
import os
import re

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from castom_driver.driver import Driver

from bs4 import BeautifulSoup


class SortKinds:
    priceup = 'priceup'
    pricedown = 'pricedown'
    popular = 'popular'
    rate = 'rate'
    sale = 'sale'
    newly = 'newly'


class Wildberries:
    headers = {
        'authority': 'www.wildberries.ru',
        'method': 'GET',
        'path': '/product/data?targetUrl=XS',
        'scheme': 'https',
        'accept': '* / *',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ru,en;q=0.9',
        'sec-ch-ua': '" Not;A Brand";v="99", "Yandex";v="91", "Chromium";v="91"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.786 Yowser/2.5 Safari/537.36'
    }
    search_url = 'https://www.wildberries.ru/catalog/0/search.aspx?'
    full_data = []

    def __init__(self, driver: Driver):
        self.driver = driver

    def get_search_source(self, search_text, page: int = 1, sort: str = SortKinds.priceup):
        page_flag = f'page={page}'
        sort_flag = f'sort={sort}'
        search_text = search_text.replace(' ', '+')
        search_flag = f'search={search_text}'

        search_url = self.search_url + '&'.join([page_flag, sort_flag, search_flag])
        self.driver.get(search_url)
        WebDriverWait(self.driver, 2, 0.1).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 'div[class="product-card j-card-item"]'
            ))
        )

        current_url = self.driver.current_url
        if page_flag in current_url and sort_flag in current_url:
            print('norm')
            # self.find_item_links(self.driver.page_source)
            # print(self.driver.page_source)
            # return self.driver.page_source
        else:
            print('not norm')
            search_url = self.change_url(current_url, sort_flag, page_flag, search_flag)

            self.driver.get(search_url)
            WebDriverWait(self.driver, 2, 0.1).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 'div[class="product-card j-card-item"]'
                ))
            )
        return self.driver.page_source
        # source = self.driver.page_source
        # hnp = self.has_next_page(source)
        # links = self.find_item_links(source)
        # for link in links:
        #     js = self.get_item_json(link)
        #     print(self.get_item_data(js, link))
        # if hnp and page < 3:
        #     page += 1
        #     self.search(search_text, page, sort)

    def search_by_max_items(self, search_text, start_page: int = 1, items: int = math.inf,
                            sort: str = SortKinds.priceup):
        item_count = 1
        source = self.get_search_source(search_text, start_page, sort)
        while item_count <= items:

            hnp = self.has_next_page(source)
            links = self.find_item_links(source)

            for link in links:
                js = self.get_item_json(link)
                if item_count < items:
                    data = self.get_item_data(js, link)
                    self.full_data.append(data)
                    print(data)
                    item_count += 1
                else:
                    break
            if hnp:
                if item_count < items:
                    start_page += 1
                    source = self.get_search_source(search_text, start_page, sort)
                else:
                    print(f'Поиск завершен, найдено {item_count} товаров.')
                    break
            else:
                print(f'У данного товара страниц меньше чем {items}, нашлось {item_count} товаров.')
                break

    def search_by_max_pages(self, search_text, start_page: int = 1, pages: int = math.inf,
                            sort: str = SortKinds.priceup):
        page_count = 1
        source = self.get_search_source(search_text, start_page, sort)
        while page_count <= pages:

            hnp = self.has_next_page(source)
            links = self.find_item_links(source)

            for link in links:
                js = self.get_item_json(link)
                data = self.get_item_data(js, link)

                self.full_data.append(data)
                print(data)
            if hnp:
                if page_count < pages:
                    page_count += 1
                    start_page += 1
                    source = self.get_search_source(search_text, start_page, sort)
                else:
                    print(f'Поиск завершен, найдено {page_count} страниц(ы).')
                    break
            else:
                print(f'У данного товара страниц меньше чем {pages}, нашлось {page_count} страниц(ы).')
                break

    def write_json_data(self, file_name):
        if not os.path.exists('files'):
            os.makedirs('files')
        with open(f'files/{file_name}', 'w', encoding='utf8') as file:
            json.dump(self.full_data, file, indent=4, ensure_ascii=False)

    def write_csv_data(self, file_name):
        res = []
        names = ['item_url', 'artikul', 'item_name', 'price_with_sale', 'price', 'sale_percent', 'star', 'description',
                 'comments_count', 'orders_count', 'quality_rate', 'is_sold_out', 'kit', 'brand_name', 'brand_id',
                 'brand_cod', 'brand_rating', 'has_certificate', 'brand_url', 'brand_logo_url']
        if not os.path.exists('files'):
            os.makedirs('files')
        data = self.full_data
        for d in data:
            item_data = d['item_data']
            photos = item_data.pop('photos', [])
            brand_data = d['brand_data']
            for key in brand_data:
                item_data[key] = brand_data[key]
            res.append(item_data)
        with open(f'files/{file_name}', 'w', encoding='utf8') as file:
            file_writer = csv.DictWriter(file, delimiter=",",
                                         lineterminator="\r", fieldnames=names)
            file_writer.writeheader()
            file_writer.writerows(res)

    @staticmethod
    def has_next_page(html):
        source = BeautifulSoup(html, 'lxml')
        link = source.find('a', class_='pagination-next')
        if link is not None:
            return True
        return False

    @staticmethod
    def change_url(current_url, sort_flag, page_flag, search_flag):
        sort_pattern = 'sort=[a-zA-Z]{2,}'
        page_pattern = 'page=\d{1,}'
        search_pattern = '&search=((\W{1,}|\w{1,}){1,}\+{0,1}){1,}'
        xsearch_pattern = '&xsearch=\w{1,}'
        xs_m = re.search(xsearch_pattern, current_url)
        if xs_m:
            current_url = current_url.replace(xs_m.group(), '')

        s_m = re.search(sort_pattern, current_url)
        p_m = re.search(page_pattern, current_url)
        ser_m = re.search(search_pattern, current_url)
        if ser_m:
            if s_m:
                current_url = current_url.replace(s_m.group(), sort_flag)
            else:
                current_url = current_url.replace(ser_m.group(), '&'.join([sort_flag, search_flag]))
            if p_m:
                current_url = current_url.replace(p_m.group(), page_flag)
            else:
                current_url = current_url.replace(ser_m.group(), '&'.join([page_flag, search_flag]))
        else:
            if '?' not in current_url:
                current_url += '?'
            if s_m:
                current_url = current_url.replace(s_m.group(), sort_flag)
            else:
                current_url += f'&{sort_flag}'
            if p_m:
                current_url = current_url.replace(p_m.group(), page_flag)
            else:
                current_url += f'&{page_flag}'
        return current_url

    @staticmethod
    def find_item_links(html):
        links = []
        soup = BeautifulSoup(html, 'lxml')
        items_block = soup.find('div', class_="product-card-list")
        items = items_block.find_all('div', class_="product-card j-card-item")
        for item in items:
            href = item.find('a').get('href')
            item_link = 'https://www.wildberries.ru' + href
            print(item_link)
            links.append(item_link)
        return links

    @staticmethod
    def get_item_json(url):
        item_id = url.split("/")[-2]
        headers = {
            # 'authority': 'www.wildberries.ru',
            # 'method': 'GET',
            # 'path': f'/{item_id}/product/data?targetUrl=XS',
            # 'scheme': 'https',
            # 'accept': '* / *',
            # 'accept-encoding': 'gzip, deflate, br',
            # 'accept-language': 'ru,en;q=0.9',
            # 'dnt': '1',
            # 'referer': url,
            # 'sec-ch-ua': '" Not;A Brand";v="99", "Yandex";v="91", "Chromium";v="91"',
            # 'sec-ch-ua-mobile': '?0',
            # 'sec-fetch-dest': 'empty',
            # 'sec-fetch-mode': 'cors',
            # 'sec-fetch-site': 'same-origin',
            # 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.786 Yowser/2.5 Safari/537.36',
            # 'x-requested-with': 'XMLHttpRequest',
            'x-spa-version': '8.0.7.1'  # позволяет получать данные
        }
        url = f'https://www.wildberries.ru/{item_id}/product/data?targetUrl=XS'
        session = requests.Session()
        response = session.get(url, headers=headers)
        return response.json()

    @staticmethod
    def get_seller_json(item_id):
        res = requests.get(f'https://wbx-content-v2.wbstatic.net/sellers/{item_id}.json?locale=ru')
        return res.json()

    @staticmethod
    def get_item_data(js: dict, url):

        result = {
            'item_data': {},
            'brand_data': {}
        }
        result['item_data']['item_url'] = url
        if js.get('value', None) is not None:
            if js['value'].get('data', None) is not None:
                data = js['value']['data']
            else:
                return result
        else:
            return result
        # try:
        #     data = js['value']['data']
        # except (KeyError, TypeError):
        #     return result

        no_data = None
        price_for_product = data['priceForProduct']
        product_card = data['productCard']
        nomenclatures = product_card.get('nomenclatures')
        selected_nomenclature = data['selectedNomenclature']
        image_helper = selected_nomenclature.get('imageHelper', no_data)

        artikul = selected_nomenclature.get('artikul', no_data)  # type: str
        result['item_data']['artikul'] = artikul

        item_name = product_card.get('goodsName', no_data)
        result['item_data']['item_name'] = item_name

        price_with_sale = price_for_product.get('priceWithSale', no_data)
        result['item_data']['price_with_sale'] = price_with_sale

        price = price_for_product.get('price', no_data)
        result['item_data']['price'] = price

        sale_percent = price_for_product.get('sale', no_data)
        result['item_data']['sale_percent'] = sale_percent

        star = product_card.get('star', no_data)
        result['item_data']['star'] = star

        description = product_card.get('description', no_data)
        result['item_data']['description'] = description

        result['item_data']['photos'] = []
        if image_helper:
            for image_info in image_helper:
                item_photo_url = 'https:' + image_info.get('preview')
                # result['item_photo_url'] = item_photo_url

                item_big_photo_url = 'https:' + image_info.get('zoom')
                # result['item_big_photo_url'] = item_big_photo_url
                result['item_data']['photos'].append(
                    {
                        'item_photo_url': item_photo_url,
                        'item_big_photo_url': item_big_photo_url
                    }
                )

        comments_count = product_card.get('commentsCount', no_data)
        result['item_data']['comments_count'] = comments_count

        orders_count = selected_nomenclature.get('ordersCount', no_data)  # количсесвто покупок
        result['item_data']['orders_count'] = orders_count

        if nomenclatures:
            id = list(nomenclatures.keys())[0]
            id_num = nomenclatures.get(id, no_data)
            sizes = id_num.get('size', no_data)
            if sizes:
                quantity = sizes[0].get('quantity', no_data)
                result['item_data']['quantity'] = quantity
        else:
            result['item_data']['quantity'] = None

        quality_rate = selected_nomenclature.get('qualityRate', no_data)
        result['item_data']['quality_rate'] = quality_rate

        is_sold_out = selected_nomenclature.get('isSoldOut', no_data)  # type: bool
        result['item_data']['is_sold_out'] = is_sold_out

        kit = product_card.get('kit', no_data)
        result['item_data']['kit'] = kit

        brand_name = product_card.get('brandName', no_data)
        result['brand_data']['brand_name'] = brand_name

        brand_id = product_card.get('brandId', no_data)
        result['brand_data']['brand_id'] = brand_id

        brand_cod = product_card.get('brandCod', no_data)
        result['brand_data']['brand_cod'] = brand_cod

        brand_rating = product_card.get('brandRating', no_data)
        result['brand_data']['brand_rating'] = brand_rating

        has_certificate = product_card.get('hasCertificate', no_data)
        result['brand_data']['has_certificate'] = has_certificate

        brand_url = 'https://www.wildberries.ru' + data.get('brandUrl', no_data)
        result['brand_data']['brand_url'] = brand_url

        brand_logo_url = 'https:' + data.get('brandLogoUrl', no_data)
        result['brand_data']['brand_logo_url'] = brand_logo_url

        return result


