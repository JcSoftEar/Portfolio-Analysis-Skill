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

# 导入分离的管理器
from holding_manager import HoldingManager
from llm_manager import LLMManager

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 初始化管理器
holding_manager = HoldingManager('portfolio.db')
llm_manager = LLMManager('portfolio.db', holding_manager)

# 组合管理器，保持原有接口兼容
class CombinedManager:
    def __init__(self, holding_manager, llm_manager):
        self.holding_manager = holding_manager
        self.llm_manager = llm_manager
        self.init_database()
        self.auto_update_thread = None
        self.auto_update_running = False
    
    # 持仓管理方法委托
    def init_database(self):
        # 同时初始化两个管理器的数据库
        self.holding_manager.init_database()
        self.llm_manager.init_llm_database()
    
    def get_stock_price(self, *args, **kwargs):
        return self.holding_manager.get_stock_price(*args, **kwargs)
    
    def get_stock_detail(self, *args, **kwargs):
        return self.holding_manager.get_stock_detail(*args, **kwargs)
    
    def update_all_prices(self, *args, **kwargs):
        return self.holding_manager.update_all_prices(*args, **kwargs)
    
    def get_portfolio_data(self, *args, **kwargs):
        return self.holding_manager.get_portfolio_data(*args, **kwargs)
    
    def add_holding(self, *args, **kwargs):
        return self.holding_manager.add_holding(*args, **kwargs)
    
    def delete_holding(self, *args, **kwargs):
        return self.holding_manager.delete_holding(*args, **kwargs)
    
    def edit_holding(self, *args, **kwargs):
        return self.holding_manager.edit_holding(*args, **kwargs)
    
    def edit_holding_multiple(self, *args, **kwargs):
        return self.holding_manager.edit_holding_multiple(*args, **kwargs)
    
    def get_operation_logs(self, *args, **kwargs):
        return self.holding_manager.get_operation_logs(*args, **kwargs)
    
    def generate_report(self, *args, **kwargs):
        return self.holding_manager.generate_report(*args, **kwargs)
    
    def start_auto_update(self, *args, **kwargs):
        return self.holding_manager.start_auto_update(*args, **kwargs)
    
    def stop_auto_update(self, *args, **kwargs):
        return self.holding_manager.stop_auto_update(*args, **kwargs)
    
    # 大模型管理方法委托
    def get_llm_config(self, *args, **kwargs):
        return self.llm_manager.get_llm_config(*args, **kwargs)
    
    def update_llm_config(self, *args, **kwargs):
        return self.llm_manager.update_llm_config(*args, **kwargs)
    
    def call_llm(self, *args, **kwargs):
        return self.llm_manager.call_llm(*args, **kwargs)
    
    def analyze_stock(self, *args, **kwargs):
        return self.llm_manager.analyze_stock(*args, **kwargs)

# 使用组合管理器保持原有接口兼容
manager = CombinedManager(holding_manager, llm_manager)

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

# ------------------- 大模型相关API -------------------
@app.route('/api/llm/config', methods=['GET'])
def get_llm_config_api():
    """获取大模型配置"""
    result = manager.get_llm_config()
    return jsonify(result)

@app.route('/api/llm/config', methods=['POST'])
def update_llm_config_api():
    """更新大模型配置"""
    try:
        data = request.get_json()
        config_id = data.get('id', 1)
        model_type = data.get('model_type', 'openai')
        model_name = data.get('model_name', 'gpt-3.5-turbo')
        api_url = data.get('api_url', 'https://api.openai.com/v1/chat/completions')
        api_key = data.get('api_key', '')
        api_id = data.get('api_id', '')
        enabled = data.get('enabled', True)
        
        result = manager.update_llm_config(config_id, model_type, model_name, api_url, api_key, api_id, enabled)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/stock/analyze/<symbol>')
def analyze_stock_api(symbol):
    """分析股票"""
    try:
        result = manager.analyze_stock(symbol)
        return jsonify(result)
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
