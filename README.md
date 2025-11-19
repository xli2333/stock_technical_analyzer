# 股票技术分析系统 (Stock Technical Analyzer)

## 项目简介
这是一个专业级的 A 股股票技术分析系统，结合了现代化的 React 前端界面与强大的 Python 后端分析能力。系统基于 `akshare` 获取实时数据，利用 `talib` 进行深度技术指标计算，提供多周期分析、智能评分及交易信号提示。

## 主要特性

### 核心功能
- **多周期分析**：支持日线、周线、月线级别的 K 线与指标分析。
- **全方位指标**：
  - **基础指标**：MA, EMA, RSI, MACD, KDJ, BOLL, VOL 等。
  - **高级指标**：SuperTrend (超级趋势), Ichimoku (一目均衡表), VWMA, ATR, CCI, ROC 等。
  - **体制识别**：自动识别当前市场处于“趋势”还是“震荡”状态。
- **智能决策**：
  - 基于多维度指标的综合评分系统 (-100 到 +100)。
  - 自动生成买入/卖出/观望建议。
  - 识别背离信号 (RSI/MACD Divergence)。

### 现代化体验
- **Web 界面**：基于 React + Tailwind CSS + Lightweight Charts 构建的响应式界面，支持深色模式。
- **单文件部署**：前端已预编译为静态文件，无需复杂配置，启动 Python 服务即可使用。
- **PDF 导出**：支持生成包含图表和详细数据的 PDF 分析报告。

## 安装指南

### 1. 环境准备
请确保已安装 Python 3.8 或更高版本。

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

**注意**：本项目依赖 `TA-Lib` 库。如果在 Windows 上安装 `talib` 遇到问题，请前往 [Christoph Gohlke's LFD](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib) 下载对应版本的 `.whl` 文件并手动安装。

### 3. 前端构建 (可选)
如果您只是使用，无需重新构建前端。如果您修改了 `client/` 目录下的代码，请执行：
```bash
cd client
npm install
npm run build
```
构建产物会自动更新到 `static/` 目录。

## 使用说明

### 方式一：Web 界面 (推荐)

启动 Web 服务：
```bash
python web_app.py
```

然后打开浏览器访问：**http://localhost:5000**

在搜索框输入 A 股代码（如 `600000`），即可查看实时分析图表与评分。

### 方式二：命令行工具 (CLI)

如果您偏好命令行操作，可以使用 `run_analysis.py`：

```bash
# 分析单只股票 (默认日线)
python run_analysis.py 600000

# 分析周线数据
python run_analysis.py 600000 --period weekly

# 分析并生成 PDF 报告
python web_app.py 的 /export_pdf 接口可用于导出，或参考代码自行调用 analyzer.export_pdf()
```

分析结果将保存在 `output/` 目录下。

## 网络与代理配置

本程序通过 `akshare` 访问东方财富等数据源。

- **直连模式**：默认情况下，程序使用您系统的默认网络设置。
- **代理模式**：如果您所在的网络环境需要代理（如访问特定数据源受限），请确保您的终端设置了正确的环境变量（`HTTP_PROXY`, `HTTPS_PROXY`）。
  - 程序会自动尊重系统的代理设置。
  - 如果遇到连接超时或数据获取失败，请尝试关闭 VPN 或检查代理配置。

## 常见问题

**Q: 为什么显示 "Missing backend dependency (talib)"?**
A: 说明 TA-Lib 库没有正确安装。这是计算技术指标的核心库，必须安装。

**Q: 输入股票代码后提示 "Analysis failed"?**
A: 
1. 请检查股票代码是否正确（6位数字）。
2. 检查网络连接，尝试访问东方财富网站看是否正常。
3. 如果是停牌股票，可能无法获取数据。

**Q: 前端页面显示空白或加载失败？**
A: 请确认 `static/index.html` 文件存在。如果不存在，请参考“前端构建”步骤重新生成资源。

## 目录结构
- `web_app.py`: Flask Web 服务器主程序。
- `analyzer.py`: 核心分析逻辑与评分系统。
- `data_fetcher.py`: 数据获取模块 (Akshare 封装)。
- `indicators.py` / `advanced_indicators.py`: 技术指标计算实现。
- `client/`: React 前端源代码。
- `static/`: 编译后的前端静态资源。
- `output/`: 分析报告输出目录。
