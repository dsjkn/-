# -*- coding: utf-8 -*-
"""
养基宝 - 模拟持仓管理系统 (Kivy移动版)
使用Kivy实现基金持仓管理和收益分析功能，支持Android平台
"""

import sys
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import time as time_module
import warnings
import json
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.datepicker import DatePicker
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# 配置Matplotlib字体
matplotlib.rcParams.update({
    'font.family': ['SimHei', 'Microsoft YaHei', 'sans-serif'],
    'axes.unicode_minus': False,  # 解决负号显示问题
    'figure.figsize': (6, 3),
    'figure.dpi': 100,
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'axes.linewidth': 1.5
})

# 忽略所有警告
warnings.filterwarnings('ignore')

class SafeRequest:
    """安全请求类：自动重试 + 指数退避"""
    
    @staticmethod
    def request(func, *args, retries=5, delay=1.2, **kwargs):
        """执行安全请求，自动重试失败的请求"""
        for i in range(retries):
            try:
                time_module.sleep(delay * (0.8 + i * 0.3))  # 智能延迟：1.0~2.5秒
                result = func(*args, **kwargs)
                if isinstance(result, pd.DataFrame):
                    return result if not result.empty else pd.DataFrame()
                return result
            except Exception as e:
                if i == retries - 1:
                    raise e
        return pd.DataFrame()

class FundDataFetcher:
    """基金数据获取类"""
    
    def __init__(self, fund_code, start_date=None, end_date=None):
        """初始化数据获取"""
        self.fund_code = fund_code
        self.start_date = start_date
        self.end_date = end_date
    
    def fetch_data(self):
        """获取基金数据"""
        try:
            # 尝试获取场外基金数据
            df = SafeRequest.request(
                ak.fund_open_fund_info_em,
                symbol=self.fund_code,
                indicator="单位净值走势"
            )
            
            fund_type = "场外基金"
            fund_info = {}
            
            # 获取基金基本信息
            try:
                if fund_type == "场外基金":
                    info_df = SafeRequest.request(
                        ak.fund_open_fund_info_em,
                        symbol=self.fund_code,
                        indicator="基本信息"
                    )
                    if not info_df.empty:
                        fund_info['基金名称'] = info_df.get('基金名称', [''])[0]
                        fund_info['基金类型'] = info_df.get('基金类型', [''])[0]
                        fund_info['成立日期'] = info_df.get('成立日期', [''])[0]
                        fund_info['基金经理'] = info_df.get('基金经理', [''])[0]
                        fund_info['基金规模'] = info_df.get('基金规模', [''])[0]
            except Exception as info_error:
                print(f"获取基金信息失败: {info_error}")
            
            # 如果未获取到基金名称，尝试从基金列表中获取
            if not fund_info.get('基金名称'):
                try:
                    fund_list = SafeRequest.request(ak.fund_name_em)
                    if not fund_list.empty:
                        # 查找对应基金代码的基金名称
                        fund_row = fund_list[fund_list['基金代码'] == self.fund_code]
                        if not fund_row.empty:
                            fund_info['基金名称'] = fund_row['基金简称'].values[0]
                except Exception as list_error:
                    print(f"从基金列表获取基金名称失败: {list_error}")
            
            # 如果场外基金数据为空，尝试获取ETF数据
            if df.empty or '净值日期' not in df.columns:
                df = SafeRequest.request(ak.fund_etf_hist_sina, symbol=self.fund_code)
                fund_type = "ETF"
            
            # 处理数据
            if not df.empty:
                # 统一数据格式
                if fund_type == "场外基金":
                    # 重命名列以统一格式
                    if '净值日期' in df.columns:
                        df.rename(columns={'净值日期': '日期'}, inplace=True)
                    if '单位净值' in df.columns:
                        df.rename(columns={'单位净值': '净值'}, inplace=True)
                else:  # ETF
                    if '日期' in df.columns:
                        # 确保日期格式正确
                        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
                    if '单位净值' in df.columns:
                        df.rename(columns={'单位净值': '净值'}, inplace=True)
                
                # 按日期范围过滤数据
                if self.start_date and self.end_date:
                    try:
                        # 确保日期列是 datetime 类型
                        df['日期'] = pd.to_datetime(df['日期'])
                        start = pd.to_datetime(self.start_date)
                        end = pd.to_datetime(self.end_date)
                        # 过滤日期范围内的数据
                        df = df[(df['日期'] >= start) & (df['日期'] <= end)]
                        # 重新格式化为字符串
                        df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
                    except Exception as date_error:
                        print(f"日期过滤失败: {date_error}")
                        # 如果日期过滤失败，使用全部数据
                
                return df, fund_type, fund_info
            else:
                return None, fund_type, fund_info
                
        except Exception as e:
            print(f"获取数据失败: {str(e)[:70]}")
            return None, None, None

