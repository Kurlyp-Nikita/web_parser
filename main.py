import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from urllib.parse import urljoin, urlparse
import os

# Проверка наличия openpyxl для работы с Excel
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("Предупреждение: openpyxl не установлен. Сохранение в Excel будет недоступно.")


class WebParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def parse_website(self, url, selectors=None, max_pages=1, delay=1):
        """
        Универсальный парсер сайтов

        Args:
            url (str): URL сайта для парсинга
            selectors (dict): CSS селекторы для извлечения данных
            max_pages (int): Максимальное количество страниц
            delay (int): Задержка между запросами в секундах
        """
        data = []

        try:
            for page in range(1, max_pages + 1):
                print(f"Парсинг страницы {page}...")

                # Формируем URL для страницы
                if page == 1:
                    current_url = url
                else:
                    # Добавляем параметр страницы (может потребоваться настройка)
                    if '?' in url:
                        current_url = f"{url}&page={page}"
                    else:
                        current_url = f"{url}?page={page}"

                # Получаем страницу
                response = self.session.get(current_url)
                response.raise_for_status()

                # Парсим HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Если селекторы не указаны, пытаемся найти общие элементы
                if not selectors:
                    items = self._auto_detect_items(soup)
                else:
                    items = soup.select(selectors.get('items', 'div'))

                for item in items:
                    item_data = {}

                    if selectors:
                        # Извлекаем данные по указанным селекторам
                        for key, selector in selectors.items():
                            if key != 'items':
                                element = item.select_one(selector)
                                if element:
                                    item_data[key] = element.get_text(strip=True)
                                    # Если есть атрибут href, сохраняем ссылку
                                    if element.get('href'):
                                        item_data[f'{key}_link'] = urljoin(url, element.get('href'))
                    else:
                        # Автоматическое извлечение данных
                        item_data = self._extract_auto_data(item)

                    if item_data:
                        data.append(item_data)

                # Задержка между запросами
                if page < max_pages:
                    time.sleep(delay)

        except Exception as e:
            print(f"Ошибка при парсинге: {e}")

        return data

    def _auto_detect_items(self, soup):
        """Автоматическое определение элементов для парсинга"""
        # Ищем общие контейнеры
        selectors = [
            'div[class*="item"]',
            'div[class*="product"]',
            'div[class*="card"]',
            'div[class*="post"]',
            'article',
            'li',
            '.item',
            '.product',
            '.card',
            '.post'
        ]

        for selector in selectors:
            items = soup.select(selector)
            if len(items) > 1:
                return items

        # Если ничего не найдено, возвращаем все div'ы
        return soup.find_all('div')[:10]

    def _extract_auto_data(self, item):
        """Автоматическое извлечение данных из элемента"""
        data = {}

        # Ищем заголовки
        title = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if title:
            data['title'] = title.get_text(strip=True)

        # Ищем ссылки
        links = item.find_all('a')
        if links:
            data['links'] = [link.get('href') for link in links if link.get('href')]

        # Ищем изображения
        images = item.find_all('img')
        if images:
            data['images'] = [img.get('src') for img in images if img.get('src')]

        # Ищем текст
        text = item.get_text(strip=True)
        if text and len(text) > 10:
            data['text'] = text[:200] + '...' if len(text) > 200 else text

        return data

    def save_to_excel(self, data, filename='parsed_data.xlsx'):
        """Сохранение данных в Excel"""
        if not EXCEL_AVAILABLE:
            print("Ошибка: openpyxl не установлен. Установите его командой: pip install openpyxl")
            return
            
        if not data:
            print("Нет данных для сохранения")
            return

        try:
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False)
            print(f"Данные сохранены в {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении в Excel: {e}")
            print("Попробуйте сохранить в CSV или JSON формат")

    def save_to_csv(self, data, filename='parsed_data.csv'):
        """Сохранение данных в CSV"""
        if not data:
            print("Нет данных для сохранения")
            return

        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Данные сохранены в {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении в CSV: {e}")

    def save_to_json(self, data, filename='parsed_data.json'):
        """Сохранение данных в JSON"""
        if not data:
            print("Нет данных для сохранения")
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Данные сохранены в {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении в JSON: {e}")


# Примеры использования
def example_parsers():
    parser = WebParser()

    # Пример 1: Парсинг новостей
    print("=== Парсинг новостей ===")
    news_data = parser.parse_website(
        url="https://news.ycombinator.com/",
        selectors={
            'items': '.athing',
            'title': '.titleline > a',
            'score': '.score',
            'author': '.hnuser'
        },
        max_pages=1
    )
    parser.save_to_excel(news_data, 'hacker_news.xlsx')

    # Пример 2: Парсинг товаров (пример)
    print("\n=== Парсинг товаров ===")
    # Замените URL на реальный сайт
    products_data = parser.parse_website(
        url="https://example.com/products",
        selectors={
            'items': '.product-item',
            'name': '.product-name',
            'price': '.product-price',
            'description': '.product-description'
        },
        max_pages=1
    )
    parser.save_to_excel(products_data, 'products.xlsx')


if __name__ == "__main__":
    # Создаем экземпляр парсера
    parser = WebParser()

    # Простой пример парсинга
    print("Введите URL сайта для парсинга (или нажмите Enter для примера):")
    url = input().strip()

    if not url:
        print("Запускаем пример парсинга...")
        example_parsers()
    else:
        print("Парсинг сайта...")
        data = parser.parse_website(url, max_pages=1)

        if data:
            parser.save_to_excel(data, 'parsed_data.xlsx')
            parser.save_to_csv(data, 'parsed_data.csv')
            print(f"Найдено {len(data)} элементов")
        else:
            print("Данные не найдены")