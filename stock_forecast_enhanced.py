#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股价走势预估工具 - 增强版
结合技术面 + 消息面 + 自动获取新闻
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


class StockNewsFetcher:
    """股票新闻获取器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def fetch_news(self, symbol, name):
        """尝试获取股票相关新闻"""
        news_list = []
        
        # 方法1: 尝试从新浪财经获取
        news_list.extend(self._try_sina(symbol, name))
        
        # 方法2: 尝试从东方财富获取
        news_list.extend(self._try_eastmoney(symbol, name))
        
        # 方法3: 尝试从网易财经获取
        news_list.extend(self._try_163(symbol, name))
        
        # 去重
        seen = set()
        unique_news = []
        for n in news_list:
            if n not in seen:
                seen.add(n)
                unique_news.append(n)
        
        return unique_news if unique_news else None
    
    def _try_sina(self, symbol, name):
        """尝试新浪财经"""
        news = []
        try:
            # 尝试新浪财经股票新闻页
            url = f'https://finance.sina.com.cn/stock/{symbol}.shtml'
            r = requests.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200 and '股票' in r.text:
                # 尝试获取新闻列表
                keywords = ['业绩', '增长', '订单', '分红', '回购', '收购', '政策', '利好']
                for kw in keywords:
                    if kw in r.text:
                        news.append(f'新浪财经相关报道: {kw}')
        except:
            pass
        return news
    
    def _try_eastmoney(self, symbol, name):
        """尝试东方财富"""
        news = []
        try:
            # 尝试东方财富个股新闻
            url = f'https://guba.eastmoney.com/news,{symbol}.html'
            r = requests.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                keywords = ['业绩', '分红', '订单', '回购', '增持']
                for kw in keywords:
                    if kw in r.text:
                        news.append(f'东方财富相关报道: {kw}')
        except:
            pass
        return news
    
    def _try_163(self, symbol, name):
        """尝试网易财经"""
        news = []
        try:
            url = f'https://money.163.com/stock/{symbol}.html'
            r = requests.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                keywords = ['业绩', '增长', '订单', '分红']
                for kw in keywords:
                    if kw in r.text:
                        news.append(f'网易财经相关报道: {kw}')
        except:
            pass
        return news


class StockAnalyzer:
    """股票走势预估分析器"""
    
    def __init__(self, symbol, name, auto_fetch_news=False):
        self.symbol = symbol
        self.name = name
        self.auto_fetch_news = auto_fetch_news
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def get_kline(self, days=60):
        """获取K线数据"""
        # 根据股票代码判断市场（沪市sh，深市sz）
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
        if not klines or len(klines) == 0:
            return None
        
        closes = [float(k['close']) for k in klines]
        volumes = [int(k['volume']) for k in klines]
        
        # 计算均线
        ma5 = statistics.mean(closes[-5:]) if len(closes) >= 5 else closes[-1]
        ma10 = statistics.mean(closes[-10:]) if len(closes) >= 10 else ma5
        ma20 = statistics.mean(closes[-20:]) if len(closes) >= 20 else ma10
        ma60 = statistics.mean(closes[-60:]) if len(closes) >= 60 else ma20
        
        current = closes[-1]
        
        # 判断趋势
        if ma5 > ma10 > ma20:
            trend = '上涨'
        elif ma5 < ma10 < ma20:
            trend = '下跌'
        else:
            trend = '震荡'
        
        # 支撑压力
        support = min(closes[-10:])
        resistance = max(closes[-10:])
        
        # 成交量分析
        avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        
        # 波动率
        returns = [(closes[i]-closes[i-1])/closes[i-1] for i in range(1, len(closes))]
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0
        
        return {
            'current': current,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'trend': trend,
            'support': support,
            'resistance': resistance,
            'vol_ratio': vol_ratio,
            'volatility': volatility,
            'closes': closes
        }
    
    def news_analysis(self, news_list):
        """消息面分析"""
        if not news_list or len(news_list) == 0:
            return {'impact': '未知', 'bullish': 0, 'bearish': 0, 'reason': '无新闻信息'}
        
        # 利好关键词
        bullish_keywords = [
            '利好', '上涨', '增长', '突破', '获批', '中标', '订单', '业绩预增', 
            '增持', '分红', '回购', '扩产', '景气', '需求', '金价', '铜价',
            '新能源', '机器人', '热管理', '空调', '制冷'
        ]
        
        # 利空关键词
        bearish_keywords = [
            '利空', '下跌', '减持', '亏损', '风险', '调查', '违规', 
            '处罚', '诉讼', '事故', '减产', '衰退', '需求下降', '竞争'
        ]
        
        bullish_count = 0
        bearish_count = 0
        news_details = []
        
        for news in news_list:
            news_lower = news.lower()
            is_bullish = False
            is_bearish = False
            
            for kw in bullish_keywords:
                if kw in news_lower:
                    bullish_count += 1
                    is_bullish = True
                    break
            
            for kw in bearish_keywords:
                if kw in news_lower:
                    bearish_count += 1
                    is_bearish = True
                    break
            
            if is_bullish or is_bearish:
                news_details.append(news)
        
        if bullish_count > bearish_count:
            impact = '偏多'
        elif bearish_count > bullish_count:
            impact = '偏空'
        else:
            impact = '中性'
        
        return {
            'impact': impact,
            'bullish': bullish_count,
            'bearish': bearish_count,
            'reason': f'利好{bullish_count}条，利空{bearish_count}条',
            'details': news_details[:5] if news_details else []
        }
    
    def comprehensive_estimate(self, tech, news):
        """综合预估"""
        if not tech:
            return {'error': '无法获取股票数据'}
        
        score = 0
        
        # 技术面评分
        if tech['current'] > tech['ma5']:
            score += 1
        if tech['current'] > tech['ma10']:
            score += 1
        if tech['trend'] == '上涨':
            score += 2
        elif tech['trend'] == '下跌':
            score -= 2
        
        # 消息面评分
        if news['impact'] == '偏多':
            score += 2
        elif news['impact'] == '偏空':
            score -= 2
        
        # 生成预估
        if score >= 3:
            est_next = '上涨'
            prob_next = '70%'
        elif score >= 1:
            est_next = '震荡偏多'
            prob_next = '60%'
        elif score >= -1:
            est_next = '震荡'
            prob_next = '50%'
        elif score >= -3:
            est_next = '震荡偏空'
            prob_next = '40%'
        else:
            est_next = '下跌'
            prob_next = '30%'
        
        # 生成各周期预估
        return self._generate_multi_period_estimate(tech, news, score, prob_next)
    
    def _generate_multi_period_estimate(self, tech, news, score, prob_next='50%'):
        """生成多周期预估"""
        current = tech['current']
        closes = tech['closes']
        
        # 消息面影响系数（随时间递减）
        news_score = news['bullish'] - news['bearish']
        news_effect_next = news_score * 0.02
        news_effect_week = news_score * 0.015
        news_effect_month = news_score * 0.01
        
        # 技术面趋势
        ma10_trend = (tech['ma10'] - closes[-5]) / closes[-5]
        ma20_trend = (tech['ma20'] - closes[-20]) / closes[-20]
        
        # 次日预估
        next_tech = 0.02 if tech['trend'] == '上涨' else (-0.02 if tech['trend'] == '下跌' else 0)
        next_total = next_tech + news_effect_next
        next_price_low = current * 0.98
        next_price_high = current * 1.02
        next_dir = '上涨' if next_total > 0.01 else ('下跌' if next_total < -0.01 else '震荡')
        
        # 7日预估
        week_total = ma10_trend + news_effect_week
        week_price = current * (1 + week_total)
        week_dir = '上涨' if week_total > 0.02 else ('下跌' if week_total < -0.02 else '震荡')
        
        # 30日预估
        month_total = ma20_trend + news_effect_month
        month_price = current * (1 + month_total)
        month_dir = '上涨' if month_total > 0.03 else ('下跌' if month_total < -0.03 else '震荡')
        
        return {
            'next': {
                'price_range': f'{next_price_low:.2f}~{next_price_high:.2f}',
                'direction': next_dir,
                'probability': prob_next
            },
            'week': {
                'price': f'{week_price:.2f}',
                'direction': week_dir
            },
            'month': {
                'price': f'{month_price:.2f}',
                'direction': month_dir
            },
            'news_score': news_score
        }
    
    def analyze(self, news_from_user=None):
        """执行完整分析"""
        print(f'正在获取 {self.name} 行情数据...')
        
        klines = self.get_kline(60)
        if not klines:
            return {'error': '无法获取行情数据'}
        
        # 获取技术面
        tech = self.technical_analysis(klines)
        
        # 获取消息面
        news_list = []
        news_source = ''
        
        if news_from_user and len(news_from_user) > 0:
            news_list = news_from_user
            news_source = '用户提供'
        elif self.auto_fetch_news:
            print(f'正在尝试自动获取 {self.name} 相关新闻...')
            fetcher = StockNewsFetcher()
            fetched = fetcher.fetch_news(self.symbol, self.name)
            if fetched:
                news_list = fetched
                news_source = '自动获取'
        
        news = self.news_analysis(news_list)
        if news_source:
            news['source'] = news_source
        
        # 综合预估
        result = self.comprehensive_estimate(tech, news)
        
        return {
            'tech': tech,
            'news': news,
            'result': result
        }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python stock_forecast_enhanced.py <股票代码> [自动获取新闻] [用户新闻...]")
        print("示例: python stock_forecast_enhanced.py 601899 true 业绩预增 金价上涨")
        sys.exit(1)
    
    symbol = sys.argv[1]
    auto_fetch = len(sys.argv) > 2 and sys.argv[2].lower() == 'true'
    user_news = sys.argv[3:] if len(sys.argv) > 3 else []
    
    # 股票名称映射
    name_map = {
        '601899': '紫金矿业',
        '600519': '贵州茅台',
        '000001': '平安银行',
        '600036': '招商银行',
        '002050': '三花智控',
    }
    name = name_map.get(symbol, symbol)
    
    analyzer = StockAnalyzer(symbol, name, auto_fetch_news=auto_fetch)
    result = analyzer.analyze(user_news)
    
    if 'error' in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    
    tech = result['tech']
    news = result['news']
    est = result['result']
    
    print('')
    print('='*65)
    print(f'       {name}({symbol}) 综合分析报告')
    print('='*65)
    
    print('\n【基础信息】')
    print(f'  当前价格: {tech["current"]:.2f} 元')
    print(f'  日波动率: {tech["volatility"]*100:.2f}%')
    
    print('\n【技术面】')
    print(f'  MA5: {tech["ma5"]:.2f}  MA10: {tech["ma10"]:.2f}  MA20: {tech["ma20"]:.2f}')
    print(f'  趋势: {tech["trend"]}')
    print(f'  支撑: {tech["support"]:.2f}  压力: {tech["resistance"]:.2f}')
    print(f'  量比: {tech["vol_ratio"]:.2f}x')
    
    print('\n【消息面】')
    if news.get('source'):
        print(f'  来源: {news["source"]}')
    print(f'  方向: {news["impact"]}')
    if news['bullish'] > 0 or news['bearish'] > 0:
        print(f'  利好: {news["bullish"]}条  利空: {news["bearish"]}条')
    else:
        print(f'  ({news["reason"]})')
    
    print('')
    print('='*65)
    print('                    多周期预估结果')
    print('='*65)
    
    print(f'\n📅 次日')
    print(f'  预估区间: {est["next"]["price_range"]} 元')
    print(f'  方向: {est["next"]["direction"]}  概率: {est["next"]["probability"]}')
    
    print(f'\n📆 7日后')
    print(f'  预估价格: {est["week"]["price"]} 元')
    print(f'  方向: {est["week"]["direction"]}')
    
    print(f'\n📆 30日后')
    print(f'  预估价格: {est["month"]["price"]} 元')
    print(f'  方向: {est["month"]["direction"]}')
    
    print('')
    print('='*65)
    print('⚠️ 消息面影响随时间递减，技术面主导中长期趋势')
    print('⚠️ 此为辅助分析，仅供参考，不构成投资建议')
    print('='*65)


if __name__ == '__main__':
    main()