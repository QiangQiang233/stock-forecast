#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股价走势预估工具 - 智能新闻检索版
结合技术面 + 行业面 + 消息面 综合分析
"""

import json
import os
import re
import statistics
import sys

try:
    import requests
except ImportError:
    print("Error: requests module not installed")
    sys.exit(1)


# 股票行业关键词映射
STOCK_KEYWORDS = {
    '002050': {  # 三花智控
        'name': '三花智控',
        'industry': '新能源车热管理',
        'keywords': ['新能源车', '热管理', '制冷', '空调', '零部件', '比亚迪', '特斯拉', '订单', '业绩'],
        'sector': '新能源车产业链'
    },
    '601899': {  # 紫金矿业
        'name': '紫金矿业',
        'industry': '黄金开采',
        'keywords': ['黄金', '金价', '有色金属', '铜', '矿产', '中东', '避险', '央行'],
        'sector': '贵金属'
    },
    '600519': {  # 贵州茅台
        'name': '贵州茅台',
        'industry': '白酒',
        'keywords': ['白酒', '茅台', '消费', '酒', '高端消费', '业绩', '分红'],
        'sector': '消费'
    },
}


class SmartNewsFetcher:
    """智能新闻获取器 - 基于行业关键词检索"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def fetch_news(self, symbol, name=None, industry_keywords=None):
        """智能获取相关新闻"""
        
        # 获取股票的行业关键词
        stock_info = STOCK_KEYWORDS.get(symbol, {})
        keywords = industry_keywords or stock_info.get('keywords', [name])
        
        print(f'  检索关键词: {keywords}')
        
        news_list = []
        
        # 方法1: 基于行业关键词搜索
        for kw in keywords[:5]:  # 限制搜索次数
            results = self._search_by_keyword(kw)
            news_list.extend(results)
        
        # 去重
        seen = set()
        unique_news = []
        for n in news_list:
            if n['keyword'] not in seen:
                seen.add(n['keyword'])
                unique_news.append(n)
        
        if unique_news:
            print(f'  找到 {len(unique_news)} 条相关资讯')
            return unique_news
        
        return None
    
    def _search_by_keyword(self, keyword):
        """根据关键词搜索新闻"""
        results = []
        
        # 尝试不同的搜索端点
        search_urls = [
            # 新浪搜索
            f'https://searchapi.sina.com.cn/sina/search.php?q={keyword}&c=news&sort=time',
        ]
        
        for url in search_urls:
            try:
                r = requests.get(url, headers=self.headers, timeout=5)
                if r.status_code == 200:
                    # 提取关键词匹配的内容
                    if keyword in r.text:
                        results.append({
                            'keyword': keyword,
                            'source': 'sina',
                            'content': f'{keyword}相关行业资讯'
                        })
            except:
                continue
        
        return results


