# -*- coding: utf-8 -*-
"""
养基宝 - 模拟持仓管理系统
使用PyQt5和Matplotlib实现基金持仓管理和收益分析功能
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
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QStatusBar, QDateEdit, QComboBox, QStackedWidget,
    QFileDialog, QDoubleSpinBox, QSpinBox, QTabWidget, QDialog, QFormLayout, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# 抑制Matplotlib字体警告
matplotlib.rcParams.update({
    'font.family': ['SimHei', 'Microsoft YaHei', 'sans-serif'],
    'axes.unicode_minus': False,  # 解决负号显示问题
    'figure.figsize': (8, 4),
    'figure.dpi': 100,
    'font.size': 12,  # 全局字体大小
    'axes.titlesize': 14,  # 图表标题字体大小
    'axes.labelsize': 12,  # 坐标轴标签字体大小
    'xtick.labelsize': 10,  # x轴刻度字体大小
    'ytick.labelsize': 10,  # y轴刻度字体大小
    'legend.fontsize': 10,  # 图例字体大小
    'axes.linewidth': 1.5  # 坐标轴线条粗细
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

class FundDataFetcher(QThread):
    """基金数据获取线程"""
    
    # 信号定义
    data_fetched = pyqtSignal(pd.DataFrame, str, dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, fund_code, start_date=None, end_date=None):
        """初始化数据获取线程"""
        super().__init__()
        self.fund_code = fund_code
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        """运行数据获取任务"""
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
                
                if not df.empty:
                    self.data_fetched.emit(df, fund_type, fund_info)
                else:
                    self.error_occurred.emit(f"指定日期范围内未获取到基金 {self.fund_code} 的数据")
            else:
                self.error_occurred.emit(f"未获取到基金 {self.fund_code} 的数据")
                
        except Exception as e:
            self.error_occurred.emit(f"获取数据失败: {str(e)[:70]}")

class PurchaseAdviceDialog(QDialog):
    """购买建议对话框"""
    
    def __init__(self, parent=None, advice_data=None):
        """初始化购买建议对话框"""
        super().__init__(parent)
        self.setWindowTitle("当日购买建议")
        self.setGeometry(300, 200, 500, 400)
        self.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 添加标题
        title = QLabel("基于算法分析的购买建议")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 添加建议内容
        if advice_data:
            # 基金基本信息
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.addWidget(QLabel(f"基金代码: {advice_data.get('fund_code', 'N/A')}"))
            info_layout.addWidget(QLabel(f"基金名称: {advice_data.get('fund_name', 'N/A')}"))
            info_layout.addWidget(QLabel(f"分析日期: {advice_data.get('analysis_date', 'N/A')}"))
            layout.addWidget(info_widget)
            
            # 水平分隔线
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            layout.addWidget(separator)
            
            # 算法分析结果
            analysis_widget = QWidget()
            analysis_layout = QVBoxLayout(analysis_widget)
            
            # 波段信号分析
            band_signal = advice_data.get('band_signal', {})
            band_widget = QWidget()
            band_layout = QVBoxLayout(band_widget)
            band_layout.addWidget(QLabel("<b>波段信号分析:</b>"))
            band_layout.addWidget(QLabel(f"信号状态: {band_signal.get('status', 'N/A')}"))
            band_layout.addWidget(QLabel(f"RSI指标: {band_signal.get('rsi', 'N/A')}"))
            band_layout.addWidget(QLabel(f"建议操作: {band_signal.get('advice', 'N/A')}"))
            analysis_layout.addWidget(band_widget)
            
            # 回撤抄底分析
            drawdown = advice_data.get('drawdown', {})
            drawdown_widget = QWidget()
            drawdown_layout = QVBoxLayout(drawdown_widget)
            drawdown_layout.addWidget(QLabel("<b>回撤抄底分析:</b>"))
            drawdown_layout.addWidget(QLabel(f"当前回撤: {drawdown.get('current_drawdown', 'N/A')}"))
            drawdown_layout.addWidget(QLabel(f"抄底胜率: {drawdown.get('win_rate', 'N/A')}"))
            drawdown_layout.addWidget(QLabel(f"建议操作: {drawdown.get('advice', 'N/A')}"))
            analysis_layout.addWidget(drawdown_widget)
            
            # 神奇反转分析
            magic_reversal = advice_data.get('magic_reversal', {})
            reversal_widget = QWidget()
            reversal_layout = QVBoxLayout(reversal_widget)
            reversal_layout.addWidget(QLabel("<b>神奇反转分析:</b>"))
            reversal_layout.addWidget(QLabel(f"连续涨跌: {magic_reversal.get('streak', 'N/A')}"))
            reversal_layout.addWidget(QLabel(f"反转概率: {magic_reversal.get('probability', 'N/A')}"))
            reversal_layout.addWidget(QLabel(f"建议操作: {magic_reversal.get('advice', 'N/A')}"))
            analysis_layout.addWidget(reversal_widget)
            
            layout.addWidget(analysis_widget)
            
            # 水平分隔线
            separator2 = QFrame()
            separator2.setFrameShape(QFrame.HLine)
            separator2.setFrameShadow(QFrame.Sunken)
            layout.addWidget(separator2)
            
            # 综合建议
            summary_widget = QWidget()
            summary_layout = QVBoxLayout(summary_widget)
            summary_layout.addWidget(QLabel("<b>综合建议:</b>"))
            summary_layout.addWidget(QLabel(advice_data.get('summary_advice', '无建议')))
            
            # 建议级别
            advice_level = advice_data.get('advice_level', 'neutral')
            level_color = {
                'strong_buy': 'green',
                'buy': 'lightgreen',
                'neutral': 'blue',
                'sell': 'orange',
                'strong_sell': 'red'
            }.get(advice_level, 'blue')
            
            level_text = {
                'strong_buy': '强烈推荐购买',
                'buy': '推荐购买',
                'neutral': '观望',
                'sell': '不推荐购买',
                'strong_sell': '强烈不推荐购买'
            }.get(advice_level, '观望')
            
            level_label = QLabel(f"建议级别: {level_text}")
            level_label.setStyleSheet(f"background-color: {level_color}; padding: 5px;")
            summary_layout.addWidget(level_label)
            layout.addWidget(summary_widget)
        else:
            layout.addWidget(QLabel("暂无足够数据生成购买建议"))
        
        # 添加按钮
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addWidget(button_widget)

class FundGUI(QMainWindow):
    """基金净值可视化GUI主窗口"""
    
    def __init__(self):
        """初始化GUI主窗口"""
        super().__init__()
        self.setWindowTitle("养基宝 - 基金净值可视化")
        self.setGeometry(100, 100, 1000, 700)
        
        # 设置字体
        self.setFont(QFont("Microsoft YaHei", 9))
        
        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建输入区域
        self.create_input_area()
        
        # 创建图表区域
        self.create_chart_area()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 数据获取线程
        self.data_thread = None
    
    def create_input_area(self):
        """创建输入区域"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        # 第一行：基金代码和查询按钮
        top_layout = QHBoxLayout()
        code_label = QLabel("基金代码:")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("例如: 270042")
        self.code_input.setText("270042")  # 默认值
        # 基金名称显示
        self.fund_name_label = QLabel("基金名称: ")
        self.fund_name_display = QLabel("")
        self.fund_name_display.setStyleSheet("font-weight: bold")
        
        # 查询按钮
        self.query_button = QPushButton("查询净值")
        self.query_button.clicked.connect(self.query_fund_data)
        
        # 导出按钮
        self.export_button = QPushButton("导出数据")
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setEnabled(False)  # 默认禁用
        
        top_layout.addWidget(code_label)
        top_layout.addWidget(self.code_input)
        top_layout.addWidget(self.fund_name_label)
        top_layout.addWidget(self.fund_name_display)
        top_layout.addWidget(self.query_button)
        top_layout.addWidget(self.export_button)
        top_layout.addStretch()
        
        # 第二行：日期选择
        date_layout = QHBoxLayout()
        start_label = QLabel("开始日期:")
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)  # 启用日历弹出
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")  # 设置日期格式
        # 设置默认开始日期为30天前
        default_start = QDate.currentDate().addDays(-30)
        self.start_date_input.setDate(default_start)
        
        end_label = QLabel("结束日期:")
        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)  # 启用日历弹出
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")  # 设置日期格式
        # 设置默认结束日期为今天
        default_end = QDate.currentDate()
        self.end_date_input.setDate(default_end)
        
        # 快速日期选择
        quick_label = QLabel("快速选择:")
        self.quick_date_combo = QComboBox()
        self.quick_date_combo.addItems(["近1月", "近3月", "近6月", "近1年", "今年以来", "近3年", "近5年", "成立以来"])
        self.quick_date_combo.currentIndexChanged.connect(self.handle_quick_date_change)
        
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_input)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_input)
        date_layout.addWidget(quick_label)
        date_layout.addWidget(self.quick_date_combo)
        date_layout.addStretch()
        
        # 添加到主输入布局
        input_layout.addLayout(top_layout)
        input_layout.addLayout(date_layout)
        
        # 第三行：基金基本信息
        self.info_widget = QWidget()
        self.info_layout = QHBoxLayout(self.info_widget)
        self.info_layout.addStretch()
        
        # 第四行：基金估值编辑（新增）
        self.valuation_widget = QWidget()
        self.valuation_layout = QHBoxLayout(self.valuation_widget)
        
        # 估值标题
        valuation_label = QLabel("基金估值编辑：")
        self.valuation_layout.addWidget(valuation_label)
        
        # 涨跌幅输入
        self.change_input = QLineEdit()
        self.change_input.setPlaceholderText("输入第二天涨跌幅（例如：-1.50%）")
        self.change_input.setMaximumWidth(150)
        self.valuation_layout.addWidget(self.change_input)
        
        # 应用估值按钮
        self.apply_valuation_button = QPushButton("应用估值")
        self.apply_valuation_button.clicked.connect(self.apply_valuation)
        self.valuation_layout.addWidget(self.apply_valuation_button)
        
        # 重置按钮
        self.reset_valuation_button = QPushButton("重置")
        self.reset_valuation_button.clicked.connect(self.reset_valuation)
        self.valuation_layout.addWidget(self.reset_valuation_button)
        
        # 导出估值按钮
        self.export_valuation_button = QPushButton("导出估值")
        self.export_valuation_button.clicked.connect(self.export_valuation)
        self.valuation_layout.addWidget(self.export_valuation_button)
        
        self.valuation_layout.addStretch()
        
        # 添加到主输入布局
        input_layout.addWidget(self.info_widget)
        input_layout.addWidget(self.valuation_widget)
        
        # 添加到主布局
        self.main_layout.addWidget(input_widget)
    
    def create_chart_area(self):
        """创建图表区域"""
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        # 图表标题
        self.chart_title = QLabel("基金净值走势图")
        self.chart_title.setAlignment(Qt.AlignCenter)
        self.chart_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        chart_layout.addWidget(self.chart_title)
        
        # 添加功能选项卡
        self.chart_tab_widget = QTabWidget()
        self.chart_tab_widget.currentChanged.connect(self.handle_chart_tab_change)
        
        # 1. 净值走势与波段信号合并模块
        self.net_value_tab = QWidget()
        self.net_value_layout = QVBoxLayout(self.net_value_tab)
        # 创建Matplotlib画布
        self.net_value_figure = Figure(figsize=(8, 4), dpi=100)
        self.net_value_canvas = FigureCanvas(self.net_value_figure)
        # 初始化图表
        self.net_value_ax = self.net_value_figure.add_subplot(111)
        self.net_value_ax.set_title("净值走势与波段信号")
        self.net_value_ax.set_xlabel("日期")
        self.net_value_ax.set_ylabel("净值")
        self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
        self.net_value_layout.addWidget(self.net_value_canvas)
        self.chart_tab_widget.addTab(self.net_value_tab, "净值走势")
        
        # 2. 神奇反转模块
        self.magic_reversal_tab = QWidget()
        self.magic_reversal_layout = QVBoxLayout(self.magic_reversal_tab)
        # 创建Matplotlib画布
        self.magic_reversal_figure = Figure(figsize=(8, 4), dpi=100)
        self.magic_reversal_canvas = FigureCanvas(self.magic_reversal_figure)
        # 初始化图表
        self.magic_reversal_ax = self.magic_reversal_figure.add_subplot(111)
        self.magic_reversal_ax.set_title("神奇反转")
        self.magic_reversal_ax.set_xlabel("连续涨跌天数")
        self.magic_reversal_ax.set_ylabel("反转概率")
        self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
        self.magic_reversal_layout.addWidget(self.magic_reversal_canvas)
        self.chart_tab_widget.addTab(self.magic_reversal_tab, "神奇反转")
        
        # 3. 回撤抄底模块
        self.drawdown_tab = QWidget()
        self.drawdown_layout = QVBoxLayout(self.drawdown_tab)
        # 创建Matplotlib画布
        self.drawdown_figure = Figure(figsize=(8, 4), dpi=100)
        self.drawdown_canvas = FigureCanvas(self.drawdown_figure)
        # 初始化图表
        self.drawdown_ax = self.drawdown_figure.add_subplot(111)
        self.drawdown_ax.set_title("回撤抄底")
        self.drawdown_ax.set_xlabel("日期")
        self.drawdown_ax.set_ylabel("回撤率")
        self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
        self.drawdown_layout.addWidget(self.drawdown_canvas)
        self.chart_tab_widget.addTab(self.drawdown_tab, "回撤抄底")
        
        # 4. 数据表格模块
        self.table_tab = QWidget()
        self.table_layout = QVBoxLayout(self.table_tab)
        # 表格标题
        self.table_title = QLabel("基金净值详细数据")
        self.table_title.setAlignment(Qt.AlignCenter)
        self.table_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.table_layout.addWidget(self.table_title)
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["日期", "净值", "日增长率"])
        # 设置表格属性
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_layout.addWidget(self.table)
        self.chart_tab_widget.addTab(self.table_tab, "数据表格")
        
        # 添加到布局
        chart_layout.addWidget(self.chart_tab_widget)
        
        # 数据缓存
        self.chart_data_cache = {}
        
        # 添加购买建议区域
        advice_widget = QWidget()
        advice_layout = QVBoxLayout(advice_widget)
        
        # 建议标题
        advice_title = QLabel("当日购买建议")
        advice_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        advice_layout.addWidget(advice_title)
        
        # 建议内容文本框
        self.advice_text = QLabel("请查询基金数据以获取购买建议")
        self.advice_text.setWordWrap(True)
        self.advice_text.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        advice_layout.addWidget(self.advice_text)
        
        # 添加到图表布局
        chart_layout.addWidget(advice_widget)
        
        # 添加到主布局
        self.main_layout.addWidget(chart_widget)
    

    
    def query_fund_data(self):
        """查询基金数据"""
        fund_code = self.code_input.text().strip()
        
        # 获取日期值
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")
        
        # 验证输入
        if not fund_code:
            QMessageBox.warning(self, "输入错误", "请输入基金代码")
            return
        
        # 检查缓存
        cache_key = f"{fund_code}_{start_date}_{end_date}"
        if cache_key in self.chart_data_cache:
            # 使用缓存数据
            cached_data = self.chart_data_cache[cache_key]
            self.handle_data(cached_data['df'], cached_data['fund_type'], cached_data['fund_info'])
            self.query_button.setEnabled(True)
            self.status_bar.showMessage("使用缓存数据")
            return
        
        # 禁用查询按钮
        self.query_button.setEnabled(False)
        self.status_bar.showMessage("正在获取数据...")
        
        # 清空之前的数据
        self.clear_chart()
        self.clear_table()
        
        # 创建并启动数据获取线程
        self.data_thread = FundDataFetcher(fund_code, start_date, end_date)
        self.data_thread.data_fetched.connect(self.handle_data)
        self.data_thread.error_occurred.connect(self.handle_error)
        self.data_thread.finished.connect(self.reset_ui)
        self.data_thread.start()
    
    def handle_data(self, df, fund_type, fund_info):
        """处理获取到的数据"""
        fund_code = self.code_input.text().strip()
        fund_name = fund_info.get('基金名称', '')
        
        # 更新基金名称显示
        if fund_name:
            self.fund_name_display.setText(fund_name)
        
        # 更新图表标题，包含基金中文名称
        if fund_name:
            self.chart_title.setText(f"{fund_type} {fund_code} - {fund_name} 分析")
        else:
            self.chart_title.setText(f"{fund_type} {fund_code} 分析")
        
        # 保存当前数据
        self.current_data = df
        self.current_fund_type = fund_type
        self.current_fund_info = fund_info
        
        # 缓存数据
        cache_key = f"{fund_code}_{self.start_date_input.date().toString('yyyy-MM-dd')}_{self.end_date_input.date().toString('yyyy-MM-dd')}"
        self.chart_data_cache[cache_key] = {
            'df': df,
            'fund_type': fund_type,
            'fund_info': fund_info
        }
        
        # 计算并添加涨跌幅信息
        fund_analysis = self.calculate_fund_analysis(df, fund_code)
        self.current_fund_analysis = fund_analysis
        
            # 显示基金基本信息
        self.show_fund_info(fund_info, fund_code, fund_type, fund_analysis)
        
        # 只更新当前激活的图表模块，其他模块在切换时按需更新
        current_tab_index = self.chart_tab_widget.currentIndex()
        if current_tab_index == 0:  # 净值走势（合并了波段信号）
            self.update_net_value_chart(df)
        elif current_tab_index == 1:  # 神奇反转
            self.update_magic_reversal_chart(df)
        elif current_tab_index == 2:  # 回撤抄底
            self.update_drawdown_chart(df)
        
        # 更新表格（无论当前选中哪个选项卡，都更新表格数据）
        self.update_table(df)
        
        # 启用导出按钮
        self.export_button.setEnabled(True)
        
        # 更新购买建议
        self.update_purchase_advice(df)
        
        # 更新状态栏
        self.status_bar.showMessage(f"成功获取 {fund_type} {fund_code} 的数据")
    
    def handle_chart_tab_change(self, index):
        """处理图表选项卡切换"""
        if not hasattr(self, 'current_data') or self.current_data.empty:
            return
        
        # 根据当前选项卡索引更新对应图表
        if index == 0:  # 净值走势（合并了波段信号）
            self.update_net_value_chart(self.current_data)
        elif index == 1:  # 神奇反转
            self.update_magic_reversal_chart(self.current_data)
        elif index == 2:  # 回撤抄底
            self.update_drawdown_chart(self.current_data)
        elif index == 3:  # 数据表格
            # 表格在数据获取时已经更新，这里不需要额外操作
            pass
    
    def handle_error(self, error_message):
        """处理错误"""
        QMessageBox.warning(self, "错误", error_message)
        self.status_bar.showMessage("获取数据失败")
    
    def reset_ui(self):
        """重置UI状态"""
        self.query_button.setEnabled(True)
    
    def apply_valuation(self):
        """应用基金估值，重新计算加仓建议"""
        # 确保有当前数据
        if not hasattr(self, 'current_data') or self.current_data.empty:
            QMessageBox.warning(self, "数据错误", "请先查询基金数据")
            return
        
        # 获取输入的涨跌幅
        change_text = self.change_input.text().strip()
        if not change_text:
            QMessageBox.warning(self, "输入错误", "请输入涨跌幅")
            return
        
        try:
            # 解析涨跌幅，移除百分号并转换为浮点数
            if change_text.endswith('%'):
                change_pct = float(change_text[:-1])
            else:
                change_pct = float(change_text)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "涨跌幅格式错误，请输入有效的数字")
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
        # 创建新的行数据
        last_date = pd.to_datetime(valuation_df['日期'].iloc[-1])
        next_date = last_date + pd.DateOffset(days=1)
        
        # 创建新行
        new_row = {
            '日期': next_date.strftime('%Y-%m-%d'),
            '净值': new_value
        }
        
        # 添加新行到数据框
        new_row_df = pd.DataFrame([new_row])
        valuation_df = pd.concat([valuation_df, new_row_df], ignore_index=True)
        
        # 更新当前数据为估值数据
        self.current_data = valuation_df
        
        # 重新生成购买建议
        self.update_purchase_advice(valuation_df)
        
        # 更新图表
        current_tab_index = self.chart_tab_widget.currentIndex()
        if current_tab_index == 0:  # 净值走势
            self.update_net_value_chart(valuation_df)
        elif current_tab_index == 1:  # 神奇反转
            self.update_magic_reversal_chart(valuation_df)
        elif current_tab_index == 2:  # 回撤抄底
            self.update_drawdown_chart(valuation_df)
        
        # 显示成功消息
        QMessageBox.information(self, "成功", f"估值应用成功！\n输入涨跌幅: {change_pct:.2f}%\n计算后净值: {new_value:.4f}")
    
    def reset_valuation(self):
        """重置估值，恢复原始数据"""
        # 清空输入
        self.change_input.clear()
        
        # 恢复原始数据
        if hasattr(self, 'original_data'):
            self.current_data = self.original_data.copy()
            delattr(self, 'original_data')
            
            # 重新生成购买建议
            self.update_purchase_advice(self.current_data)
            
            # 更新图表
            current_tab_index = self.chart_tab_widget.currentIndex()
            if current_tab_index == 0:  # 净值走势
                self.update_net_value_chart(self.current_data)
            elif current_tab_index == 1:  # 神奇反转
                self.update_magic_reversal_chart(self.current_data)
            elif current_tab_index == 2:  # 回撤抄底
                self.update_drawdown_chart(self.current_data)
            
            QMessageBox.information(self, "成功", "估值已重置，恢复原始数据")
        else:
            QMessageBox.information(self, "提示", "当前没有应用估值")
    
    def export_valuation(self):
        """导出估值数据"""
        # 确保有当前数据
        if not hasattr(self, 'current_data') or self.current_data.empty:
            QMessageBox.warning(self, "数据错误", "请先查询基金数据")
            return
        
        # 生成文件名
        fund_code = self.code_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fund_{fund_code}_valuation_{timestamp}.csv"
        
        # 导出为CSV
        try:
            self.current_data.to_csv(filename, index=False, encoding='utf-8-sig')
            QMessageBox.information(self, "成功", f"估值数据已导出到 {filename}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")
    
    def clear_chart(self):
        """清空所有图表"""
        # 清空净值走势图表
        self.net_value_ax.clear()
        self.net_value_ax.set_title("净值走势与波段信号")
        self.net_value_ax.set_xlabel("日期")
        self.net_value_ax.set_ylabel("净值")
        self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
        self.net_value_canvas.draw()
        
        # 清空神奇反转图表
        self.magic_reversal_ax.clear()
        self.magic_reversal_ax.set_title("神奇反转")
        self.magic_reversal_ax.set_xlabel("连续涨跌天数")
        self.magic_reversal_ax.set_ylabel("反转概率")
        self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
        self.magic_reversal_canvas.draw()
        
        # 清空回撤抄底图表
        self.drawdown_ax.clear()
        self.drawdown_ax.set_title("回撤抄底")
        self.drawdown_ax.set_xlabel("日期")
        self.drawdown_ax.set_ylabel("回撤率")
        self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
        self.drawdown_canvas.draw()
    
    def clear_table(self):
        """清空表格"""
        self.table.setRowCount(0)
    
    def update_net_value_chart(self, df):
        """更新净值走势图表（合并了波段信号）"""
        # 确保日期列存在
        if '日期' not in df.columns:
            return
        
        # 确保净值列存在
        if '净值' not in df.columns:
            return
        
        try:
            # 转换日期格式
            dates = pd.to_datetime(df['日期'])
            values = df['净值'].astype(float)
            
            # 优化：对于大数据集，限制绘制的数据点数量
            max_points = 1000
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                values = values[::step]
            
            # 绘制图表
            self.net_value_ax.clear()
            # 绘制净值曲线
            self.net_value_ax.plot(dates, values, 'b-', linewidth=2, label='净值')
            
            # 添加波段信号分析（升级版）
            if len(values) > 0:
                # 计算技术分析指标
                # 1. 移动平均线
                ma5 = values.rolling(window=5).mean()  # 5日均线
                ma20 = values.rolling(window=20).mean()  # 20日均线
                ma60 = values.rolling(window=60).mean()  # 60日均线
                
                # 2. 相对强弱指数（RSI）
                def calculate_rsi(data, window=14):
                    delta = data.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    return rsi
                
                rsi = calculate_rsi(values)
                
                # 3. 布林带
                def calculate_bollinger_bands(data, window=20, num_std=2):
                    ma = data.rolling(window=window).mean()
                    std = data.rolling(window=window).std()
                    upper_band = ma + (std * num_std)
                    lower_band = ma - (std * num_std)
                    return ma, upper_band, lower_band
                
                bb_ma, upper_band, lower_band = calculate_bollinger_bands(values)
                
                # 4. MACD
                def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
                    exp1 = data.ewm(span=fast_period, adjust=False).mean()
                    exp2 = data.ewm(span=slow_period, adjust=False).mean()
                    macd = exp1 - exp2
                    signal = macd.ewm(span=signal_period, adjust=False).mean()
                    histogram = macd - signal
                    return macd, signal, histogram
                
                macd, macd_signal, macd_hist = calculate_macd(values)
                
                # 绘制技术分析指标
                # 绘制移动平均线
                self.net_value_ax.plot(dates, ma5, 'g-', linewidth=1.5, label='5日均线', alpha=0.7)
                self.net_value_ax.plot(dates, ma20, 'r-', linewidth=1.5, label='20日均线', alpha=0.7)
                self.net_value_ax.plot(dates, ma60, 'y-', linewidth=1.5, label='60日均线', alpha=0.7)
                
                # 绘制布林带
                self.net_value_ax.plot(dates, upper_band, 'k--', linewidth=1, label='布林带上轨', alpha=0.7)
                self.net_value_ax.plot(dates, lower_band, 'k--', linewidth=1, label='布林带下轨', alpha=0.7)
                self.net_value_ax.fill_between(dates, upper_band, lower_band, color='gray', alpha=0.1)
                
                # 确定高位区和低位区
                # 基于布林带和RSI的综合判断
                current_value = values.iloc[-1]
                current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
                current_upper_band = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else current_value
                current_lower_band = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else current_value
                
                # 信号状态判定
                if current_value >= current_upper_band or current_rsi >= 70:
                    signal_status = "高位区 - 谨慎"
                    signal_color = 'red'
                elif current_value <= current_lower_band or current_rsi <= 30:
                    signal_status = "低位区 - 关注"
                    signal_color = 'green'
                else:
                    # 基于MACD和均线判断趋势
                    if not pd.isna(macd.iloc[-1]) and not pd.isna(macd_signal.iloc[-1]):
                        if macd.iloc[-1] > macd_signal.iloc[-1] and ma5.iloc[-1] > ma20.iloc[-1]:
                            signal_status = "上升趋势 - 持有"
                            signal_color = 'blue'
                        elif macd.iloc[-1] < macd_signal.iloc[-1] and ma5.iloc[-1] < ma20.iloc[-1]:
                            signal_status = "下降趋势 - 观望"
                            signal_color = 'purple'
                        else:
                            signal_status = "震荡区 - 观望"
                            signal_color = 'orange'
                    else:
                        signal_status = "震荡区 - 观望"
                        signal_color = 'orange'
                
                # 添加信号状态文本
                self.net_value_ax.text(0.05, 0.95, f"当前信号: {signal_status}", 
                                      transform=self.net_value_ax.transAxes, 
                                      fontsize=10, 
                                      bbox=dict(facecolor=signal_color, alpha=0.2))
                
                # 添加RSI指标信息
                if not pd.isna(current_rsi):
                    self.net_value_ax.text(0.05, 0.85, f"RSI: {current_rsi:.1f}", 
                                          transform=self.net_value_ax.transAxes, 
                                          fontsize=10, 
                                          bbox=dict(facecolor='yellow', alpha=0.2))
                
                # 在净值曲线上标注抄底和高位信号
                # 计算历史信号点
                signal_points = []
                for i in range(len(values)):
                    if i < 14:  # 确保有足够的数据计算指标
                        continue
                    
                    # 获取当前点的指标值
                    value = values.iloc[i]
                    rsi_val = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
                    upper_band_val = upper_band.iloc[i] if not pd.isna(upper_band.iloc[i]) else value
                    lower_band_val = lower_band.iloc[i] if not pd.isna(lower_band.iloc[i]) else value
                    
                    # 判断信号
                    if value >= upper_band_val or rsi_val >= 70:
                        # 高位信号
                        signal_points.append((dates.iloc[i], value, 'high'))
                    elif value <= lower_band_val or rsi_val <= 30:
                        # 低位信号（抄底）
                        signal_points.append((dates.iloc[i], value, 'low'))
                
                # 绘制信号点
                # 先绘制所有信号点，不添加标签
                for date, value, signal_type in signal_points:
                    if signal_type == 'high':
                        # 高位信号：红色倒三角
                        self.net_value_ax.scatter(date, value, marker='v', color='red', s=100, alpha=0.8)
                    elif signal_type == 'low':
                        # 低位信号：绿色倒三角
                        self.net_value_ax.scatter(date, value, marker='v', color='green', s=100, alpha=0.8)
                
                # 手动创建所有图例条目，确保包含所有必要的元素
                from matplotlib.lines import Line2D
                legend_elements = []
                
                # 添加净值曲线图例
                legend_elements.append(Line2D([], [], color='blue', linewidth=2, label='净值'))
                
                # 添加均线图例
                legend_elements.append(Line2D([], [], color='green', linewidth=1.5, label='5日均线'))
                legend_elements.append(Line2D([], [], color='red', linewidth=1.5, label='20日均线'))
                legend_elements.append(Line2D([], [], color='yellow', linewidth=1.5, label='60日均线'))
                
                # 添加布林带图例
                legend_elements.append(Line2D([], [], color='black', linestyle='--', linewidth=1, label='布林带上轨'))
                
                # 添加高位区和低位区图例
                # legend_elements.append(Line2D([], [], marker='v', color='red', linestyle='None', markersize=8, label='高位区'))
                # legend_elements.append(Line2D([], [], marker='v', color='green', linestyle='None', markersize=8, label='低位区'))
                
                # 创建图例
                self.net_value_ax.legend(handles=legend_elements)
            
            # 设置图表属性
            self.net_value_ax.set_title("净值走势与波段信号")
            self.net_value_ax.set_xlabel("日期")
            self.net_value_ax.set_ylabel("净值")
            self.net_value_ax.grid(True, linestyle='--', alpha=0.7)
            self.net_value_ax.legend()
            
            # 设置日期格式
            self.net_value_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.net_value_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # 自动调整日期标签角度
            self.net_value_figure.autofmt_xdate()
            
            # 绘制
            self.net_value_canvas.draw()
        except Exception as e:
            print(f"更新净值走势图表失败: {e}")
            # 显示错误信息
            self.net_value_ax.clear()
            self.net_value_ax.set_title("净值走势与波段信号")
            self.net_value_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                                 transform=self.net_value_ax.transAxes, 
                                 ha='center', va='center', 
                                 bbox=dict(facecolor='red', alpha=0.2))
            self.net_value_canvas.draw()
    
    def update_band_signal_chart(self, df):
        """更新波段信号图表"""
        # 确保日期列存在
        if '日期' not in df.columns:
            return
        
        # 确保净值列存在
        if '净值' not in df.columns:
            return
        
        try:
            # 转换日期格式
            dates = pd.to_datetime(df['日期'])
            values = df['净值'].astype(float)
            
            # 优化：对于大数据集，限制绘制的数据点数量
            max_points = 1000
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                values = values[::step]
            
            # 计算简单的波段信号（基于移动平均线）
            import numpy as np
            # 计算5日均线
            ma5 = np.convolve(values, np.ones(5)/5, mode='valid')
            # 计算10日均线
            ma10 = np.convolve(values, np.ones(10)/10, mode='valid')
            # 计算信号强度（5日均线 - 10日均线）
            signal_strength = []
            if len(ma5) > 0 and len(ma10) > 0:
                min_len = min(len(ma5), len(ma10))
                signal_strength = ma5[:min_len] - ma10[:min_len]
                # 对齐日期
                signal_dates = dates[-min_len:]
            
            # 绘制图表
            self.band_signal_ax.clear()
            # 绘制净值曲线
            self.band_signal_ax.plot(dates, values, 'b-', linewidth=2, label='净值')
            
            # 添加高低位区域
            if len(values) > 0:
                max_value = max(values)
                min_value = min(values)
                range_value = max_value - min_value
                high_level = max_value - range_value * 0.2
                low_level = min_value + range_value * 0.2
                
                # 绘制高位区和低位区
                self.band_signal_ax.axhline(y=high_level, color='red', linestyle='--', alpha=0.7, label='高位区')
                self.band_signal_ax.axhline(y=low_level, color='green', linestyle='--', alpha=0.7, label='低位区')
                self.band_signal_ax.fill_between(dates, high_level, max_value, color='red', alpha=0.2)
                self.band_signal_ax.fill_between(dates, min_value, low_level, color='green', alpha=0.2)
                
                # 显示当前信号状态
                current_value = values.iloc[-1]
                if current_value >= high_level:
                    signal_status = "高位区 - 谨慎"
                    signal_color = 'red'
                elif current_value <= low_level:
                    signal_status = "低位区 - 关注"
                    signal_color = 'green'
                else:
                    signal_status = "震荡区 - 观望"
                    signal_color = 'blue'
                
                # 添加信号状态文本
                self.band_signal_ax.text(0.05, 0.95, f"当前信号: {signal_status}", 
                                      transform=self.band_signal_ax.transAxes, 
                                      fontsize=10, 
                                      bbox=dict(facecolor=signal_color, alpha=0.2))
            
            # 设置图表属性
            self.band_signal_ax.set_title("波段信号")
            self.band_signal_ax.set_xlabel("日期")
            self.band_signal_ax.set_ylabel("净值")
            self.band_signal_ax.grid(True, linestyle='--', alpha=0.7)
            self.band_signal_ax.legend()
            
            # 设置日期格式
            self.band_signal_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.band_signal_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # 自动调整日期标签角度
            self.band_signal_figure.autofmt_xdate()
            
            # 绘制
            self.band_signal_canvas.draw()
        except Exception as e:
            print(f"更新波段信号图表失败: {e}")
            # 显示错误信息
            self.band_signal_ax.clear()
            self.band_signal_ax.set_title("波段信号")
            self.band_signal_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                                  transform=self.band_signal_ax.transAxes, 
                                  ha='center', va='center', 
                                  bbox=dict(facecolor='red', alpha=0.2))
            self.band_signal_canvas.draw()
    
    def update_magic_reversal_chart(self, df):
        """更新神奇反转图表"""
        # 确保净值列存在
        if '净值' not in df.columns:
            return
        
        try:
            # 计算连续涨跌天数和幅度
            values = df['净值'].astype(float)
            changes = np.diff(values)
            direction = np.sign(changes)
            change_percent = changes / values[:-1] * 100  # 涨跌幅百分比
            
            # 计算连续涨跌天数和累计幅度
            consecutive_days = []
            current_streak = 0
            current_direction = 0
            current_total_change = 0
            
            for d, change_pct in zip(direction, change_percent):
                if d == current_direction and d != 0:
                    current_streak += 1
                    current_total_change += change_pct
                else:
                    if current_direction != 0:
                        consecutive_days.append((current_streak, current_direction, current_total_change))
                    current_streak = 1 if d != 0 else 0
                    current_direction = d
                    current_total_change = change_pct if d != 0 else 0
            
            if current_direction != 0:
                consecutive_days.append((current_streak, current_direction, current_total_change))
            
            # 计算技术指标
            # 1. 波动率
            volatility = values.pct_change().rolling(window=20).std() * np.sqrt(252) * 100  # 年化波动率
            current_volatility = volatility.iloc[-1] if not pd.isna(volatility.iloc[-1]) else 0
            
            # 2. RSI
            def calculate_rsi(data, window=14):
                delta = data.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            
            rsi = calculate_rsi(values)
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            
            # 分析历史反转情况
            def analyze_reversals(consecutive_days):
                reversals = []
                for i in range(1, len(consecutive_days)):
                    prev_streak, prev_dir, prev_change = consecutive_days[i-1]
                    curr_streak, curr_dir, curr_change = consecutive_days[i]
                    # 如果方向相反，视为一次反转
                    if prev_dir != curr_dir:
                        reversals.append({
                            'prev_streak': prev_streak,
                            'prev_dir': prev_dir,
                            'prev_change': prev_change,
                            'curr_streak': curr_streak,
                            'curr_dir': curr_dir,
                            'curr_change': curr_change
                        })
                return reversals
            
            reversals = analyze_reversals(consecutive_days)
            
            # 计算反转概率（升级版）
            def calculate_reversal_probability(streak, direction, total_change, volatility, rsi, reversals):
                # 基础概率：基于连续天数
                base_prob = min(0.9, streak * 0.15)
                
                # 考虑涨跌幅度
                magnitude_factor = 1.0
                if abs(total_change) > 10:
                    magnitude_factor = 1.3  # 大幅涨跌增加反转概率
                elif abs(total_change) < 2:
                    magnitude_factor = 0.7  # 小幅涨跌减少反转概率
                
                # 考虑波动率
                volatility_factor = 1.0
                if volatility > 30:
                    volatility_factor = 1.2  # 高波动增加反转概率
                elif volatility < 15:
                    volatility_factor = 0.8  # 低波动减少反转概率
                
                # 考虑RSI
                rsi_factor = 1.0
                if direction > 0 and rsi > 70:
                    rsi_factor = 1.4  # 超买增加反转概率
                elif direction < 0 and rsi < 30:
                    rsi_factor = 1.4  # 超卖增加反转概率
                
                # 考虑历史反转情况
                history_factor = 1.0
                if reversals:
                    # 计算历史平均反转概率
                    similar_reversals = [r for r in reversals if abs(r['prev_streak'] - streak) <= 2]
                    if similar_reversals:
                        avg_prev_streak = np.mean([r['prev_streak'] for r in similar_reversals])
                        if avg_prev_streak > streak:
                            history_factor = 1.2  # 历史上类似情况反转概率高
                        else:
                            history_factor = 0.9  # 历史上类似情况反转概率低
                
                # 综合概率
                prob = base_prob * magnitude_factor * volatility_factor * rsi_factor * history_factor
                prob = min(0.95, max(0.05, prob))  # 限制在0.05-0.95之间
                
                return prob
            
            # 计算不同连续天数的反转概率
            max_streak = max([abs(day) for day, _, _ in consecutive_days]) if consecutive_days else 1
            reversal_probabilities = []
            streak_range = range(1, max_streak + 1)
            
            for streak in streak_range:
                # 假设当前为上涨趋势，计算反转概率
                prob = calculate_reversal_probability(streak, 1, streak * 0.5, current_volatility, 70, reversals)
                reversal_probabilities.append(prob)
            
            # 绘制图表
            self.magic_reversal_ax.clear()
            
            # 绘制连续涨跌天数和反转概率
            if reversal_probabilities:
                # 使用不同颜色表示反转概率大小
                colors = []
                for prob in reversal_probabilities:
                    if prob > 0.7:
                        colors.append('red')  # 高反转概率
                    elif prob > 0.4:
                        colors.append('orange')  # 中等反转概率
                    else:
                        colors.append('green')  # 低反转概率
                
                # 绘制反转概率条形图
                bars = self.magic_reversal_ax.bar(streak_range, reversal_probabilities, color=colors, alpha=0.7)
                
                # 添加概率值标签
                for bar, prob in zip(bars, reversal_probabilities):
                    height = bar.get_height()
                    self.magic_reversal_ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                                             f'{prob:.2f}',
                                             ha='center', va='bottom', fontsize=8)
            
            # 显示当前连续涨跌状态
            if consecutive_days:
                current_streak, current_direction, current_total_change = consecutive_days[-1]
                if current_direction > 0:
                    streak_status = f"当前连涨: {current_streak}天 (累计+{current_total_change:.2f}%)"
                    streak_color = 'red'
                else:
                    streak_status = f"当前连跌: {current_streak}天 (累计{current_total_change:.2f}%)"
                    streak_color = 'green'
                
                # 添加连续涨跌状态文本
                self.magic_reversal_ax.text(0.05, 0.95, streak_status, 
                                         transform=self.magic_reversal_ax.transAxes, 
                                         fontsize=10, 
                                         bbox=dict(facecolor=streak_color, alpha=0.2))
                
                # 计算并显示当前反转概率
                current_prob = calculate_reversal_probability(current_streak, current_direction, current_total_change, current_volatility, current_rsi, reversals)
                self.magic_reversal_ax.text(0.05, 0.85, f"反转概率: {current_prob:.2f}", 
                                         transform=self.magic_reversal_ax.transAxes, 
                                         fontsize=10, 
                                         bbox=dict(facecolor='blue', alpha=0.2))
                
                # 添加市场环境信息
                market_env = ""
                if current_volatility > 30:
                    market_env += "高波动 "
                elif current_volatility < 15:
                    market_env += "低波动 "
                
                if current_rsi > 70:
                    market_env += "超买"
                elif current_rsi < 30:
                    market_env += "超卖"
                else:
                    market_env += "正常"
                
                self.magic_reversal_ax.text(0.05, 0.75, f"市场环境: {market_env}", 
                                         transform=self.magic_reversal_ax.transAxes, 
                                         fontsize=10, 
                                         bbox=dict(facecolor='yellow', alpha=0.2))
            
            # 设置图表属性
            self.magic_reversal_ax.set_title("神奇反转")
            self.magic_reversal_ax.set_xlabel("连续涨跌天数")
            self.magic_reversal_ax.set_ylabel("反转概率")
            self.magic_reversal_ax.set_ylim(0, 1)
            self.magic_reversal_ax.grid(True, linestyle='--', alpha=0.7)
            
            # 添加图例
            self.magic_reversal_ax.legend(['反转概率'], loc='upper left')
            
            # 绘制
            self.magic_reversal_canvas.draw()
        except Exception as e:
            print(f"更新神奇反转图表失败: {e}")
            # 显示错误信息
            self.magic_reversal_ax.clear()
            self.magic_reversal_ax.set_title("神奇反转")
            self.magic_reversal_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                                     transform=self.magic_reversal_ax.transAxes, 
                                     ha='center', va='center', 
                                     bbox=dict(facecolor='red', alpha=0.2))
            self.magic_reversal_canvas.draw()
    
    def update_purchase_advice(self, df):
        """更新购买建议文本框"""
        # 确保净值列存在
        if '净值' not in df.columns:
            self.advice_text.setText("数据不足，无法生成购买建议")
            return
        
        try:
            # 计算技术分析指标
            values = df['净值'].astype(float)
            
            # 1. 移动平均线
            ma5 = values.rolling(window=5).mean()  # 5日均线
            ma20 = values.rolling(window=20).mean()  # 20日均线
            ma60 = values.rolling(window=60).mean()  # 60日均线
            
            # 2. 相对强弱指数（RSI）
            def calculate_rsi(data, window=14):
                delta = data.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            
            rsi = calculate_rsi(values)
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            
            # 3. 布林带
            def calculate_bollinger_bands(data, window=20, num_std=2):
                ma = data.rolling(window=window).mean()
                std = data.rolling(window=window).std()
                upper_band = ma + (std * num_std)
                lower_band = ma - (std * num_std)
                return ma, upper_band, lower_band
            
            bb_ma, upper_band, lower_band = calculate_bollinger_bands(values)
            current_upper_band = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else values.iloc[-1]
            current_lower_band = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else values.iloc[-1]
            
            # 4. MACD
            def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
                exp1 = data.ewm(span=fast_period, adjust=False).mean()
                exp2 = data.ewm(span=slow_period, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=signal_period, adjust=False).mean()
                histogram = macd - signal
                return macd, signal, histogram
            
            macd, macd_signal, macd_hist = calculate_macd(values)
            
            # 5. 回撤率
            import numpy as np
            running_max = np.maximum.accumulate(values)
            drawdown = (values - running_max) / running_max * 100
            current_drawdown = drawdown.iloc[-1] if not pd.isna(drawdown.iloc[-1]) else 0
            
            # 6. 连续涨跌分析
            changes = np.diff(values)
            direction = np.sign(changes)
            change_percent = changes / values[:-1] * 100  # 涨跌幅百分比
            
            # 计算连续涨跌天数和累计幅度
            consecutive_days = []
            current_streak = 0
            current_direction = 0
            current_total_change = 0
            
            for d, change_pct in zip(direction, change_percent):
                if d == current_direction and d != 0:
                    current_streak += 1
                    current_total_change += change_pct
                else:
                    if current_direction != 0:
                        consecutive_days.append((current_streak, current_direction, current_total_change))
                    current_streak = 1 if d != 0 else 0
                    current_direction = d
                    current_total_change = change_pct if d != 0 else 0
            
            if current_direction != 0:
                consecutive_days.append((current_streak, current_direction, current_total_change))
            
            # 获取当前连续涨跌状态
            current_streak = 0
            current_direction = 0
            current_total_change = 0
            if consecutive_days:
                current_streak, current_direction, current_total_change = consecutive_days[-1]
            
            # 分析市场状态和生成建议
            market_status = ""
            advice = ""
            advice_level = "neutral"
            
            # 基于多指标综合分析
            buy_score = 0
            
            # RSI分析
            if current_rsi < 30:
                market_status += "超卖状态，"
                buy_score += 3
            elif current_rsi > 70:
                market_status += "超买状态，"
                buy_score -= 3
            else:
                market_status += "正常状态，"
            
            # 布林带分析
            current_value = values.iloc[-1]
            if current_value <= current_lower_band:
                market_status += "触及布林带下轨，"
                buy_score += 3
            elif current_value >= current_upper_band:
                market_status += "触及布林带上轨，"
                buy_score -= 3
            
            # 回撤分析
            if current_drawdown < -20:
                market_status += "深度回撤，"
                buy_score += 4
            elif current_drawdown < -10:
                market_status += "中度回撤，"
                buy_score += 2
            elif current_drawdown < -5:
                market_status += "轻度回撤，"
                buy_score += 1
            
            # 均线分析
            if not pd.isna(ma5.iloc[-1]) and not pd.isna(ma20.iloc[-1]):
                if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
                    market_status += "多头排列，"
                    buy_score += 2
                elif ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]:
                    market_status += "空头排列，"
                    buy_score -= 2
            
            # MACD分析
            if not pd.isna(macd.iloc[-1]) and not pd.isna(macd_signal.iloc[-1]):
                if macd.iloc[-1] > macd_signal.iloc[-1]:
                    market_status += "MACD金叉，"
                    buy_score += 2
                else:
                    market_status += "MACD死叉，"
                    buy_score -= 2
            
            # 连续涨跌分析
            if current_streak >= 3:
                if current_direction > 0:
                    market_status += f"连续上涨{current_streak}天，"
                    buy_score -= 1  # 连续上涨过多可能回调
                else:
                    market_status += f"连续下跌{current_streak}天，"
                    buy_score += 1  # 连续下跌过多可能反弹
            
            # 确定建议级别
            if buy_score >= 6:
                advice_level = "strong_buy"
                advice = "强烈推荐购买：多指标显示当前为极佳买点，建议积极布局。"
            elif buy_score >= 3:
                advice_level = "buy"
                advice = "推荐购买：当前市场处于较好买入区间，建议适量配置。"
            elif buy_score >= -2:
                advice_level = "neutral"
                advice = "观望：市场处于震荡区间，建议暂时观望或小额试探性建仓。"
            elif buy_score >= -4:
                advice_level = "sell"
                advice = "不推荐购买：市场处于弱势，建议等待更好买点。"
            else:
                advice_level = "strong_sell"
                advice = "强烈不推荐购买：多指标显示当前风险较高，建议避免入场。"
            
            # 建议级别文本和颜色
            level_text = {
                'strong_buy': '强烈推荐购买',
                'buy': '推荐购买',
                'neutral': '观望',
                'sell': '不推荐购买',
                'strong_sell': '强烈不推荐购买'
            }.get(advice_level, '观望')
            
            level_color = {
                'strong_buy': 'green',
                'buy': 'lightgreen',
                'neutral': 'blue',
                'sell': 'orange',
                'strong_sell': 'red'
            }.get(advice_level, 'blue')
            
            # 生成完整建议文本
            full_advice = f"{market_status[:-1]}。\n\n"
            full_advice += f"{advice}\n\n"
            full_advice += f"当前指标：\n"
            full_advice += f"RSI: {current_rsi:.1f}\n"
            full_advice += f"回撤率: {current_drawdown:.1f}%\n"
            if current_streak > 0:
                trend = "上涨" if current_direction > 0 else "下跌"
                full_advice += f"连续{trend}: {current_streak}天\n"
                if current_total_change != 0:
                    full_advice += f"累计幅度: {current_total_change:.2f}%\n"
            full_advice += f"建议级别: <span style='color:{level_color}; font-weight:bold'>{level_text}</span>"
            
            # 更新建议文本框
            self.advice_text.setText(full_advice)
            self.advice_text.setTextFormat(Qt.RichText)
            
        except Exception as e:
            print(f"更新购买建议失败: {e}")
            self.advice_text.setText("生成购买建议时出错，请稍后重试")
    
    def update_drawdown_chart(self, df):
        """更新回撤抄底图表"""
        # 确保日期列存在
        if '日期' not in df.columns:
            return
        
        # 确保净值列存在
        if '净值' not in df.columns:
            return
        
        try:
            # 转换日期格式
            dates = pd.to_datetime(df['日期'])
            values = df['净值'].astype(float)
            
            # 优化：对于大数据集，限制绘制的数据点数量
            max_points = 1000
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                values = values[::step]
            
            # 计算回撤率
            import numpy as np
            running_max = np.maximum.accumulate(values)
            drawdown = (values - running_max) / running_max * 100
            
            # 计算其他技术分析指标
            # 1. 波动率
            volatility = values.pct_change().rolling(window=20).std() * np.sqrt(252) * 100  # 年化波动率
            
            # 2. MACD
            def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
                exp1 = data.ewm(span=fast_period, adjust=False).mean()
                exp2 = data.ewm(span=slow_period, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=signal_period, adjust=False).mean()
                histogram = macd - signal
                return macd, signal, histogram
            
            macd, macd_signal, macd_hist = calculate_macd(values)
            
            # 3. 回撤持续时间
            def calculate_drawdown_duration(drawdown):
                duration = []
                current_duration = 0
                for d in drawdown:
                    if d < 0:
                        current_duration += 1
                    else:
                        current_duration = 0
                    duration.append(current_duration)
                return pd.Series(duration, index=drawdown.index)
            
            drawdown_duration = calculate_drawdown_duration(drawdown)
            
            # 4. 回撤恢复情况分析
            def analyze_drawdown_recovery(drawdown):
                recoveries = []
                in_drawdown = False
                drawdown_start = 0
                max_drawdown_in_period = 0
                
                for i, d in enumerate(drawdown):
                    if d < 0 and not in_drawdown:
                        in_drawdown = True
                        drawdown_start = i
                        max_drawdown_in_period = d
                    elif d < 0 and in_drawdown:
                        if d < max_drawdown_in_period:
                            max_drawdown_in_period = d
                    elif d >= 0 and in_drawdown:
                        in_drawdown = False
                        recovery_period = i - drawdown_start
                        if recovery_period > 0:
                            recoveries.append({
                                'start': drawdown_start,
                                'end': i,
                                'duration': recovery_period,
                                'max_drawdown': max_drawdown_in_period
                            })
                return recoveries
            
            drawdown_recoveries = analyze_drawdown_recovery(drawdown)
            
            # 绘制图表
            self.drawdown_ax.clear()
            # 绘制回撤率
            self.drawdown_ax.plot(dates, drawdown, 'g-', linewidth=2, label='回撤率')
            # 添加零轴
            self.drawdown_ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            # 添加抄底区域
            self.drawdown_ax.fill_between(dates, drawdown, -20, where=(drawdown < -15), color='red', alpha=0.2, label='抄底区')
            self.drawdown_ax.fill_between(dates, drawdown, -10, where=(drawdown < -10) & (drawdown >= -15), color='orange', alpha=0.2, label='关注区')
            
            # 计算关键回撤指标
            current_drawdown = drawdown.iloc[-1]
            max_drawdown = min(drawdown)
            drawdown_diff = max_drawdown - current_drawdown
            current_duration = drawdown_duration.iloc[-1]
            current_volatility = volatility.iloc[-1] if not pd.isna(volatility.iloc[-1]) else 0
            
            # 计算抄底胜率（升级版）
            def calculate_bottom_win_rate(current_drawdown, current_duration, current_volatility, drawdown_recoveries):
                # 基础胜率
                base_win_rate = 0
                if current_drawdown < -20:
                    base_win_rate = 0.8
                elif current_drawdown < -15:
                    base_win_rate = 0.65
                elif current_drawdown < -10:
                    base_win_rate = 0.45
                elif current_drawdown < -5:
                    base_win_rate = 0.3
                else:
                    base_win_rate = 0.1
                
                # 考虑回撤持续时间
                duration_factor = min(1.5, 1 + current_duration / 30)  # 持续时间越长，胜率越高
                
                # 考虑波动率
                volatility_factor = 1.0
                if current_volatility > 30:
                    volatility_factor = 0.8  # 高波动降低胜率
                elif current_volatility < 15:
                    volatility_factor = 1.2  # 低波动提高胜率
                
                # 考虑历史回撤恢复情况
                recovery_factor = 1.0
                if drawdown_recoveries:
                    avg_recovery_duration = np.mean([r['duration'] for r in drawdown_recoveries])
                    avg_max_drawdown = np.mean([abs(r['max_drawdown']) for r in drawdown_recoveries])
                    if avg_recovery_duration < 20:
                        recovery_factor = 1.3  # 历史恢复快，提高胜率
                    elif avg_recovery_duration > 60:
                        recovery_factor = 0.8  # 历史恢复慢，降低胜率
                
                # 综合胜率
                win_rate = base_win_rate * duration_factor * volatility_factor * recovery_factor
                win_rate = min(0.95, max(0.05, win_rate))  # 限制在0.05-0.95之间
                
                return win_rate
            
            win_rate = calculate_bottom_win_rate(current_drawdown, current_duration, current_volatility, drawdown_recoveries)
            
            # 胜率等级判定
            if win_rate >= 0.7:
                bottom_win_rate = f"高胜率 ({win_rate:.2f})"
                win_rate_color = 'green'
            elif win_rate >= 0.4:
                bottom_win_rate = f"中等胜率 ({win_rate:.2f})"
                win_rate_color = 'orange'
            else:
                bottom_win_rate = f"低胜率 ({win_rate:.2f})"
                win_rate_color = 'red'
            
            # 计算当前市场状态
            current_macd = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0
            current_macd_signal = macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else 0
            
            market_status = "震荡"
            if current_macd > current_macd_signal and current_drawdown > -10:
                market_status = "上升"
            elif current_macd < current_macd_signal and current_drawdown < -15:
                market_status = "下跌"
            
            # 添加回撤指标文本
            self.drawdown_ax.text(0.05, 0.95, f"当前回撤: {current_drawdown:.2f}%", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor='blue', alpha=0.2))
            self.drawdown_ax.text(0.05, 0.88, f"最大回撤: {max_drawdown:.2f}%", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor='red', alpha=0.2))
            self.drawdown_ax.text(0.05, 0.81, f"回撤持续: {current_duration}天", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor='purple', alpha=0.2))
            self.drawdown_ax.text(0.05, 0.74, f"年化波动率: {current_volatility:.2f}%", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor='yellow', alpha=0.2))
            self.drawdown_ax.text(0.05, 0.67, f"市场状态: {market_status}", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor='cyan', alpha=0.2))
            self.drawdown_ax.text(0.05, 0.60, f"抄底胜率: {bottom_win_rate}", 
                               transform=self.drawdown_ax.transAxes, 
                               fontsize=10, 
                               bbox=dict(facecolor=win_rate_color, alpha=0.2))
            
            # 添加MACD指标（可选）
            # 这里可以添加MACD子图，但为了保持图表简洁，暂时不添加
            
            # 标记历史重要回撤点
            if drawdown_recoveries:
                for recovery in drawdown_recoveries:
                    if recovery['max_drawdown'] < -15:
                        recovery_date = dates.iloc[recovery['end']]
                        self.drawdown_ax.plot(recovery_date, 0, 'go', markersize=6, alpha=0.7, label='历史抄底点')
            
            # 设置图表属性
            self.drawdown_ax.set_title("回撤抄底")
            self.drawdown_ax.set_xlabel("日期")
            self.drawdown_ax.set_ylabel("回撤率 (%)")
            self.drawdown_ax.grid(True, linestyle='--', alpha=0.7)
            self.drawdown_ax.legend()
            
            # 设置日期格式
            self.drawdown_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.drawdown_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # 自动调整日期标签角度
            self.drawdown_figure.autofmt_xdate()
            
            # 绘制
            self.drawdown_canvas.draw()
        except Exception as e:
            print(f"更新回撤抄底图表失败: {e}")
            # 显示错误信息
            self.drawdown_ax.clear()
            self.drawdown_ax.set_title("回撤抄底")
            self.drawdown_ax.text(0.5, 0.5, f"图表加载失败: {str(e)[:50]}", 
                               transform=self.drawdown_ax.transAxes, 
                               ha='center', va='center', 
                               bbox=dict(facecolor='red', alpha=0.2))
            self.drawdown_canvas.draw()
    
    def update_table(self, df):
        """更新表格"""
        # 清空表格
        self.table.setRowCount(0)
        
        # 按日期降序排序，确保最近的数据显示在上面
        if '日期' in df.columns:
            try:
                # 尝试转换日期格式并排序
                df_sorted = df.sort_values(by='日期', ascending=False)
            except:
                # 如果排序失败，使用原始数据
                df_sorted = df
        else:
            df_sorted = df
        
        # 添加数据行
        for index, row in df_sorted.iterrows():
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # 日期
            if '日期' in row:
                date_item = QTableWidgetItem(str(row['日期']))
                self.table.setItem(row_position, 0, date_item)
            
            # 净值
            if '净值' in row:
                value_item = QTableWidgetItem(str(row['净值']))
                self.table.setItem(row_position, 1, value_item)
            
            # 日增长率
            if '日增长率' in row:
                growth_item = QTableWidgetItem(str(row['日增长率']))
                self.table.setItem(row_position, 2, growth_item)
            elif '日涨幅' in row:
                growth_item = QTableWidgetItem(str(row['日涨幅']))
                self.table.setItem(row_position, 2, growth_item)
    
    def calculate_fund_analysis(self, df, fund_code):
        """计算基金分析数据"""
        analysis = {
            'current_nav': '',
            'today_change': '',
            'one_year_change': ''
        }
        
        if not df.empty and '净值' in df.columns:
            try:
                # 获取当前净值
                values = df['净值'].astype(float)
                current_nav = values.iloc[-1]
                analysis['current_nav'] = f"{current_nav:.4f}"
                
                # 计算今日涨跌幅
                if len(values) >= 2:
                    today_change = (values.iloc[-1] - values.iloc[-2]) / values.iloc[-2] * 100
                    analysis['today_change'] = f"{today_change:+.2f}%"
                
                # 计算近一年涨跌幅
                # 找到一年前的日期
                one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
                
                # 尝试从当前数据集中找到一年前的净值
                one_year_ago_nav = None
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'])
                    one_year_ago_df = df[df['日期'] <= one_year_ago]
                    if not one_year_ago_df.empty:
                        one_year_ago_nav = one_year_ago_df['净值'].iloc[-1].astype(float)
                
                # 如果当前数据集不包含一年前的数据，单独获取基金的历史数据
                if one_year_ago_nav is None:
                    try:
                        # 获取基金的历史数据
                        # 首先尝试获取场外基金数据
                        history_df = SafeRequest.request(
                            ak.fund_open_fund_info_em,
                            symbol=fund_code,
                            indicator="单位净值走势"
                        )
                        
                        # 如果场外基金数据为空，尝试获取ETF数据
                        if history_df.empty or '净值日期' not in history_df.columns:
                            history_df = SafeRequest.request(ak.fund_etf_hist_sina, symbol=fund_code)
                        
                        # 处理数据
                        if not history_df.empty:
                            # 统一数据格式
                            if '净值日期' in history_df.columns:
                                history_df.rename(columns={'净值日期': '日期'}, inplace=True)
                            if '单位净值' in history_df.columns:
                                history_df.rename(columns={'单位净值': '净值'}, inplace=True)
                            
                            # 找到一年前或最接近一年前的净值
                            if '日期' in history_df.columns:
                                history_df['日期'] = pd.to_datetime(history_df['日期'])
                                one_year_ago_history_df = history_df[history_df['日期'] <= one_year_ago]
                                if not one_year_ago_history_df.empty:
                                    one_year_ago_nav = one_year_ago_history_df['净值'].iloc[-1].astype(float)
                    except Exception as e:
                        print(f"获取历史数据失败: {e}")
                
                # 计算近一年涨跌幅
                if one_year_ago_nav is not None:
                    one_year_change = (current_nav - one_year_ago_nav) / one_year_ago_nav * 100
                    analysis['one_year_change'] = f"{one_year_change:+.2f}%"
            except Exception as e:
                print(f"计算基金分析数据失败: {e}")
        
        return analysis
    
    def show_fund_info(self, fund_info, fund_code, fund_type, fund_analysis=None):
        """显示基金基本信息"""
        # 清空之前的信息
        for i in reversed(range(self.info_layout.count())):
            widget = self.info_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 创建信息标签
        if fund_info:
            info_text = f"基金代码: {fund_code} | 基金类型: {fund_type}"
            for key, value in fund_info.items():
                if value:
                    info_text += f" | {key}: {value}"
        else:
            info_text = f"基金代码: {fund_code} | 基金类型: {fund_type}"
        
        # 添加涨跌幅信息
        if fund_analysis:
            info_text += f" | 净值: {fund_analysis.get('current_nav', 'N/A')}"
            info_text += f" | 今日涨跌幅: {fund_analysis.get('today_change', 'N/A')}"
            info_text += f" | 近一年涨跌幅: {fund_analysis.get('one_year_change', 'N/A')}"
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #333; font-size: 9pt;")
        
        # 添加到布局
        self.info_layout.addWidget(info_label)
        self.info_layout.addStretch()
    
    def export_data(self):
        """导出数据"""
        if not hasattr(self, 'current_data') or self.current_data.empty:
            QMessageBox.warning(self, "错误", "没有可导出的数据")
            return
        
        try:
            # 生成文件名
            fund_code = self.code_input.text().strip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fund_{fund_code}_{timestamp}.csv"
            
            # 导出为CSV
            self.current_data.to_csv(filename, index=False, encoding='utf-8-sig')
            
            QMessageBox.information(self, "成功", f"数据已导出到 {filename}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")
    
    def show_purchase_advice(self):
        """显示购买建议对话框"""
        if not hasattr(self, 'current_data') or self.current_data.empty:
            QMessageBox.warning(self, "错误", "没有足够的数据生成购买建议")
            return
        
        try:
            # 生成购买建议数据
            advice_data = self.generate_purchase_advice()
            
            # 显示购买建议对话框
            dialog = PurchaseAdviceDialog(self, advice_data)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成购买建议失败: {str(e)}")
    
    def generate_purchase_advice(self):
        """生成购买建议数据"""
        # 基金基本信息
        fund_code = self.code_input.text().strip()
        fund_name = self.current_fund_info.get('基金名称', fund_code) if hasattr(self, 'current_fund_info') else fund_code
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        
        # 准备数据
        df = self.current_data
        values = df['净值'].astype(float)
        dates = pd.to_datetime(df['日期'])
        
        # 1. 波段信号分析
        band_signal = self.analyze_band_signal(values, dates)
        
        # 2. 回撤抄底分析
        drawdown = self.analyze_drawdown(values, dates)
        
        # 3. 神奇反转分析
        magic_reversal = self.analyze_magic_reversal(values)
        
        # 4. 综合建议
        summary_advice, advice_level = self.generate_summary_advice(band_signal, drawdown, magic_reversal)
        
        # 构建建议数据
        advice_data = {
            'fund_code': fund_code,
            'fund_name': fund_name,
            'analysis_date': analysis_date,
            'band_signal': band_signal,
            'drawdown': drawdown,
            'magic_reversal': magic_reversal,
            'summary_advice': summary_advice,
            'advice_level': advice_level
        }
        
        return advice_data
    
    def analyze_band_signal(self, values, dates):
        """分析波段信号"""
        # 计算技术指标
        ma5 = values.rolling(window=5).mean()
        ma20 = values.rolling(window=20).mean()
        
        # 计算RSI
        def calculate_rsi(data, window=14):
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        rsi = calculate_rsi(values)
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # 计算布林带
        def calculate_bollinger_bands(data, window=20, num_std=2):
            ma = data.rolling(window=window).mean()
            std = data.rolling(window=window).std()
            upper_band = ma + (std * num_std)
            lower_band = ma - (std * num_std)
            return ma, upper_band, lower_band
        
        bb_ma, upper_band, lower_band = calculate_bollinger_bands(values)
        current_upper_band = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else values.iloc[-1]
        current_lower_band = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else values.iloc[-1]
        
        # 信号状态判定
        current_value = values.iloc[-1]
        if current_value >= current_upper_band or current_rsi >= 70:
            status = "高位区 - 谨慎"
            advice = "不建议购买"
        elif current_value <= current_lower_band or current_rsi <= 30:
            status = "低位区 - 关注"
            advice = "建议购买"
        else:
            status = "震荡区 - 观望"
            advice = "观望"
        
        return {
            'status': status,
            'rsi': f"{current_rsi:.2f}",
            'advice': advice
        }
    
    def analyze_drawdown(self, values, dates):
        """分析回撤抄底"""
        # 计算回撤率
        import numpy as np
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max * 100
        
        # 计算关键指标
        current_drawdown = drawdown.iloc[-1]
        max_drawdown = min(drawdown)
        
        # 计算抄底胜率
        def calculate_bottom_win_rate(current_drawdown):
            if current_drawdown < -20:
                return 0.8
            elif current_drawdown < -15:
                return 0.65
            elif current_drawdown < -10:
                return 0.45
            elif current_drawdown < -5:
                return 0.3
            else:
                return 0.1
        
        win_rate = calculate_bottom_win_rate(current_drawdown)
        
        # 建议操作
        if win_rate >= 0.7:
            advice = "强烈建议购买"
        elif win_rate >= 0.4:
            advice = "建议购买"
        else:
            advice = "不建议购买"
        
        return {
            'current_drawdown': f"{current_drawdown:.2f}%",
            'max_drawdown': f"{max_drawdown:.2f}%",
            'win_rate': f"{win_rate:.2f}",
            'advice': advice
        }
    
    def analyze_magic_reversal(self, values):
        """分析神奇反转"""
        # 计算连续涨跌天数和幅度
        changes = np.diff(values)
        direction = np.sign(changes)
        
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
        
        # 计算反转概率
        if consecutive_days:
            current_streak, current_direction = consecutive_days[-1]
            if current_direction > 0:
                streak_status = f"连涨 {current_streak}天"
            else:
                streak_status = f"连跌 {current_streak}天"
            
            # 计算反转概率
            reversal_prob = min(0.9, current_streak * 0.15)
            
            # 建议操作
            if reversal_prob >= 0.7:
                advice = "建议反向操作"
            else:
                advice = "观望"
        else:
            streak_status = "无明显趋势"
            reversal_prob = 0.5
            advice = "观望"
        
        return {
            'streak': streak_status,
            'probability': f"{reversal_prob:.2f}",
            'advice': advice
        }
    
    def generate_summary_advice(self, band_signal, drawdown, magic_reversal):
        """生成综合建议"""
        # 评分系统
        score = 0
        
        # 波段信号评分
        band_advice = band_signal.get('advice', '观望')
        if band_advice == "建议购买":
            score += 2
        elif band_advice == "不建议购买":
            score -= 2
        
        # 回撤抄底评分
        drawdown_advice = drawdown.get('advice', '观望')
        if drawdown_advice == "强烈建议购买":
            score += 3
        elif drawdown_advice == "建议购买":
            score += 1
        elif drawdown_advice == "不建议购买":
            score -= 1
        
        # 神奇反转评分
        magic_advice = magic_reversal.get('advice', '观望')
        if magic_advice == "建议反向操作":
            # 根据当前趋势调整评分
            streak = magic_reversal.get('streak', '')
            if "连涨" in streak:
                score -= 2  # 连涨后反转，不建议购买
            elif "连跌" in streak:
                score += 2  # 连跌后反转，建议购买
        
        # 确定建议级别
        if score >= 5:
            advice_level = 'strong_buy'
            summary_advice = "综合多个指标分析，当前基金处于较好的买入时机，建议积极购买。"
        elif score >= 2:
            advice_level = 'buy'
            summary_advice = "综合多个指标分析，当前基金存在买入机会，建议适量购买。"
        elif score >= -2:
            advice_level = 'neutral'
            summary_advice = "综合多个指标分析，当前基金处于震荡状态，建议观望为主。"
        elif score >= -5:
            advice_level = 'sell'
            summary_advice = "综合多个指标分析，当前基金不建议购买，建议观望。"
        else:
            advice_level = 'strong_sell'
            summary_advice = "综合多个指标分析，当前基金处于不利状态，强烈不建议购买。"
        
        return summary_advice, advice_level
    
    def handle_quick_date_change(self, index):
        """处理快速日期选择变化"""
        end_date = QDate.currentDate()
        
        if index == 0:  # 近1月
            start_date = end_date.addDays(-30)
        elif index == 1:  # 近3月
            start_date = end_date.addDays(-90)
        elif index == 2:  # 近6月
            start_date = end_date.addDays(-180)
        elif index == 3:  # 近1年
            start_date = end_date.addDays(-365)
        elif index == 4:  # 今年以来
            start_date = QDate(end_date.year(), 1, 1)
        elif index == 5:  # 近3年
            start_date = end_date.addDays(-1095)
        elif index == 6:  # 近5年
            start_date = end_date.addDays(-1825)
        elif index == 7:  # 成立以来
            # 这里设置一个较早的日期作为默认值
            # 实际应用中可能需要根据基金的具体成立日期来设置
            start_date = QDate(2000, 1, 1)
        
        self.start_date_input.setDate(start_date)
        self.end_date_input.setDate(end_date)

    def set_quick_date(self, days):
        """快速设置日期范围"""
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        
        self.start_date_input.setDate(start_date)
        self.end_date_input.setDate(end_date)















