#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股价走势预估工具 - 智能学习版
具备自主了解股票概念的能力
"""

import json
import re
import statistics
import sys
import os

try:
    import requests
except ImportError:
    sys.exit(1)


# 股票概念知识库（自动扩展）
STOCK_KNOWLEDGE = {
    '002050': {
        'name': '三花智控',
        'industry': '新能源车热管理',
        'concepts': ['特斯拉概念', '机器人概念', '人形机器人', 'Optimus', '微通道换热器'],
        'keywords': ['新能源车', '热管理', '制冷', '空调', '特斯拉', '机器人', '订单', '业绩', '比亚迪']
    },
    '601899': {
        'name': '紫金矿业',
        'industry': '黄金开采',
        'concepts': ['黄金概念', '避险资产', '有色金属', '铜'],
        'keywords': ['黄金', '金价', '有色金属', '铜', '矿产', '中东', '避险', '央行', '业绩']
    },
}

# 知识库文件路径
KNOWLEDGE_FILE = '/home/admin/.openclaw/workspace/memory/stock_knowledge.json'


class StockKnowledgeLearner:
    """股票概念学习器"""
    
    def __init__(self):
        self.knowledge = STOCK_KNOWLEDGE.copy()
        self._load_knowledge()
    
    def _load_knowledge(self):
        """加载本地知识库"""
        if os.path.exists(KNOWLEDGE_FILE):
            try:
                with open(KNOWLEDGE_FILE, 'r') as f:
                    saved = json.load(f)
                    self.knowledge.update(saved)
            except:
                pass
    
    def _save_knowledge(self):
        """保存知识库"""
        with open(KNOWLEDGE_FILE, 'w') as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
    
    def learn(self, symbol, name, concepts_or_keywords):
        """学习新的股票概念"""
        if symbol not in self.knowledge:
            self.knowledge[symbol] = {
                'name': name,
                'industry': '未知',
                'concepts': [],
                'keywords': []
            }
        
        # 更新概念和关键词
        for item in concepts_or_keywords:
            if item not in self.knowledge[symbol]['concepts']:
                self.knowledge[symbol]['concepts'].append(item)
            if item not in self.knowledge[symbol]['keywords']:
                self.knowledge[symbol]['keywords'].append(item)
        
        self._save_knowledge()
        print(f"✅ 已学习: {name}({symbol}) - 新增概念: {concepts_or_keywords}")
    
    def get_knowledge(self, symbol, name=None):
        """获取股票知识"""
        if symbol in self.knowledge:
            return self.knowledge[symbol]
        
        # 如果没有，返回默认结构
        return {
            'name': name or symbol,
            'industry': '未知',
            'concepts': [],
            'keywords': [name] if name else []
        }
    
    def get_all_concepts(self, symbol):
        """获取某股票所有概念"""
        info = self.get_knowledge(symbol)
        return info.get('concepts', []) + info.get('keywords', [])


class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, symbol, name=None, learner=None):
        self.symbol = symbol
        self.learner = learner or StockKnowledgeLearner()
        self.info = self.learner.get_knowledge(symbol, name)
        self.name = self.info['name']
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
    
    def get_kline(self, days=60):
        market = 'sh' if self.symbol.startswith('6') else 'sz'
        url = f'https://quotes.sina.cn/cn/api/jsonp.php/var _m{market}{self.symbol}=/CN_MarketDataService.getKLineData?symbol={market}{self.symbol}&scale=240&ma=no'
        
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            data = json.loads(re.search(r'\[.*\]', r.text).group())
            return data[-days:]
        except:
            return None
    
    def analyze(self, user_news=None):
        print(f'正在分析 {self.name}...')
        
        # 获取概念关键词
        concepts = self.learner.get_all_concepts(self.symbol)
        print(f'  已掌握概念: {concepts}')
        
        klines = self.get_kline(60)
        if not klines:
            return {'error': '无法获取数据'}
        
        # 技术分析
        closes = [float(k['close']) for k in klines]
        volumes = [int(k['volume']) for k in klines]
        
        ma5 = statistics.mean(closes[-5:])
        ma10 = statistics.mean(closes[-10:])
        ma20 = statistics.mean(closes[-20:])
        current = closes[-1]
        
        trend = '上涨' if ma5 > ma10 > ma20 else ('下跌' if ma5 < ma10 < ma20 else '震荡')
        
        # 消息分析
        news_keywords = concepts + (user_news or [])
        bullish = sum([1 for kw in news_keywords if any(k in kw for k in ['增长','订单','业绩','特斯拉','机器人','利好','突破'])])
        bearish = sum([1 for kw in news_keywords if any(k in kw for k in ['下跌','利空','减持','亏损','风险'])])
        
        impact = '偏多' if bullish > bearish else ('偏空' if bearish > bullish else '中性')
        news_score = bullish - bearish
        
        # 预估
        score = 0
        if current > ma5: score += 1
        if current > ma10: score += 1
        if trend == '上涨': score += 2
        elif trend == '下跌': score -= 2
        score += news_score
        
        next_dir = '上涨' if score >= 2 else ('下跌' if score <= -2 else '震荡')
        week_dir = '上涨' if (ma10-closes[-5])/closes[-5] + news_score*0.015 > 0.02 else ('下跌' if (ma10-closes[-5])/closes[-5] + news_score*0.015 < -0.02 else '震荡')
        month_dir = '上涨' if (ma20-closes[-20])/closes[-20] + news_score*0.01 > 0.03 else ('下跌' if (ma20-closes[-20])/closes[-20] + news_score*0.01 < -0.03 else '震荡')
        
        return {
            'name': self.name,
            'symbol': self.symbol,
            'concepts': concepts,
            'current': current,
            'trend': trend,
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20,
            'impact': impact,
            'bullish': bullish,
            'next': {'range': f'{current*0.98:.2f}~{current*1.02:.2f}', 'dir': next_dir},
            'week': {'price': f'{current*(1+(ma10-closes[-5])/closes[-5]+news_score*0.015):.2f}', 'dir': week_dir},
            'month': {'price': f'{current*(1+(ma20-closes[-20])/closes[-20]+news_score*0.01):.2f}', 'dir': month_dir}
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python stock_learn.py <股票代码> [用户消息...]")
        print("示例: python stock_learn.py 002050 业绩预增 特斯拉机器人订单")
        sys.exit(1)
    
    symbol = sys.argv[1]
    user_news = sys.argv[2:] if len(sys.argv) > 2 else []
    
    analyzer = StockAnalyzer(symbol)
    result = analyzer.analyze(user_news)
    
    if 'error' in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    
    print('')
    print('='*55)
    print(f'  {result["name"]}({result["symbol"]}) 综合分析')
    print('='*55)
    print(f'已掌握概念: {result["concepts"]}')
    print(f'当前价格: {result["current"]:.2f}元 | 趋势: {result["trend"]}')
    print(f'消息面: {result["impact"]} (利好{result["bullish"]}条)')
    print('')
    print(f'📅 次日: {result["next"]["range"]} -> {result["next"]["dir"]}')
    print(f'📆 7日:  {result["week"]["price"]}元 -> {result["week"]["dir"]}')
    print(f'📆 30日: {result["month"]["price"]}元 -> {result["month"]["dir"]}')
    print('='*55)


if __name__ == '__main__':
    main()