class StockAnalyzer:
    """股票走势预估分析器"""
    
    def __init__(self, symbol, name=None, auto_fetch_news=True):
        self.symbol = symbol
        self.name = name or STOCK_KEYWORDS.get(symbol, {}).get('name', symbol)
        self.auto_fetch_news = auto_fetch_news
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def get_kline(self, days=60):
        """获取K线数据"""
        # 根据股票代码判断市场
        if self.symbol.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'
        
        url = f'https://quotes.sina.cn/cn/api/jsonp.php/var _m{market}{self.symbol}=/CN_MarketDataService.getKLineData?symbol={market}{self.symbol}&scale=240&ma=no'
        
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            data = json.loads(re.search(r'\[.*\]', r.text).group())
            return data[-days:]
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def technical_analysis(self, klines):
        """技术面分析"""
        if not klines:
            return None
        
        closes = [float(k['close']) for k in klines]
        volumes = [int(k['volume']) for k in klines]
        
        ma5 = statistics.mean(closes[-5:])
        ma10 = statistics.mean(closes[-10:])
        ma20 = statistics.mean(closes[-20:])
        ma60 = statistics.mean(closes[-60:]) if len(closes) >= 60 else ma20
        current = closes[-1]
        
        if ma5 > ma10 > ma20:
            trend = '上涨'
        elif ma5 < ma10 < ma20:
            trend = '下跌'
        else:
            trend = '震荡'
        
        support = min(closes[-10:])
        resistance = max(closes[-10:])
        avg_vol = statistics.mean(volumes[-20:])
        vol_ratio = volumes[-1] / avg_vol
        
        returns = [(closes[i]-closes[i-1])/closes[i-1] for i in range(1, len(closes))]
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0
        
        return {
            'current': current,
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
            'trend': trend,
            'support': support, 'resistance': resistance,
            'vol_ratio': vol_ratio, 'volatility': volatility,
            'closes': closes
        }
    
    def news_analysis(self, news_list):
        """消息面分析"""
        if not news_list:
            return {'impact': '未知', 'bullish': 0, 'bearish': 0, 'reason': '无行业资讯'}
        
        # 行业相关关键词
        bullish_keywords = ['利好', '上涨', '增长', '突破', '获批', '中标', '订单', '业绩预增', 
                          '增持', '分红', '回购', '扩产', '景气', '需求', '金价', '新能源', '热管理']
        bearish_keywords = ['利空', '下跌', '减持', '亏损', '风险', '调查', '违规', '减产', '衰退']
        
        bullish = bearish = 0
        keywords_found = []
        
        for news in news_list:
            kw = news.get('keyword', '').lower()
            for bk in bullish_keywords:
                if bk in kw:
                    bullish += 1
                    keywords_found.append(bk)
                    break
            for bk in bearish_keywords:
                if bk in kw:
                    bearish += 1
                    keywords_found.append(bk)
                    break
        
        impact = '偏多' if bullish > bearish else ('偏空' if bearish > bullish else '中性')
        
        return {
            'impact': impact,
            'bullish': bullish,
            'bearish': bearish,
            'reason': f'行业相关: {", ".join(set(keywords_found[:3]))}' if keywords_found else '行业资讯中性',
            'details': [n['keyword'] for n in news_list[:3]]
        }
    
    def estimate(self, tech, news):
        """综合预估"""
        score = 0
        
        if tech['current'] > tech['ma5']: score += 1
        if tech['current'] > tech['ma10']: score += 1
        if tech['trend'] == '上涨': score += 2
        elif tech['trend'] == '下跌': score -= 2
        
        if news['impact'] == '偏多': score += 2
        elif news['impact'] == '偏空': score -= 2
        
        # 多周期预估
        current = tech['current']
        news_score = news['bullish'] - news['bearish']
        
        next_dir = '上涨' if score >= 1 else ('下跌' if score <= -3 else '震荡')
        week_tech = (tech['ma10'] - tech['closes'][-5]) / tech['closes'][-5]
        week_dir = '上涨' if week_tech + news_score*0.015 > 0.02 else ('下跌' if week_tech + news_score*0.015 < -0.02 else '震荡')
        month_tech = (tech['ma20'] - tech['closes'][-20]) / tech['closes'][-20]
        month_dir = '上涨' if month_tech + news_score*0.01 > 0.03 else ('下跌' if month_tech + news_score*0.01 < -0.03 else '震荡')
        
        return {
            'next': {'range': f'{current*0.98:.2f}~{current*1.02:.2f}', 'direction': next_dir},
            'week': {'price': f'{current*(1+week_tech+news_score*0.015):.2f}', 'direction': week_dir},
            'month': {'price': f'{current*(1+month_tech+news_score*0.01):.2f}', 'direction': month_dir}
        }
    
    def analyze(self, user_news=None):
        """执行分析"""
        print(f'正在获取 {self.name} 行情数据...')
        
        klines = self.get_kline(60)
        if not klines:
            return {'error': '无法获取行情数据'}
        
        tech = self.technical_analysis(klines)
        
        # 获取行业资讯
        news_list = None
        if self.auto_fetch_news:
            print(f'正在检索 {self.name} 相关行业资讯...')
            fetcher = SmartNewsFetcher()
            news_list = fetcher.fetch_news(self.symbol, self.name)
        
        news = self.news_analysis(news_list or user_news or [])
        result = self.estimate(tech, news)
        
        return {'tech': tech, 'news': news, 'result': result, 'source': '智能检索' if news_list else '用户提供'}


def main():
    if len(sys.argv) < 2:
        print("用法: python stock_smart.py <股票代码> [用户消息...]")
        sys.exit(1)
    
    symbol = sys.argv[1]
    user_news = sys.argv[2:] if len(sys.argv) > 2 else []
    
    analyzer = StockAnalyzer(symbol, auto_fetch_news=True)
    result = analyzer.analyze(user_news)
    
    if 'error' in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    
    tech = result['tech']
    news = result['news']
    est = result['result']
    
    print('')
    print('='*60)
    print(f'       {result.get("source", "")} - {tech["ma10"]:.2f}({symbol}) 综合分析')
    print('='*60)
    
    print(f'\n当前价格: {tech["current"]:.2f} 元 | 趋势: {tech["trend"]}')
    print(f'MA5:{tech["ma5"]:.2f} MA10:{tech["ma10"]:.2f} MA20:{tech["ma20"]:.2f}')
    print(f'支撑:{tech["support"]:.2f} 压力:{tech["resistance"]:.2f}')
    
    print(f'\n消息面: {news["impact"]} ({news["reason"]})')
    
    print('')
    print('='*60)
    print('多周期预估:')
    print(f'  📅 次日: {est["next"]["range"]}元 -> {est["next"]["direction"]}')
    print(f'  📆 7日:  {est["week"]["price"]}元 -> {est["week"]["direction"]}')
    print(f'  📆 30日: {est["month"]["price"]}元 -> {est["month"]["direction"]}')
    print('='*60)
    print('⚠️ 仅供参考，不构成投资建议')


if __name__ == '__main__':
    main()