class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.setWindowTitle("养基宝 - 基金查询系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(self.central_widget)
        
        # 导航栏
        nav_layout = QHBoxLayout()
        
        # 导航按钮
        self.nav_buttons = []
        
        # 基金查询按钮
        fund_query_button = QPushButton("基金查询")
        fund_query_button.clicked.connect(lambda: self.switch_tab(0))
        nav_layout.addWidget(fund_query_button)
        self.nav_buttons.append(fund_query_button)
        
        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)
        
        # 堆叠窗口
        self.stacked_widget = QStackedWidget()
        
        # 添加基金查询模块（使用原有的FundGUI）
        self.fund_gui = FundGUI()
        self.stacked_widget.addWidget(self.fund_gui)
        
        main_layout.addWidget(self.stacked_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 默认选中第一个标签
        self.switch_tab(0)
    
    def switch_tab(self, index):
        """切换标签"""
        # 更新按钮状态
        for i, button in enumerate(self.nav_buttons):
            if i == index:
                button.setStyleSheet("background-color: #e6f7ff; font-weight: bold;")
            else:
                button.setStyleSheet("")
        
        # 切换堆叠窗口
        self.stacked_widget.setCurrentIndex(index)
        
        # 更新状态栏
        tab_names = ["基金查询"]
        self.status_bar.showMessage(f"当前模块: {tab_names[index]}")
    

    
    def closeEvent(self, event):
        """关闭窗口事件"""
        event.accept()

if __name__ == "__main__":
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
