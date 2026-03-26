#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓看盘系统 - 统一网页版
整合所有功能，提供完整的股票投资管理解决方案
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import requests
import json
import os
import socket
import threading
import time
from datetime import datetime
import webbrowser

# 模拟浏览器的headers
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

class PortfolioManager:
    """持仓管理器 - 核心业务逻辑"""
    
    def __init__(self, db_path='portfolio.db'):
        self.db_path = db_path
        self.init_database()
        self.auto_update_thread = None
        self.auto_update_running = False
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建持仓表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            current_price REAL NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建操作记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_stock_price(self, symbol):
        """获取股票实时价格 - 支持多个数据源"""
        try:
            # 判断市场
            if symbol.startswith('6'):
                market = 'sh'
            elif symbol.startswith('0') or symbol.startswith('3'):
                market = 'sz'
            elif symbol.startswith('688'):
                market = 'sh'
            elif symbol.startswith('301'):
                market = 'sz'
            elif symbol.startswith('512'):
                market = 'sh'
            elif symbol.startswith('000'):
                market = 'sz'
            elif symbol.startswith('1'):
                market = 'sz'
            else:
                market = 'sh'
            
            # 尝试新浪财经API
            url = f'https://hq.sinajs.cn/list={market}{symbol}'
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            
            if response.status_code == 200:
                content = response.content.decode('gbk')
                if '\"' in content:
                    data_str = content.split('\"')[1]
                    values = data_str.split(',')
                    
                    if len(values) >= 32 and values[3]:
                        return {
                            'price': float(values[3]),
                            'name': values[0],
                            'source': '新浪财经'
                        }
            
            # 如果新浪失败，尝试腾讯API
            code = f'{market}{symbol}'
            url = f'https://qt.gtimg.cn/q={code}'
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            # print('response', response.text)
            if response.status_code == 200:
                text = response.text
                if '=' in text:
                    parts = text.split('=')
                    if len(parts) > 1:
                        values = parts[1].strip('"').split('~')
                        if len(values) >= 4 and values[3]:
                            return {
                                'price': float(values[3]),
                                'name': values[1],
                                'source': '腾讯财经'
                            }
            
            return None
            
        except Exception as e:
            print(f"获取价格失败 {symbol}: {e}")
            return None
    
    def get_stock_detail(self, symbol):
        """获取股票详细信息，包括涨跌和分时图数据"""
        try:
            # 判断市场
            if symbol.startswith('6'):
                market = 'sh'
            elif symbol.startswith('0') or symbol.startswith('3'):
                market = 'sz'
            elif symbol.startswith('688'):
                market = 'sh'
            elif symbol.startswith('301'):
                market = 'sz'
            elif symbol.startswith('512'):
                market = 'sh'
            elif symbol.startswith('000'):
                market = 'sz'
            elif symbol.startswith('1'):
                market = 'sz'
            else:
                market = 'sh'
            
            # 尝试新浪财经API获取详细数据
            url = f'https://hq.sinajs.cn/list={market}{symbol}'
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            
            detail_data = None
            
            if response.status_code == 200:
                content = response.content.decode('gbk')
                if '\"' in content:
                    data_str = content.split('\"')[1]
                    values = data_str.split(',')
                    
                    if len(values) >= 32:
                        detail_data = {
                            'symbol': symbol,
                            'name': values[0],
                            'open': float(values[1]) if values[1] else 0,
                            'pre_close': float(values[2]) if values[2] else 0,
                            'current': float(values[3]) if values[3] else 0,
                            'high': float(values[4]) if values[4] else 0,
                            'low': float(values[5]) if values[5] else 0,
                            'source': '新浪财经'
                        }
            
            # 如果新浪失败，尝试腾讯API
            if not detail_data:
                code = f'{market}{symbol}'
                url = f'https://qt.gtimg.cn/q={code}'
                response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
                if response.status_code == 200:
                    text = response.text
                    if '=' in text:
                        parts = text.split('=')
                        if len(parts) > 1:
                            values = parts[1].strip('"').split('~')
                            if len(values) >= 40:
                                detail_data = {
                                    'symbol': symbol,
                                    'name': values[1],
                                    'open': float(values[5]) if values[5] else 0,
                                    'pre_close': float(values[4]) if values[4] else 0,
                                    'current': float(values[3]) if values[3] else 0,
                                    'high': float(values[33]) if values[33] else 0,
                                    'low': float(values[34]) if values[34] else 0,
                                    'source': '腾讯财经'
                                }
            
            if detail_data:
                # 计算涨跌
                change = detail_data['current'] - detail_data['pre_close']
                change_percent = (change / detail_data['pre_close'] * 100) if detail_data['pre_close'] != 0 else 0
                detail_data['change'] = change
                detail_data['change_percent'] = change_percent
                
                # 获取分时图数据
                detail_data['min_data'] = self.get_minute_data(market, symbol)
            
            return detail_data
            
        except Exception as e:
            print(f"获取股票详情失败 {symbol}: {e}")
            return None
    
    def get_minute_data(self, market, symbol):
        """获取分时图数据"""
        try:
            # 获取今天的日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 使用新浪财经分钟级K线API（5分钟）
            url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {
                'symbol': f'{market}{symbol}',
                'scale': '5',
                'datalen': '320',
                'ma': 'no'
            }
            
            response = requests.get(url, headers=REQUEST_HEADERS, params=params, timeout=10)
            
            if response.status_code == 200:
                text = response.text
                # 解析返回的数据
                try:
                    # 清理可能的格式问题
                    if text.startswith('('):
                        text = text[1:]
                    if text.endswith(')'):
                        text = text[:-1]
                    
                    import json
                    kline_data = json.loads(text)
                    
                    if kline_data and len(kline_data) > 0:
                        minute_data = {
                            'times': [],
                            'prices': [],
                            'volumes': [],
                            'opens': [],
                            'highs': [],
                            'lows': []
                        }
                        
                        for kline in kline_data:
                            # 提取时间
                            if 'day' in kline:
                                day_str = kline['day']
                                if len(day_str) >= 16:
                                    # 格式化为 HH:MM
                                    time_part = day_str[11:16]
                                    hour = int(time_part[:2])
                                    minute = int(time_part[3:])
                                    
                                    # 检查是否是今天的日期
                                    date_part = day_str[:10]
                                    
                                    # 只保留今天9:30到15:00之间的数据
                                    if date_part == today and (hour > 9 or (hour == 9 and minute >= 30)) and hour < 15:
                                        minute_data['times'].append(time_part)
                                        
                                        # 提取价格（使用close）
                                        if 'close' in kline and kline['close']:
                                            minute_data['prices'].append(float(kline['close']))
                                        elif 'open' in kline and kline['open']:
                                            minute_data['prices'].append(float(kline['open']))
                                        else:
                                            minute_data['prices'].append(0)
                                        
                                        # 提取成交量
                                        if 'volume' in kline and kline['volume']:
                                            minute_data['volumes'].append(int(kline['volume']))
                                        else:
                                            minute_data['volumes'].append(0)
                                        
                                        # 提取其他K线数据
                                        if 'open' in kline and kline['open']:
                                            minute_data['opens'].append(float(kline['open']))
                                        if 'high' in kline and kline['high']:
                                            minute_data['highs'].append(float(kline['high']))
                                        if 'low' in kline and kline['low']:
                                            minute_data['lows'].append(float(kline['low']))
                        
                        if minute_data['times'] and minute_data['prices']:
                            return minute_data
                
                except Exception as e:
                    print(f'解析K线数据失败: {e}')
            
            # 如果新浪K线失败，尝试原来的分时数据API
            url = f'https://hq.sinajs.cn/list={market}{symbol}_min'
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            
            if response.status_code == 200:
                content = response.content.decode('gbk')
                if '\"' in content:
                    data_str = content.split('\"')[1]
                    if data_str:
                        values = data_str.split(',')
                        
                        if len(values) >= 1:
                            # 解析分时数据
                            minute_data = {
                                'times': [],
                                'prices': [],
                                'volumes': []
                            }
                            
                            # 新浪数据格式：价格,均价,成交量,时间
                            for i in range(0, len(values), 4):
                                if i + 3 < len(values) and values[i]:
                                    time_str = values[i + 3]
                                    if time_str:
                                        minute_data['times'].append(time_str)
                                        minute_data['prices'].append(float(values[i]) if values[i] else 0)
                                        minute_data['volumes'].append(int(values[i + 2]) if values[i + 2] else 0)
                            
                            if minute_data['times']:
                                return minute_data
            
            # 如果新浪失败，尝试腾讯财经分时图
            url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_min&param={market}{symbol},min,86400,1'
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            
            if response.status_code == 200:
                text = response.text
                if '=' in text:
                    json_str = text.split('=', 1)[1]
                    try:
                        import json
                        data = json.loads(json_str)
                        if data.get('data') and data['data'].get(market + symbol):
                            kline_data = data['data'][market + symbol]['min']
                            if kline_data:
                                minute_data = {
                                    'times': [],
                                    'prices': [],
                                    'volumes': []
                                }
                                for kline in kline_data:
                                    if len(kline) >= 6:
                                        time_str = kline[0]
                                        if time_str:
                                            # 只取时间部分
                                            time_short = time_str[-5:] if len(time_str) >= 5 else time_str
                                            minute_data['times'].append(time_short)
                                            minute_data['prices'].append(float(kline[1]) if kline[1] else 0)
                                            minute_data['volumes'].append(int(kline[5]) if kline[5] else 0)
                                
                                if minute_data['times']:
                                    return minute_data
                    except:
                        pass
            
            # 如果都失败，返回示例数据
            return {
                'times': ['09:30', '10:00', '10:30', '11:00', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'],
                'prices': [],
                'volumes': []
            }
            
        except Exception as e:
            print(f"获取分时图数据失败 {symbol}: {e}")
            # 返回示例数据
            return {
                'times': ['09:30', '10:00', '10:30', '11:00', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'],
                'prices': [],
                'volumes': []
            }
    
    def update_all_prices(self):
        """更新所有持仓价格"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有持仓
            cursor.execute('SELECT symbol, name, current_price FROM holdings')
            holdings = cursor.fetchall()
            
            updated_count = 0
            failed_list = []
            
            for symbol, name, old_price in holdings:
                try:
                    price_data = self.get_stock_price(symbol)
                    print(price_data, symbol)
                    if price_data:
                        new_price = price_data['price']
                        cursor.execute('''
                        UPDATE holdings 
                        SET current_price = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE symbol = ?
                        ''', (new_price, symbol))
                        updated_count += 1
                    else:
                        failed_list.append(f'{name}({symbol})')
                except Exception:
                    failed_list.append(f'{name}({symbol})')
            
            conn.commit()
            conn.close()
            
            message = f'更新完成: 成功 {updated_count} 只, 失败 {len(failed_list)} 只'
            if failed_list:
                message += f'\n失败的股票: {", ".join(failed_list)}'
            
            return {
                'status': 'success',
                'message': message,
                'updated_count': updated_count,
                'failed_count': len(failed_list),
                'failed_symbols': failed_list
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_portfolio_data(self):
        """获取完整的持仓数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取持仓数据
            cursor.execute('''
            SELECT 
                symbol,
                name,
                quantity,
                cost_price,
                current_price,
                ROUND((current_price - cost_price) * quantity, 4) as pnl,
                ROUND((current_price - cost_price) / cost_price * 100, 4) as pnl_percent,
                ROUND((quantity * current_price) / (SELECT SUM(quantity * current_price) FROM holdings) * 100, 4) as weight_percent,
                last_updated
            FROM holdings
            ORDER BY weight_percent DESC
            ''')
            
            holdings = cursor.fetchall()
            
            # 计算总体情况
            cursor.execute('''
            SELECT 
                SUM(quantity * current_price) as total_value,
                SUM(quantity * cost_price) as total_cost,
                SUM(quantity * (current_price - cost_price)) as total_pnl,
                COUNT(*) as holding_count
            FROM holdings
            ''')
            
            result = cursor.fetchone()
            if result:
                total_value, total_cost, total_pnl, holding_count = result
                total_pnl_percent = (total_pnl / total_cost * 100) if total_cost != 0 else 0
            else:
                total_value = total_cost = total_pnl = total_pnl_percent = holding_count = 0
            
            conn.close()
            
            # 整理数据
            portfolio_data = {
                'holdings': [],
                'summary': {
                    'total_value': round(total_value, 4),
                    'total_cost': round(total_cost, 4),
                    'total_pnl': round(total_pnl, 4),
                    'total_pnl_percent': round(total_pnl_percent, 4),
                    'holding_count': holding_count,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            for h in holdings:
                symbol, name, qty, cost, current, pnl, pnl_pct, weight, updated = h
                portfolio_data['holdings'].append({
                    'symbol': symbol,
                    'name': name,
                    'quantity': qty,
                    'cost_price': round(cost, 4),
                    'current_price': round(current, 4),
                    'pnl': round(pnl, 4),
                    'pnl_percent': round(pnl_pct, 4),
                    'weight_percent': round(weight, 4),
                    'last_updated': updated
                })
            
            return portfolio_data
            
        except Exception as e:
            print(f"获取持仓数据失败: {e}")
            return None
    
    def add_holding(self, symbol, name, quantity, cost_price):
        """新增持仓记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM holdings WHERE symbol = ?', (symbol,))
            if cursor.fetchone():
                conn.close()
                return {'status': 'error', 'error': f'股票{symbol}已存在'}
            
            # 获取实时价格
            price_data = self.get_stock_price(symbol)
            if price_data:
                current_price = price_data['price']
                name = price_data['name'] if not name else name
            else:
                current_price = cost_price
                if not name:
                    conn.close()
                    return {'status': 'error', 'error': '请输入股票名称'}
            
            # 插入新记录
            cursor.execute('''
            INSERT INTO holdings (symbol, name, quantity, cost_price, current_price)
            VALUES (?, ?, ?, ?, ?)
            ''', (symbol, name, quantity, cost_price, current_price))
            
            # 记录操作
            cursor.execute('''
            INSERT INTO operation_log (operation_type, symbol, details)
            VALUES (?, ?, ?)
            ''', ('add', symbol, f'新增持仓: {name} {quantity}股 成本价:{cost_price:.4f}'))
            
            conn.commit()
            conn.close()
            
            return {'status': 'success', 'message': f'成功添加持仓: {name}({symbol})'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def delete_holding(self, symbol):
        """删除持仓记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否存在
            cursor.execute('SELECT name FROM holdings WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {'status': 'error', 'error': f'股票{symbol}不存在'}
            
            name = result[0]
            
            # 删除记录
            cursor.execute('DELETE FROM holdings WHERE symbol = ?', (symbol,))
            
            # 记录操作
            cursor.execute('''
            INSERT INTO operation_log (operation_type, symbol, details)
            VALUES (?, ?, ?)
            ''', ('delete', symbol, f'删除持仓: {name}'))
            
            conn.commit()
            conn.close()
            
            return {'status': 'success', 'message': f'成功删除持仓: {name}({symbol})'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def edit_holding(self, symbol, field, value):
        """编辑持仓记录"""
        try:
            if field not in ['quantity', 'cost_price', 'current_price', 'symbol', 'name']:
                return {'status': 'error', 'error': '无效字段'}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取旧值
            cursor.execute(f'SELECT {field} FROM holdings WHERE symbol = ?', (symbol,))
            old_value = cursor.fetchone()
            
            if not old_value:
                conn.close()
                return {'status': 'error', 'error': f'股票{symbol}不存在'}
            
            old_value = old_value[0]
            
            # 如果修改股票代码，检查新代码是否已存在
            if field == 'symbol':
                cursor.execute('SELECT id FROM holdings WHERE symbol = ? AND symbol != ?', (value, symbol))
                if cursor.fetchone():
                    conn.close()
                    return {'status': 'error', 'error': f'股票{value}已存在'}
            
            # 更新字段
            if field == 'symbol':
                # 如果修改股票代码，需要更新操作记录中的symbol
                cursor.execute(f'''
                UPDATE holdings 
                SET {field} = ?, last_updated = CURRENT_TIMESTAMP
                WHERE symbol = ?
                ''', (value, symbol))
                
                # 更新操作记录中的symbol
                cursor.execute('''
                UPDATE operation_log 
                SET symbol = ?
                WHERE symbol = ?
                ''', (value, symbol))
            else:
                cursor.execute(f'''
                UPDATE holdings 
                SET {field} = ?, last_updated = CURRENT_TIMESTAMP
                WHERE symbol = ?
                ''', (value, symbol))
            
            # 记录操作
            if field == 'cost_price':
                cursor.execute('''
                INSERT INTO operation_log (operation_type, symbol, details)
                VALUES (?, ?, ?)
                ''', ('edit', value if field == 'symbol' else symbol, f'修改{field}: {old_value:.4f} -> {value:.4f}'))
            else:
                cursor.execute('''
                INSERT INTO operation_log (operation_type, symbol, details)
                VALUES (?, ?, ?)
                ''', ('edit', value if field == 'symbol' else symbol, f'修改{field}: {old_value} -> {value}'))
            
            conn.commit()
            conn.close()
            
            return {'status': 'success', 'message': f'成功修改: {field}: {old_value} -> {value}'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def edit_holding_multiple(self, old_symbol, data):
        """批量编辑持仓记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取旧数据
            cursor.execute('SELECT symbol, name, quantity, cost_price FROM holdings WHERE symbol = ?', (old_symbol,))
            old_data = cursor.fetchone()
            
            if not old_data:
                conn.close()
                return {'status': 'error', 'error': f'股票{old_symbol}不存在'}
            
            old_symbol_db, old_name, old_quantity, old_cost_price = old_data
            
            # 检查新股票代码是否已存在（如果有变化）
            new_symbol = data.get('symbol', old_symbol_db)
            if new_symbol != old_symbol_db:
                cursor.execute('SELECT id FROM holdings WHERE symbol = ? AND symbol != ?', (new_symbol, old_symbol_db))
                if cursor.fetchone():
                    conn.close()
                    return {'status': 'error', 'error': f'股票{new_symbol}已存在'}
            
            # 构建更新语句
            update_fields = []
            update_values = []
            changes = []
            
            # 检查各个字段的变化
            if new_symbol != old_symbol_db:
                update_fields.append('symbol = ?')
                update_values.append(new_symbol)
                changes.append(f'股票代码: {old_symbol_db} -> {new_symbol}')
            
            new_name = data.get('name', old_name)
            if new_name != old_name:
                update_fields.append('name = ?')
                update_values.append(new_name)
                changes.append(f'股票名称: {old_name} -> {new_name}')
            
            new_quantity = data.get('quantity', old_quantity)
            if new_quantity != old_quantity:
                update_fields.append('quantity = ?')
                update_values.append(new_quantity)
                changes.append(f'持仓数量: {old_quantity} -> {new_quantity}')
            
            new_cost_price = data.get('cost_price', old_cost_price)
            if new_cost_price != old_cost_price:
                update_fields.append('cost_price = ?')
                update_values.append(new_cost_price)
                changes.append(f'成本价: {old_cost_price:.4f} -> {new_cost_price:.4f}')
            
            # 如果有变化，执行更新
            if update_fields:
                update_fields.append('last_updated = CURRENT_TIMESTAMP')
                update_values.append(old_symbol_db)
                
                cursor.execute(f'''
                UPDATE holdings 
                SET {', '.join(update_fields)}
                WHERE symbol = ?
                ''', update_values)
                
                # 如果修改了股票代码，更新操作记录中的symbol
                if new_symbol != old_symbol_db:
                    cursor.execute('''
                    UPDATE operation_log 
                    SET symbol = ?
                    WHERE symbol = ?
                    ''', (new_symbol, old_symbol_db))
                
                # 记录一次操作
                if changes:
                    details = '; '.join(changes)
                    cursor.execute('''
                    INSERT INTO operation_log (operation_type, symbol, details)
                    VALUES (?, ?, ?)
                    ''', ('edit', new_symbol, f'批量修改: {details}'))
                
                conn.commit()
            
            conn.close()
            
            if changes:
                return {'status': 'success', 'message': '编辑成功'}
            else:
                return {'status': 'success', 'message': '无变化'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_operation_logs(self, limit=50):
        """获取操作记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT operation_type, symbol, details, created_at 
            FROM operation_log 
            ORDER BY created_at DESC 
            LIMIT ?
            ''', (limit,))
            
            logs = cursor.fetchall()
            conn.close()
            
            log_list = []
            for op_type, symbol, details, timestamp in logs:
                log_list.append({
                    'operation_type': op_type,
                    'symbol': symbol,
                    'details': details,
                    'timestamp': timestamp
                })
            
            return {'status': 'success', 'logs': log_list}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def generate_report(self):
        """生成持仓报告"""
        try:
            portfolio_data = self.get_portfolio_data()
            
            if not portfolio_data:
                return {'status': 'error', 'error': '获取数据失败'}
            
            summary = portfolio_data['summary']
            holdings = portfolio_data['holdings']
            
            # 生成报告内容
            report_content = f"""# 持仓报告

**生成时间:** {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

## 总体情况

- 持仓数量: {summary['holding_count']} 只
- 总市值: ¥{summary['total_value']:,.4f}
- 总成本: ¥{summary['total_cost']:,.4f}
- 总盈亏: ¥{summary['total_pnl']:+,.4f} ({summary['total_pnl_percent']:+.4f}%)

## 持仓明细

| 股票名称 | 股票代码 | 持仓数量 | 成本价 | 当前价 | 盈亏额 | 盈亏% | 仓位% |
|----------|----------|----------|--------|--------|--------|--------|--------|
"""
            
            for holding in holdings:
                cost = holding['cost_price']
                current = holding['current_price']
                pnl = holding['pnl']
                pnl_percent = holding['pnl_percent']
                weight = holding['weight_percent']
                
                report_content += f"| {holding['name']} | {holding['symbol']} | {holding['quantity']:,} | ¥{cost:.4f} | ¥{current:.4f} | ¥{pnl:+,.4f} | {pnl_percent:+.4f}% | {weight:.4f}% |\n"
            
            # 添加报告尾部
            report_content += f"""
## 报告生成信息

- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 持仓总数: {summary['holding_count']} 只
- 更新时间: {summary['update_time']}
---
**报告生成完成**
"""
            
            # 保存报告文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs('reports', exist_ok=True)
            report_path = f'reports/portfolio_report_{timestamp}.md'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return {
                'status': 'success',
                'message': f'报告生成成功: {report_path}',
                'report_path': report_path
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def start_auto_update(self, interval_seconds=300):
        """启动自动更新线程"""
        def is_trading_time():
            """检查是否是交易时间"""
            now = datetime.now()
            
            # 检查是否是工作日（周一到周五）
            if now.weekday() >= 5:  # 0-4 是周一到周五
                return False
            
            # 检查时间是否在交易时段内
            hour = now.hour
            minute = now.minute
            
            # 上午交易时间：9:30 - 11:30
            morning_trading = (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30)
            
            # 下午交易时间：13:00 - 15:00
            afternoon_trading = (hour == 13) or (hour == 14) or (hour == 15 and minute == 0)
            
            return morning_trading or afternoon_trading
        
        def update_worker():
            while self.auto_update_running:
                try:
                    if is_trading_time():
                        result = self.update_all_prices()
                        if result['status'] == 'success':
                            print(f"🔄 自动更新完成: {result['message']}")
                    time.sleep(interval_seconds)
                except Exception as e:
                    print(f"❌ 自动更新失败: {e}")
                    time.sleep(60)
        
        self.auto_update_running = True
        self.auto_update_thread = threading.Thread(target=update_worker, daemon=True)
        self.auto_update_thread.start()
        print(f"✅ 自动更新已启动，间隔 {interval_seconds} 秒")
    
    def stop_auto_update(self):
        """停止自动更新"""
        self.auto_update_running = False
        if self.auto_update_thread:
            self.auto_update_thread.join(timeout=5)
        print("⏹️  自动更新已停止")

# 初始化管理器
manager = PortfolioManager('portfolio.db')

def get_local_ip():
    """获取本地IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/portfolio')
def get_portfolio():
    """获取持仓数据"""
    try:
        portfolio_data = manager.get_portfolio_data()
        
        if portfolio_data:
            return jsonify({
                'status': 'success',
                **portfolio_data
            })
        else:
            return jsonify({
                'status': 'error',
                'error': '获取数据失败'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/portfolio/update', methods=['POST'])
def update_prices():
    """更新持仓价格"""
    result = manager.update_all_prices()
    return jsonify(result)

@app.route('/api/portfolio/add', methods=['POST'])
def add_holding():
    """新增持仓记录"""
    try:
        data = request.get_json()
        
        required_fields = ['symbol', 'quantity', 'cost_price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'error': f'缺少字段: {field}'
                }), 400
        
        result = manager.add_holding(
            data['symbol'],
            data.get('name', ''),
            data['quantity'],
            data['cost_price']
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/portfolio/delete/<symbol>', methods=['DELETE'])
def delete_holding(symbol):
    """删除持仓记录"""
    result = manager.delete_holding(symbol)
    return jsonify(result)

@app.route('/api/portfolio/edit/<symbol>', methods=['PUT'])
def edit_holding(symbol):
    """编辑持仓记录"""
    try:
        data = request.get_json()
        field = data.get('field', 'quantity')
        value = data.get('value', 0)
        
        result = manager.edit_holding(symbol, field, value)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/portfolio/edit-multiple/<symbol>', methods=['PUT'])
def edit_holding_multiple(symbol):
    """批量编辑持仓记录"""
    try:
        data = request.get_json()
        
        result = manager.edit_holding_multiple(symbol, data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/portfolio/logs')
def get_logs():
    """获取操作记录"""
    result = manager.get_operation_logs()
    return jsonify(result)

@app.route('/api/portfolio/report')
def generate_report():
    """生成持仓报告"""
    result = manager.generate_report()
    return jsonify(result)

@app.route('/api/portfolio/export')
def export_report():
    """导出持仓报告"""
    result = manager.generate_report()
    
    if result['status'] == 'success':
        report_path = result['report_path']
        return send_file(report_path, as_attachment=True)
    else:
        return jsonify(result)

@app.route('/api/stock/price/<symbol>')
def get_stock_price_api(symbol):
    """查询股票价格"""
    try:
        result = manager.get_stock_price(symbol)
        if result:
            return jsonify({
                'status': 'success',
                'symbol': result['symbol'] if 'symbol' in result else symbol,
                'name': result['name'],
                'price': result['price']
            })
        else:
            return jsonify({
                'status': 'error',
                'error': '未找到股票信息'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/stock/detail/<symbol>')
def get_stock_detail_api(symbol):
    """查询股票详细信息"""
    try:
        result = manager.get_stock_detail(symbol)
        if result:
            return jsonify({
                'status': 'success',
                'data': result
            })
        else:
            return jsonify({
                'status': 'error',
                'error': '未找到股票信息'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

def start_server(host='0.0.0.0', port=5000, debug=False, auto_update=True):
    """启动Web服务器"""
    print("="*60)
    print("🚀 持仓看盘系统 - 统一网页版")
    print("="*60)
    
    local_ip = get_local_ip()
    
    print(f"📡 访问地址:")
    print(f"   本地: http://localhost:{port}")
    print(f"   局域网: http://{local_ip}:{port}")
    print(f"   移动端: http://{local_ip}:{port}")
    print()
    print("🎯 功能特性:")
    print("   📊 持仓管理 - 增删改查")
    print("   🔄 实时价格 - 自动更新")
    print("   📈 数据分析 - 盈亏统计")
    print("   📋 操作记录 - 完整追溯")
    print("   📄 报告导出 - Markdown格式")
    print()
    print("🔧 按 Ctrl+C 停止服务")
    print("="*60)
    
    # 启动自动更新
    if auto_update:
        manager.start_auto_update(interval_seconds=300)
    
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        manager.stop_auto_update()
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")

def main():
    """主函数"""
    print("🔍 系统初始化...")
    
    # 检查数据库
    if not os.path.exists('portfolio.db'):
        print("⚠️  数据库不存在，正在创建...")
        manager.init_database()
    
    print("✅ 系统就绪")
    print()
    
    # 启动服务器
    start_server(host='0.0.0.0', port=5000, debug=False, auto_update=True)

if __name__ == '__main__':
    main()