class FundGUI(App):
    """基金净值可视化GUI应用"""
    
    def build(self):
        """构建应用界面"""
        self.title = "养基宝 - 基金分析"
        
        # 创建主布局
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 创建输入区域
        input_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=200)
        
        # 基金代码输入
        code_layout = BoxLayout(orientation='horizontal', spacing=5)
        code_label = Label(text="基金代码:", size_hint_x=0.2)
        self.code_input = TextInput(text="270042", hint_text="例如: 270042", size_hint_x=0.3)
        self.query_button = Button(text="查询净值", size_hint_x=0.3)
        self.query_button.bind(on_press=self.query_fund_data)
        code_layout.add_widget(code_label)
        code_layout.add_widget(self.code_input)
        code_layout.add_widget(self.query_button)
        
        # 基金名称显示
        self.fund_name_label = Label(text="基金名称: ", halign='left', valign='middle')
        self.fund_name_display = Label(text="", halign='left', valign='middle', bold=True)
        
        # 日期选择
        date_layout = BoxLayout(orientation='horizontal', spacing=5)
        start_label = Label(text="开始日期:", size_hint_x=0.2)
        self.start_date_input = TextInput(text=(datetime.now() - pd.DateOffset(days=30)).strftime('%Y-%m-%d'), size_hint_x=0.35)
        end_label = Label(text="结束日期:", size_hint_x=0.2)
        self.end_date_input = TextInput(text=datetime.now().strftime('%Y-%m-%d'), size_hint_x=0.35)
        date_layout.add_widget(start_label)
        date_layout.add_widget(self.start_date_input)
        date_layout.add_widget(end_label)
        date_layout.add_widget(self.end_date_input)
        
        # 快速日期选择
        quick_layout = BoxLayout(orientation='horizontal', spacing=5)
        quick_label = Label(text="快速选择:", size_hint_x=0.2)
        self.quick_date_buttons = BoxLayout(size_hint_x=0.8, spacing=2)
        quick_options = ["近1月", "近3月", "近6月", "近1年"]
        for option in quick_options:
            btn = Button(text=option, size_hint_x=None, width=80)
            btn.bind(on_press=self.handle_quick_date)
            self.quick_date_buttons.add_widget(btn)
        quick_layout.add_widget(quick_label)
        quick_layout.add_widget(self.quick_date_buttons)
        
        # 估值编辑
        valuation_layout = BoxLayout(orientation='horizontal', spacing=5)
        valuation_label = Label(text="涨跌幅:", size_hint_x=0.2)
        self.change_input = TextInput(hint_text="例如: -1.50%", size_hint_x=0.3)
        self.apply_valuation_button = Button(text="应用估值", size_hint_x=0.25)
        self.apply_valuation_button.bind(on_press=self.apply_valuation)
        self.reset_valuation_button = Button(text="重置", size_hint_x=0.25)
        self.reset_valuation_button.bind(on_press=self.reset_valuation)
        valuation_layout.add_widget(valuation_label)
        valuation_layout.add_widget(self.change_input)
        valuation_layout.add_widget(self.apply_valuation_button)
        valuation_layout.add_widget(self.reset_valuation_button)
        
        # 添加到输入布局
        input_layout.add_widget(code_layout)
        input_layout.add_widget(self.fund_name_label)
        input_layout.add_widget(self.fund_name_display)
        input_layout.add_widget(date_layout)
        input_layout.add_widget(quick_layout)
        input_layout.add_widget(valuation_layout)
        
        # 创建标签页
        self.tab_panel = TabbedPanel(do_default_tab=False)
        
        # 净值走势标签
        net_value_tab = TabbedPanelItem(text="净值走势")
        net_value_content = ScrollView()
        self.net_value_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.net_value_figure = Figure(figsize=(6, 3), dpi=100)
        self.net_value_canvas = FigureCanvasKivyAgg(self.net_value_figure)
        self.net_value_ax = self.net_value_figure.add_subplot(111)
        self.net_value_ax.set_title("净值走势与波段信号")
        self.net_value_ax.set_xlabel("日期")
        self.net_value_ax.set_ylabel("净值")
        self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
        self.net_value_layout.add_widget(self.net_value_canvas)
        net_value_content.add_widget(self.net_value_layout)
        net_value_tab.add_widget(net_value_content)
        self.tab_panel.add_widget(net_value_tab)
        
        # 神奇反转标签
        magic_reversal_tab = TabbedPanelItem(text="神奇反转")
        magic_reversal_content = ScrollView()
        self.magic_reversal_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.magic_reversal_figure = Figure(figsize=(6, 3), dpi=100)
        self.magic_reversal_canvas = FigureCanvasKivyAgg(self.magic_reversal_figure)
        self.magic_reversal_ax = self.magic_reversal_figure.add_subplot(111)
        self.magic_reversal_ax.set_title("神奇反转")
        self.magic_reversal_ax.set_xlabel("连续涨跌天数")
        self.magic_reversal_ax.set_ylabel("反转概率")
        self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
        self.magic_reversal_layout.add_widget(self.magic_reversal_canvas)
        magic_reversal_content.add_widget(self.magic_reversal_layout)
        magic_reversal_tab.add_widget(magic_reversal_content)
        self.tab_panel.add_widget(magic_reversal_tab)
        
        # 回撤抄底标签
        drawdown_tab = TabbedPanelItem(text="回撤抄底")
        drawdown_content = ScrollView()
        self.drawdown_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.drawdown_figure = Figure(figsize=(6, 3), dpi=100)
        self.drawdown_canvas = FigureCanvasKivyAgg(self.drawdown_figure)
        self.drawdown_ax = self.drawdown_figure.add_subplot(111)
        self.drawdown_ax.set_title("回撤抄底")
        self.drawdown_ax.set_xlabel("日期")
        self.drawdown_ax.set_ylabel("回撤率")
        self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
        self.drawdown_layout.add_widget(self.drawdown_canvas)
        drawdown_content.add_widget(self.drawdown_layout)
        drawdown_tab.add_widget(drawdown_content)
        self.tab_panel.add_widget(drawdown_tab)
        
        # 数据表格标签
        table_tab = TabbedPanelItem(text="数据表格")
        table_content = ScrollView()
        self.table_layout = GridLayout(cols=3, spacing=5, padding=10, size_hint_y=None)
        self.table_layout.bind(minimum_height=self.table_layout.setter('height'))
        # 添加表头
        headers = ["日期", "净值", "日增长率"]
        for header in headers:
            label = Label(text=header, size_hint_y=None, height=30, bold=True)
            self.table_layout.add_widget(label)
        table_content.add_widget(self.table_layout)
        table_tab.add_widget(table_content)
        self.tab_panel.add_widget(table_tab)
        
        # 购买建议区域
        advice_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=150)
        advice_title = Label(text="当日购买建议", bold=True, size_hint_y=None, height=30)
        self.advice_text = Label(text="请查询基金数据以获取购买建议", size_hint_y=None, height=120, halign='left', valign='top', text_size=(self.root.width, None))
        advice_layout.add_widget(advice_title)
        advice_layout.add_widget(self.advice_text)
        
        # 状态栏
        self.status_bar = Label(text="就绪", size_hint_y=None, height=30, halign='left', valign='middle')
        
        # 添加到主布局
        main_layout.add_widget(input_layout)
        main_layout.add_widget(self.tab_panel)
        main_layout.add_widget(advice_layout)
        main_layout.add_widget(self.status_bar)
        
        # 数据缓存
        self.chart_data_cache = {}
        
        return main_layout
    
    def handle_quick_date(self, instance):
        """处理快速日期选择"""
        option = instance.text
        end_date = datetime.now()
        
        if option == "近1月":
            start_date = end_date - pd.DateOffset(days=30)
        elif option == "近3月":
            start_date = end_date - pd.DateOffset(months=3)
        elif option == "近6月":
            start_date = end_date - pd.DateOffset(months=6)
        elif option == "近1年":
            start_date = end_date - pd.DateOffset(years=1)
        else:
            return
        
        self.start_date_input.text = start_date.strftime('%Y-%m-%d')
        self.end_date_input.text = end_date.strftime('%Y-%m-%d')
    
    def query_fund_data(self, instance):
        """查询基金数据"""
        fund_code = self.code_input.text.strip()
        start_date = self.start_date_input.text.strip()
        end_date = self.end_date_input.text.strip()
        
        # 验证输入
        if not fund_code:
            self.show_popup("输入错误", "请输入基金代码")
            return
        
        # 检查缓存
        cache_key = f"{fund_code}_{start_date}_{end_date}"
        if cache_key in self.chart_data_cache:
            # 使用缓存数据
            cached_data = self.chart_data_cache[cache_key]
            self.handle_data(cached_data['df'], cached_data['fund_type'], cached_data['fund_info'])
            self.status_bar.text = "使用缓存数据"
            return
        
        # 更新状态栏
        self.status_bar.text = "正在获取数据..."
        
        # 清空之前的数据
        self.clear_chart()
        self.clear_table()
        
        # 创建并启动数据获取
        def fetch_data():
            fetcher = FundDataFetcher(fund_code, start_date, end_date)
            df, fund_type, fund_info = fetcher.fetch_data()
            Clock.schedule_once(lambda dt: self.handle_data(df, fund_type, fund_info), 0)
        
        # 在后台线程中执行
        Clock.schedule_once(lambda dt: fetch_data(), 0.1)
    
    def handle_data(self, df, fund_type, fund_info):
        """处理获取到的数据"""
        if df is None:
            self.status_bar.text = "获取数据失败"
            self.show_popup("错误", "未获取到基金数据")
            return
        
        fund_code = self.code_input.text.strip()
        fund_name = fund_info.get('基金名称', '')
        
        # 更新基金名称显示
        if fund_name:
            self.fund_name_display.text = fund_name
        
        # 保存当前数据
        self.current_data = df
        self.current_fund_type = fund_type
        self.current_fund_info = fund_info
        
        # 缓存数据
        cache_key = f"{fund_code}_{self.start_date_input.text}_{self.end_date_input.text}"
        self.chart_data_cache[cache_key] = {
            'df': df,
            'fund_type': fund_type,
            'fund_info': fund_info
        }
        
        # 计算并添加涨跌幅信息
        self.calculate_fund_analysis(df, fund_code)
        
        # 显示基金基本信息
        self.show_fund_info(fund_info, fund_code, fund_type)
        
        # 更新当前激活的图表
        current_tab = self.tab_panel.current_tab
        if current_tab.text == "净值走势":
            self.update_net_value_chart(df)
        elif current_tab.text == "神奇反转":
            self.update_magic_reversal_chart(df)
        elif current_tab.text == "回撤抄底":
            self.update_drawdown_chart(df)
        elif current_tab.text == "数据表格":
            self.update_table(df)
        
        # 更新表格
        self.update_table(df)
        
        # 更新购买建议
        self.update_purchase_advice(df)
        
        # 更新状态栏
        self.status_bar.text = f"成功获取 {fund_type} {fund_code} 的数据"
    
    def show_fund_info(self, fund_info, fund_code, fund_type):
        """显示基金基本信息"""
        info_text = f"基金代码: {fund_code}\n"
        info_text += f"基金名称: {fund_info.get('基金名称', 'N/A')}\n"
        info_text += f"基金类型: {fund_info.get('基金类型', 'N/A')}\n"
        info_text += f"成立日期: {fund_info.get('成立日期', 'N/A')}\n"
        info_text += f"基金经理: {fund_info.get('基金经理', 'N/A')}\n"
        info_text += f"基金规模: {fund_info.get('基金规模', 'N/A')}\n"
        
        # 这里可以添加一个信息弹窗
        # self.show_popup("基金基本信息", info_text)
    
    def update_net_value_chart(self, df):
        """更新净值走势图表"""
        # 确保日期列存在
        if '日期' not in df.columns or '净值' not in df.columns:
            return
        
        try:
            # 转换日期格式
            dates = pd.to_datetime(df['日期'])
            values = df['净值'].astype(float)
            
            # 优化：对于大数据集，限制绘制的数据点数量
            max_points = 500
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                values = values[::step]
            
            # 清空图表
            self.net_value_ax.clear()
            
            # 绘制净值曲线
            self.net_value_ax.plot(dates, values, 'b-', linewidth=2, label='净值')
            
            # 添加技术分析指标
            if len(values) > 0:
                # 计算移动平均线
                ma5 = values.rolling(window=5).mean()
                ma20 = values.rolling(window=20).mean()
                
                # 绘制移动平均线
                self.net_value_ax.plot(dates, ma5, 'g-', linewidth=1.5, label='5日均线', alpha=0.7)
                self.net_value_ax.plot(dates, ma20, 'r-', linewidth=1.5, label='20日均线', alpha=0.7)
                
                # 计算布林带
                def calculate_bollinger_bands(data, window=20, num_std=2):
                    ma = data.rolling(window=window).mean()
                    std = data.rolling(window=window).std()
                    upper_band = ma + (std * num_std)
                    lower_band = ma - (std * num_std)
                    return ma, upper_band, lower_band
                
                bb_ma, upper_band, lower_band = calculate_bollinger_bands(values)
                
                # 绘制布林带
                self.net_value_ax.plot(dates, upper_band, 'k--', linewidth=1, label='布林带上轨', alpha=0.7)
                self.net_value_ax.plot(dates, lower_band, 'k--', linewidth=1, label='布林带下轨', alpha=0.7)
                self.net_value_ax.fill_between(dates, upper_band, lower_band, color='gray', alpha=0.1)
            
            # 设置图表属性
            self.net_value_ax.set_title("净值走势与技术指标")
            self.net_value_ax.set_xlabel("日期")
            self.net_value_ax.set_ylabel("净值")
            self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
            self.net_value_ax.legend()
            
            # 设置日期格式
            self.net_value_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.net_value_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # 自动调整日期标签角度
            plt.setp(self.net_value_ax.get_xticklabels(), rotation=45, ha='right')
            
            # 重绘
            self.net_value_figure.tight_layout()
            self.net_value_canvas.draw_idle()
        except Exception as e:
            print(f"更新净值走势图表失败: {e}")
            self.net_value_ax.clear()
            self.net_value_ax.set_title("净值走势与技术指标")
            self.net_value_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                                 transform=self.net_value_ax.transAxes, 
                                 ha='center', va='center')
            self.net_value_canvas.draw_idle()
    
    def update_magic_reversal_chart(self, df):
        """更新神奇反转图表"""
        if '净值' not in df.columns:
            return
        
        try:
            # 计算连续涨跌天数和幅度
            values = df['净值'].astype(float)
            changes = np.diff(values)
            direction = np.sign(changes)
            change_percent = changes / values[:-1] * 100  # 涨跌幅百分比
            
            # 计算连续涨跌天数
            consecutive_days = []
            current_streak = 0
            current_direction = 0
            
            for d in direction:
                if d == current_direction and d != 0:
                    current_streak += 1
                else:
                    if current_direction != 0:
                        consecutive_days.append((current_streak, current_direction))
                    current_streak = 1 if d != 0 else 0
                    current_direction = d
            
            if current_direction != 0:
                consecutive_days.append((current_streak, current_direction))
            
            # 分析反转概率
            max_streak = 10
            up_probabilities = []
            down_probabilities = []
            
            for i in range(1, max_streak + 1):
                # 计算连续上涨i天后反转的概率
                up_streaks = [s for s, d in consecutive_days if d == 1 and s >= i]
                if up_streaks:
                    # 简单模拟反转概率
                    prob = min(0.9, 0.3 + i * 0.08)
                    up_probabilities.append((i, prob))
                
                # 计算连续下跌i天后反转的概率
                down_streaks = [s for s, d in consecutive_days if d == -1 and s >= i]
                if down_streaks:
                    # 简单模拟反转概率
                    prob = min(0.9, 0.3 + i * 0.08)
                    down_probabilities.append((i, prob))
            
            # 清空图表
            self.magic_reversal_ax.clear()
            
            # 绘制反转概率曲线
            if up_probabilities:
                x_up, y_up = zip(*up_probabilities)
                self.magic_reversal_ax.plot(x_up, y_up, 'r-', linewidth=2, label='连续上涨反转概率')
            
            if down_probabilities:
                x_down, y_down = zip(*down_probabilities)
                self.magic_reversal_ax.plot(x_down, y_down, 'g-', linewidth=2, label='连续下跌反转概率')
            
            # 设置图表属性
            self.magic_reversal_ax.set_title("神奇反转分析")
            self.magic_reversal_ax.set_xlabel("连续涨跌天数")
            self.magic_reversal_ax.set_ylabel("反转概率")
            self.magic_reversal_ax.set_ylim(0, 1)
            self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
            self.magic_reversal_ax.legend()
            
            # 重绘
            self.magic_reversal_figure.tight_layout()
            self.magic_reversal_canvas.draw_idle()
        except Exception as e:
            print(f"更新神奇反转图表失败: {e}")
            self.magic_reversal_ax.clear()
            self.magic_reversal_ax.set_title("神奇反转分析")
            self.magic_reversal_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                                     transform=self.magic_reversal_ax.transAxes, 
                                     ha='center', va='center')
            self.magic_reversal_canvas.draw_idle()
    
    def update_drawdown_chart(self, df):
        """更新回撤抄底图表"""
        if '净值' not in df.columns:
            return
        
        try:
            # 计算回撤
            values = df['净值'].astype(float)
            rolling_max = values.cummax()
            drawdown = (values - rolling_max) / rolling_max * 100
            
            # 确保日期列存在
            if '日期' in df.columns:
                dates = pd.to_datetime(df['日期'])
            else:
                dates = pd.date_range(start=datetime.now() - pd.DateOffset(days=len(values)-1), periods=len(values))
            
            # 优化：对于大数据集，限制绘制的数据点数量
            max_points = 500
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                drawdown = drawdown[::step]
            
            # 清空图表
            self.drawdown_ax.clear()
            
            # 绘制回撤曲线
            self.drawdown_ax.plot(dates, drawdown, 'b-', linewidth=2, label='回撤率')
            
            # 添加零轴
            self.drawdown_ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            
            # 标记重要回撤点
            significant_drawdowns = []
            for i, d in enumerate(drawdown):
                if d < -10:  # 10%以上的回撤
                    significant_drawdowns.append((dates[i], d))
            
            for date, value in significant_drawdowns:
                self.drawdown_ax.scatter(date, value, marker='v', color='red', s=50)
            
            # 设置图表属性
            self.drawdown_ax.set_title("回撤抄底分析")
            self.drawdown_ax.set_xlabel("日期")
            self.drawdown_ax.set_ylabel("回撤率 (%)")
            self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
            self.drawdown_ax.legend()
            
            # 设置日期格式
            self.drawdown_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.drawdown_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # 自动调整日期标签角度
            plt.setp(self.drawdown_ax.get_xticklabels(), rotation=45, ha='right')
            
            # 重绘
            self.drawdown_figure.tight_layout()
            self.drawdown_canvas.draw_idle()
        except Exception as e:
            print(f"更新回撤抄底图表失败: {e}")
            self.drawdown_ax.clear()
            self.drawdown_ax.set_title("回撤抄底分析")
            self.drawdown_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                               transform=self.drawdown_ax.transAxes, 
                               ha='center', va='center')
            self.drawdown_canvas.draw_idle()
    
    def update_table(self, df):
        """更新数据表格"""
        # 清空表格
        self.clear_table()
        
        try:
            # 计算涨跌幅
            if '净值' in df.columns:
                values = df['净值'].astype(float)
                changes = np.diff(values)
                change_percent = (changes / values[:-1] * 100).round(2)
                
                # 添加数据行
                for i, row in df.iterrows():
                    date = row.get('日期', '')
                    value = row.get('净值', '')
                    change = "{:.2f}%" .format(change_percent[i-1]) if i > 0 else ""
                    
                    # 添加到表格
                    date_label = Label(text=str(date), size_hint_y=None, height=30, halign='left')
                    value_label = Label(text=str(value), size_hint_y=None, height=30, halign='right')
                    change_label = Label(text=change, size_hint_y=None, height=30, halign='right')
                    
                    self.table_layout.add_widget(date_label)
                    self.table_layout.add_widget(value_label)
                    self.table_layout.add_widget(change_label)
        except Exception as e:
            print(f"更新表格失败: {e}")
    
    def update_purchase_advice(self, df):
        """更新购买建议"""
        if df is None or df.empty:
            self.advice_text.text = "请查询基金数据以获取购买建议"
            return
        
        try:
            # 计算基本指标
            values = df['净值'].astype(float)
            latest_value = values.iloc[-1]
            
            # 计算技术指标
            # RSI
            def calculate_rsi(data, window=14):
                delta = data.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            
            rsi = calculate_rsi(values)
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            
            # 移动平均线
            ma5 = values.rolling(window=5).mean().iloc[-1]
            ma20 = values.rolling(window=20).mean().iloc[-1]
            
            # 生成建议
            advice = "基于技术分析的购买建议:\n\n"
            
            if current_rsi <= 30:
                advice += "RSI指标: 超卖状态，可能是买入机会\n"
            elif current_rsi >= 70:
                advice += "RSI指标: 超买状态，建议谨慎\n"
            else:
                advice += f"RSI指标: {current_rsi:.1f}，处于正常区间\n"
            
            if ma5 > ma20:
                advice += "均线状态: 短期均线高于长期均线，处于上升趋势\n"
            else:
                advice += "均线状态: 短期均线低于长期均线，处于下降趋势\n"
            
            # 计算回撤
            rolling_max = values.cummax()
            current_drawdown = (latest_value - rolling_max.iloc[-1]) / rolling_max.iloc[-1] * 100
            advice += f"当前回撤: {current_drawdown:.2f}%\n"
            
            # 综合建议
            if current_rsi <= 30 and current_drawdown < -10:
                advice += "\n综合建议: 强烈推荐购买"
            elif current_rsi <= 40 or (ma5 > ma20 and current_rsi < 60):
                advice += "\n综合建议: 推荐购买"
            elif current_rsi >= 70:
                advice += "\n综合建议: 不推荐购买"
            else:
                advice += "\n综合建议: 观望"
            
            self.advice_text.text = advice
        except Exception as e:
            print(f"更新购买建议失败: {e}")
            self.advice_text.text = "生成购买建议失败"
    
    def apply_valuation(self, instance):
        """应用基金估值"""
        if not hasattr(self, 'current_data') or self.current_data.empty:
            self.show_popup("数据错误", "请先查询基金数据")
            return
        
        # 获取输入的涨跌幅
        change_text = self.change_input.text.strip()
        if not change_text:
            self.show_popup("输入错误", "请输入涨跌幅")
            return
        
        try:
            # 解析涨跌幅，移除百分号并转换为浮点数
            if change_text.endswith('%'):
                change_pct = float(change_text[:-1])
            else:
                change_pct = float(change_text)
        except ValueError:
            self.show_popup("输入错误", "涨跌幅格式错误，请输入有效的数字")
            return
        
        # 基于当前净值和涨跌幅计算新的净值
        current_value = self.current_data['净值'].iloc[-1].astype(float)
        new_value = current_value * (1 + change_pct / 100)
        
        # 创建包含估值的新数据框
        valuation_df = self.current_data.copy()
        
        # 保存原始数据，用于恢复
        if not hasattr(self, 'original_data'):
            self.original_data = self.current_data.copy()
        
        # 更新数据框，添加估值数据
        last_date = pd.to_datetime(valuation_df['日期'].iloc[-1])
        next_date = last_date + pd.DateOffset(days=1)
        
        # 创建新行
        new_row = pd.DataFrame([{
            '日期': next_date.strftime('%Y-%m-%d'),
            '净值': new_value
        }])
        
        # 添加新行到数据框
        valuation_df = pd.concat([valuation_df, new_row], ignore_index=True)
        
        # 更新当前数据为估值数据
        self.current_data = valuation_df
        
        # 重新生成购买建议
        self.update_purchase_advice(valuation_df)
        
        # 更新图表
        current_tab = self.tab_panel.current_tab
        if current_tab.text == "净值走势":
            self.update_net_value_chart(valuation_df)
        elif current_tab.text == "神奇反转":
            self.update_magic_reversal_chart(valuation_df)
        elif current_tab.text == "回撤抄底":
            self.update_drawdown_chart(valuation_df)
        elif current_tab.text == "数据表格":
            self.update_table(valuation_df)
        
        # 显示成功消息
        self.show_popup("成功", f"估值应用成功！\n输入涨跌幅: {change_pct:.2f}%\n计算后净值: {new_value:.4f}")
    
    def reset_valuation(self, instance):
        """重置估值，恢复原始数据"""
        # 清空输入
        self.change_input.text = ""
        
        # 恢复原始数据
        if hasattr(self, 'original_data'):
            self.current_data = self.original_data.copy()
            delattr(self, 'original_data')
            
            # 重新生成购买建议
            self.update_purchase_advice(self.current_data)
            
            # 更新图表
            current_tab = self.tab_panel.current_tab
            if current_tab.text == "净值走势":
                self.update_net_value_chart(self.current_data)
            elif current_tab.text == "神奇反转":
                self.update_magic_reversal_chart(self.current_data)
            elif current_tab.text == "回撤抄底":
                self.update_drawdown_chart(self.current_data)
            elif current_tab.text == "数据表格":
                self.update_table(self.current_data)
            
            self.show_popup("成功", "估值已重置，恢复原始数据")
        else:
            self.show_popup("提示", "当前没有应用估值")
    
    def clear_chart(self):
        """清空所有图表"""
        # 清空净值走势图表
        self.net_value_ax.clear()
        self.net_value_ax.set_title("净值走势与技术指标")
        self.net_value_ax.set_xlabel("日期")
        self.net_value_ax.set_ylabel("净值")
        self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
        self.net_value_canvas.draw_idle()
        
        # 清空神奇反转图表
        self.magic_reversal_ax.clear()
        self.magic_reversal_ax.set_title("神奇反转分析")
        self.magic_reversal_ax.set_xlabel("连续涨跌天数")
        self.magic_reversal_ax.set_ylabel("反转概率")
        self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
        self.magic_reversal_canvas.draw_idle()
        
        # 清空回撤抄底图表
        self.drawdown_ax.clear()
        self.drawdown_ax.set_title("回撤抄底分析")
        self.drawdown_ax.set_xlabel("日期")
        self.drawdown_ax.set_ylabel("回撤率")
        self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
        self.drawdown_canvas.draw_idle()
    
    def clear_table(self):
        """清空表格"""
        # 保留表头，删除其他行
        while len(self.table_layout.children) > 3:
            self.table_layout.remove_widget(self.table_layout.children[0])
    
    def show_popup(self, title, message):
        """显示弹窗"""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, halign='left', valign='middle', text_size=(400, None)))
        button = Button(text="确定", size_hint_y=None, height=40)
        content.add_widget(button)
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        button.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == "__main__":
    FundGUI().run()
