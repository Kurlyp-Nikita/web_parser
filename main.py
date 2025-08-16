import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from urllib.parse import urljoin, urlparse
import os
import sys

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

    def auto_save_all(self, data, base_filename='parsed_data'):
        """Автоматическое сохранение во все форматы"""
        if not data:
            print("Нет данных для сохранения")
            return
        
        print(f"\n💾 Сохраняем {len(data)} элементов...")
        
        # Сохраняем в Excel
        if EXCEL_AVAILABLE:
            self.save_to_excel(data, f"{base_filename}.xlsx")
        
        # Сохраняем в CSV
        self.save_to_csv(data, f"{base_filename}.csv")
        
        # Сохраняем в JSON
        self.save_to_json(data, f"{base_filename}.json")
        
        print("✅ Все файлы сохранены!")


def quick_parse(url, max_pages=1, delay=1):
    """
    Быстрый парсинг сайта без лишних вопросов
    
    Args:
        url (str): URL для парсинга
        max_pages (int): Количество страниц (по умолчанию 1)
        delay (int): Задержка между запросами (по умолчанию 1 секунда)
    """
    print(f"🚀 Быстрый парсинг: {url}")
    print(f"📄 Страниц: {max_pages}, ⏱️ Задержка: {delay}с")
    
    parser = WebParser()
    data = parser.parse_website(url, max_pages=max_pages, delay=delay)
    
    if data:
        print(f"✅ Найдено {len(data)} элементов")
        
        # Автоматически сохраняем во все форматы
        base_filename = f"parsed_{urlparse(url).netloc.replace('.', '_')}"
        parser.auto_save_all(data, base_filename)
        
        # Показываем превью
        print(f"\n📋 ПРЕВЬЮ (первые 3 элемента):")
        print("-" * 50)
        for i, item in enumerate(data[:3], 1):
            print(f"Элемент {i}:")
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")
            print()
    else:
        print("❌ Данные не найдены")


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        url = sys.argv[1]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        delay = float(sys.argv[3]) if len(sys.argv) > 3 else 1
        quick_parse(url, max_pages, delay)
    else:
        # Если нет аргументов, запрашиваем URL
        url = input("Введите URL для парсинга: ").strip()
        if url:
            quick_parse(url)
        else:
            print("❌ URL не может быть пустым!")