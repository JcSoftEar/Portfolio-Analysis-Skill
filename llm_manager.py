#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型管理器 - 负责与大模型相关的所有功能
"""

import sqlite3
import requests
import json
from datetime import datetime
import markdown

class LLMManager:
    """大模型管理器 - 处理所有与大模型相关的功能"""
    
    def __init__(self, db_path='portfolio.db', holding_manager=None):
        self.db_path = db_path
        self.holding_manager = holding_manager
        self.init_llm_database()
    
    def init_llm_database(self):
        """初始化大模型配置表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建大模型配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_type TEXT NOT NULL,  -- openai, baichuan, volcano
            model_name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            api_id TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 插入默认配置（如果不存在）
        cursor.execute('SELECT COUNT(*) FROM llm_config')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO llm_config (model_type, model_name, api_url, api_key, api_id, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('openai', 'gpt-3.5-turbo', 'https://api.openai.com/v1/chat/completions', '', '', 1))
        
        conn.commit()
        conn.close()
    
    def get_llm_config(self):
        """获取大模型配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, model_type, model_name, api_url, api_key, api_id, enabled
            FROM llm_config
            ORDER BY id
            ''')
            
            configs = []
            for row in cursor.fetchall():
                configs.append({
                    'id': row[0],
                    'model_type': row[1],
                    'model_name': row[2],
                    'api_url': row[3],
                    'api_key': row[4],
                    'api_id': row[5],
                    'enabled': bool(row[6])
                })
            
            conn.close()
            return {'status': 'success', 'data': configs}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def update_llm_config(self, config_id, model_type, model_name, api_url, api_key, api_id, enabled):
        """更新大模型配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新配置
            cursor.execute('''
            UPDATE llm_config 
            SET model_type = ?, model_name = ?, api_url = ?, api_key = ?, api_id = ?, enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (model_type, model_name, api_url, api_key, api_id, 1 if enabled else 0, config_id))
            
            if cursor.rowcount == 0:
                # 如果没有找到记录，插入新记录
                cursor.execute('''
                INSERT INTO llm_config (model_type, model_name, api_url, api_key, api_id, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (model_type, model_name, api_url, api_key, api_id, 1 if enabled else 0))
            
            conn.commit()
            conn.close()
            return {'status': 'success', 'message': '大模型配置更新成功'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def call_llm(self, prompt):
        """调用大模型"""
        try:
            # 获取启用的大模型配置
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT model_type, model_name, api_url, api_key, api_id
            FROM llm_config
            WHERE enabled = 1
            LIMIT 1
            ''')
            
            config = cursor.fetchone()
            conn.close()
            
            if not config:
                return {'status': 'error', 'error': '未找到启用的大模型配置'}
            
            model_type, model_name, api_url, api_key, api_id = config
            
            if model_type == 'openai':
                # 调用OpenAI API
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                
                data = {
                    'model': model_name,
                    'messages': [
                        {'role': 'system', 'content': '你是一位专业的股票分析师，请基于提供的数据进行分析并给出操作建议。中文回答！'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=300)
                print(response)
                if response.status_code == 200:
                    result = response.json()
                    # 将markdown转换为html
                    markdown_content = result['choices'][0]['message']['content']
                    html_content = markdown.markdown(markdown_content)
                    return {
                        'status': 'success',
                        'content': html_content,
                        'original_content': markdown_content
                    }
                else:
                    return {
                        'status': 'error',
                        'error': f'OpenAI API调用失败: {response.text}'
                    }
                    
            elif model_type == 'baichuan':
                # 调用百炼API
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                
                data = {
                    'model': model_name,
                    'messages': [
                        {'role': 'system', 'content': '你是一位专业的股票分析师，请基于提供的数据进行分析并给出操作建议。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    # 将markdown转换为html
                    markdown_content = result['choices'][0]['message']['content']
                    html_content = markdown.markdown(markdown_content)
                    return {
                        'status': 'success',
                        'content': html_content,
                        'original_content': markdown_content
                    }
                else:
                    return {
                        'status': 'error',
                        'error': f'百炼API调用失败: {response.text}'
                    }
                    
            elif model_type == 'volcano':
                # 调用火山引擎API
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                    'X-Volc-Auth-AK': api_id if api_id else ''
                }
                
                data = {
                    'model': model_name,
                    'messages': [
                        {'role': 'system', 'content': '你是一位专业的股票分析师，请基于提供的数据进行分析并给出操作建议。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    # 将markdown转换为html
                    markdown_content = result['choices'][0]['message']['content']
                    html_content = markdown.markdown(markdown_content)
                    return {
                        'status': 'success',
                        'content': html_content,
                        'original_content': markdown_content
                    }
                else:
                    return {
                        'status': 'error',
                        'error': f'火山引擎API调用失败: {response.text}'
                    }
                    
            else:
                return {'status': 'error', 'error': f'不支持的模型类型: {model_type}'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def analyze_stock(self, symbol):
        """分析股票"""
        try:
            # 获取股票详细信息（需要调用持仓管理器的方法）
            if not self.holding_manager:
                return {'status': 'error', 'error': '持仓管理器未初始化'}
                
            stock_detail = self.holding_manager.get_stock_detail(symbol)
            if not stock_detail:
                return {'status': 'error', 'error': f'获取股票{symbol}信息失败'}
            
            # 构建prompt
            prompt = f"""请分析以下股票：

股票名称：{stock_detail['name']}
股票代码：{symbol}
当前价格：{stock_detail['current']}元
今日开盘：{stock_detail['open']}元
今日最高：{stock_detail['high']}元
今日最低：{stock_detail['low']}元
昨日收盘：{stock_detail['pre_close']}元
涨跌额：{stock_detail['change']}元
涨跌幅：{stock_detail['change_percent']}%

近200个5分钟数据：
{json.dumps(stock_detail.get('min_data', {}), ensure_ascii=False)}

请基于以上数据，分析股票的走势情况，并给出后续操作建议（持仓、买入、卖出、观望等）。"""
            
            # 调用大模型
            result = self.call_llm(prompt)
            return result
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
