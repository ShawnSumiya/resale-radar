"""
Yahoo!オークション用スクレイパー
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re
from urllib.parse import quote
from base_scraper import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class YahooScraper(BaseScraper):
    """Yahoo!オークションのスクレイパー実装"""
    
    BASE_URL = "https://auctions.yahoo.co.jp"
    SEARCH_URL = "https://auctions.yahoo.co.jp/search/search"
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        super().__init__('yahoo', config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        キーワードでYahoo!オークションを検索
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            商品情報のリスト
        """
        try:
            # 検索URLを生成
            params = {
                'va': keyword,  # 検索キーワード
                'exflg': 1,     # 詳細検索フラグ
                'b': 1,         # 開始位置
                'n': 50         # 取得件数
            }
            
            logger.debug(f"Yahoo検索URL: {self.SEARCH_URL}?va={quote(keyword)}")
            
            response = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            # HTML解析
            items = self.parse(response.text)
            logger.info(f"Yahoo検索結果: {len(items)}件（キーワード: {keyword}）")
            
            return items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yahoo検索リクエストエラー: {e}")
            return []
        except Exception as e:
            logger.error(f"Yahoo検索処理エラー: {e}", exc_info=True)
            return []
    
    def parse(self, html: str) -> List[Dict[str, Any]]:
        """
        Yahoo!オークションのHTMLを解析して商品情報を抽出
        
        Args:
            html: HTML文字列
            
        Returns:
            商品情報のリスト
        """
        items = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 商品リストの取得（YahooオークションのHTML構造に基づく）
            # 注意: YahooオークションのHTML構造は変更される可能性があるため、
            # 実際のサイト構造に合わせて調整が必要
            product_list = soup.find_all('li', class_='Product')
            
            if not product_list:
                # 別のセレクタを試す
                product_list = soup.find_all('div', class_='Product')
            
            for product in product_list:
                try:
                    item = self._extract_item_info(product)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.debug(f"商品情報抽出エラー: {e}")
                    continue
            
            # 商品が見つからない場合、より汎用的な方法を試す
            if not items:
                items = self._parse_alternative(html)
            
        except Exception as e:
            logger.error(f"HTML解析エラー: {e}", exc_info=True)
        
        return items
    
    def _extract_item_info(self, product_element) -> Dict[str, Any]:
        """
        商品要素から情報を抽出
        
        Args:
            product_element: BeautifulSoup要素
            
        Returns:
            商品情報辞書
        """
        item = {}
        
        # タイトル取得
        title_elem = product_element.find('a', class_='Product__titleLink')
        if not title_elem:
            title_elem = product_element.find('h3')
        if title_elem:
            item['title'] = title_elem.get_text(strip=True)
            # URL取得
            href = title_elem.get('href', '')
            if href:
                if href.startswith('/'):
                    item['url'] = self.BASE_URL + href
                else:
                    item['url'] = href
        
        # 価格取得
        price_elem = product_element.find('span', class_='Product__priceValue')
        if not price_elem:
            price_elem = product_element.find('span', string=re.compile(r'¥|円'))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price = self._parse_price(price_text)
            item['price'] = price
        
        # 商品ID取得（URLから抽出）
        if 'url' in item:
            item_id = self._extract_item_id_from_url(item['url'])
            if item_id:
                item['item_id'] = item_id
        
        return item if item.get('title') and item.get('url') else None
    
    def _parse_alternative(self, html: str) -> List[Dict[str, Any]]:
        """
        代替パース方法（HTML構造が異なる場合のフォールバック）
        
        Args:
            html: HTML文字列
            
        Returns:
            商品情報のリスト
        """
        items = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # リンクから商品を探す
            links = soup.find_all('a', href=re.compile(r'/jp/auction/'))
            
            for link in links[:50]:  # 最大50件
                try:
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    url = self.BASE_URL + href if href.startswith('/') else href
                    item_id = self._extract_item_id_from_url(url)
                    
                    # 価格を探す（親要素周辺から）
                    parent = link.find_parent()
                    price = 0
                    if parent:
                        price_elem = parent.find(string=re.compile(r'¥\d+'))
                        if price_elem:
                            price = self._parse_price(price_elem)
                    
                    items.append({
                        'title': title,
                        'url': url,
                        'price': price,
                        'item_id': item_id
                    })
                except Exception as e:
                    logger.debug(f"代替パースエラー: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"代替パース処理エラー: {e}")
        
        return items
    
    def _parse_price(self, price_text: str) -> int:
        """
        価格文字列を整数に変換
        
        Args:
            price_text: 価格文字列（例: "¥1,000"）
            
        Returns:
            価格（整数）
        """
        try:
            # 数字以外を除去
            numbers = re.sub(r'[^\d]', '', price_text)
            return int(numbers) if numbers else 0
        except:
            return 0
    
    def _extract_item_id_from_url(self, url: str) -> str:
        """
        URLから商品IDを抽出
        
        Args:
            url: 商品URL
            
        Returns:
            商品ID（文字列）
        """
        try:
            # YahooオークションのURL形式: /jp/auction/{item_id}
            match = re.search(r'/auction/([a-z0-9]+)', url)
            if match:
                return match.group(1)
        except:
            pass
        return ''
    
    def get_item_id(self, item: Dict[str, Any]) -> str:
        """
        商品IDを取得
        
        Args:
            item: 商品情報辞書
            
        Returns:
            商品ID
        """
        return item.get('item_id', '') or self._extract_item_id_from_url(item.get('url', ''))
    
    def get_price(self, item: Dict[str, Any]) -> int:
        """
        商品の価格を取得
        
        Args:
            item: 商品情報辞書
            
        Returns:
            価格（整数）
        """
        return item.get('price', 0)

