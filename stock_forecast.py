#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股价走势预估工具
结合技术面 + 消息面 进行综合分析
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
    print("Please install: pip install requests")
    sys.exit(1)


class StockAnalyzer:
    """股票走势预估分析器"""
    
    def __init__(self, symbol, name):
        self.symbol = symbol
        self.name = name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def get_kline(self, days=60):
        """获取K线数据"""
        url = 'https://quotes.sina.cn/cn/api/jsonp.php/var _sh{}=/CN_MarketDataService.getKLineData?symbol=sh{}&scale=240&ma=no'.format(
            self.symbol, self.symbol
        )
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
            'closes': closes
        }
    
    def news_analysis(self, news_list):
        """消息面分析"""
        if not news_list or len(news_list) == 0:
            return {'impact': '未知', 'reason': '未提供新闻信息', 'bullish': 0, 'bearish': 0}
        
        # 利好关键词
        bullish_keywords = ['利好', '上涨', '增长', '突破', '获批', '中标', '订单', '业绩预增', '增持', '分红', '回购', '扩产', '景气', '需求', '金价上涨', '铜价上涨']
        
        # 利空关键词
        bearish_keywords = ['利空', '下跌', '减持', '亏损', '风险', '调查', '违规', '处罚', '诉讼', '事故', '减产', '衰退', '需求下降']
        
        bullish_count = 0
        bearish_count = 0
        
        for news in news_list:
            news_lower = news.lower()
            for kw in bullish_keywords:
                if kw in news_lower:
                    bullish_count += 1
                    break
            for kw in bearish_keywords:
                if kw in news_lower:
                    bearish_count += 1
                    break
        
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
            'reason': '利好{}条，利空{}条'.format(bullish_count, bearish_count)
        }
    
    def comprehensive_estimate(self, tech, news):
        """综合预估"""
        if not tech:
            return {'estimate': '数据获取失败', 'probability': '-', 'reason': '无法获取股票数据'}
        
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
        
        # 判定结果
        if score >= 3:
            estimate = '看涨'
            probability = '70%'
        elif score >= 1:
            estimate = '震荡偏多'
            probability = '60%'
        elif score >= -1:
            estimate = '震荡'
            probability = '50%'
        elif score >= -3:
            estimate = '震荡偏空'
            probability = '40%'
        else:
            estimate = '看跌'
            probability = '30%'
        
        # 生成理由
        reasons = []
        if tech['trend'] == '上涨':
            reasons.append('均线多头排列，短期趋势向上')
        elif tech['trend'] == '下跌':
            reasons.append('均线空头排列，短期趋势向下')
        
        if tech['current'] < tech['ma20'] * 0.9:
            reasons.append('价格处于相对低位')
        elif tech['current'] > tech['ma20'] * 1.1:
            reasons.append('价格处于相对高位')
        
        if tech['vol_ratio'] > 1.3:
            reasons.append('成交量放大')
        elif tech['vol_ratio'] < 0.7:
            reasons.append('成交量萎缩')
        
        if news.get('reason') and news['reason'] != '未提供新闻信息':
            reasons.append(news['reason'])
        
        return {
            'estimate': estimate,
            'probability': probability,
            'score': score,
            'reason': '; '.join(reasons) if reasons else '综合分析中'
        }
    
    def analyze(self, news_list=None):
        """执行完整分析"""
        print('正在获取 {} 行情数据...'.format(self.name))
        
        klines = self.get_kline(60)
        if not klines:
            return None
        
        tech = self.technical_analysis(klines)
        news = self.news_analysis(news_list or [])
        result = self.comprehensive_estimate(tech, news)
        
        return {
            'tech': tech,
            'news': news,
            'result': result
        }


def parse_input(user_input):
    """解析用户输入，提取股票代码和新闻关键词"""
    # 匹配6位数字的股票代码
    symbol_match = re.search(r'(\d{6})', user_input)
    
    # 提取股票代码
    symbol = symbol_match.group(1) if symbol_match else None
    
    # 提取新闻关键词（排除股票代码）
    text = user_input
    if symbol_match:
        text = text.replace(symbol_match.group(), '')
    
    # 简单分词，去除常见干扰词
    stop_words = ['分析', '预估', '预测', '走势', '股票', '帮我', '看看', '这只', '怎么样', '如何', '好不好']
    words = [w.strip() for w in re.split(r'[,\s]+', text) if w.strip() and w.strip() not in stop_words]
    
    return symbol, words


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python stock_forecast.py <stock_code> [news_keywords...]")
        print("Example: python stock_forecast.py 601899 业绩预增 黄金价格上涨")
        sys.exit(1)
    
    symbol = sys.argv[1]
    news = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # 尝试从输入推断股票名称
    name_map = {
        '601899': '紫金矿业',
        '600519': '贵州茅台',
        '000001': '平安银行',
        '600036': '招商银行',
    }
    name = name_map.get(symbol, symbol)
    
    analyzer = StockAnalyzer(symbol, name)
    result = analyzer.analyze(news)
    
    if not result:
        print("分析失败，请检查股票代码是否正确")
        sys.exit(1)
    
    tech = result['tech']
    news_result = result['news']
    estimate = result['result']
    
    print('')
    print('='*60)
    print('        {} 综合分析报告'.format(name))
    print('='*60)
    
    print('\n【技术面分析】')
    print('  当前价格: {:.2f} 元'.format(tech['current']))
    print('  MA5: {:.2f}  MA10: {:.2f}  MA20: {:.2f}'.format(tech['ma5'], tech['ma10'], tech['ma20']))
    print('  趋势判断: {}'.format(tech['trend']))
    print('  支撑位: {:.2f}  压力位: {:.2f}'.format(tech['support'], tech['resistance']))
    print('  量比: {:.2f}x'.format(tech['vol_ratio']))
    
    print('\n【消息面分析】')
    print('  影响方向: {}'.format(news_result['impact']))
    if news:
        print('  利好因素: {}条  利空因素: {}条'.format(news_result['bullish'], news_result['bearish']))
    else:
        print('  (无新闻信息，如需分析请提供相关新闻)')
    
    print('\n【综合预估】')
    print('  走势判断: {}'.format(estimate['estimate']))
    print('  预估概率: {}'.format(estimate['probability']))
    print('  分析理由: {}'.format(estimate['reason']))
    
    print('\n' + '='*60)
    print('⚠️ 此为辅助分析，仅供参考，不构成投资建议')
    print('='*60)


if __name__ == '__main__':
    main()