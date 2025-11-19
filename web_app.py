"""Flask web UI for Stock Technical Analyzer (ASCII-safe)
- API: /analyze returns structured analysis with OHLCV & advanced indicators
- API: /export_pdf generates PDF with chart (SuperTrend/Ichimoku overlays)
"""

import sys
# Force UTF-8 for stdout (fixes Windows console issues)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import os
import tempfile
import shutil
import numpy as np

# Optional plotting/PDF deps
try:
    import mplfinance as mpf
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAVE_REPORT = True
except Exception:
    HAVE_REPORT = False

# Configure Chinese Fonts
CHINESE_FONT = 'Helvetica'
if HAVE_REPORT:
    try:
        # Use relative path for font (supports Vercel/Docker/Windows)
        # Updated to use HarmonyOS Sans SC Regular - JUST ONE FILE to save space
        font_path = os.path.join(os.path.dirname(__file__), 'HarmonyOS Sans', 'HarmonyOS_Sans_SC', 'HarmonyOS_Sans_SC_Regular.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('HarmonyOS', font_path))
            CHINESE_FONT = 'HarmonyOS'
        else:
             print(f"Warning: Font file not found at {font_path}")
    except Exception as e:
        print(f"Warning: Could not register Chinese font: {e}")


app = Flask(__name__, static_folder='static', static_url_path='')

# Ensure directories exist (for local dev mainly)
os.makedirs('output', exist_ok=True)
os.makedirs('static', exist_ok=True)


@app.errorhandler(500)
def internal_error(error):
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'Internal Server Error', 'details': str(error)}), 500

@app.route('/')
def index():
    return send_file(os.path.join('static', 'index.html'))


@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    try:
        if request.method == 'POST':
             data = request.get_json(force=True)
             symbol = (data.get('symbol') or '').strip()
             period = (data.get('period') or 'daily').strip()
        else:
             symbol = (request.args.get('symbol') or '').strip()
             period = (request.args.get('period') or 'daily').strip()

        if not symbol:
            return jsonify({'error': 'Please enter a stock symbol'}), 400

        try:
            from analyzer import StockAnalyzer
        except Exception as e:
            return jsonify({'error': f'Missing backend dependency (maybe TA-Lib/akshare): {e}'}), 500

        analyzer = StockAnalyzer(use_proxy=True)
        # Use longer history for weekly/monthly
        days = 400
        if period == 'weekly': days = 500
        if period == 'monthly': days = 2000
        
        if not analyzer.analyze(symbol, days=days, period=period):
            return jsonify({'error': 'Analysis failed, check symbol or network'}), 400

        # OHLCV for charting
        try:
            ohlcv = []
            if analyzer.data is not None and len(analyzer.data) > 0:
                for _, row in analyzer.data.iterrows():
                    d = str(row['date'])
                    if len(d) == 8 and d.isdigit():
                        d = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
                    ohlcv.append({
                        'date': d,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume']) if 'volume' in row else None,
                    })

            # Convert advanced indicators to JSON-safe
            def _to_safe_list(arr):
                safe = []
                for x in arr:
                    if isinstance(x, float) and (x != x):  # NaN -> None
                        safe.append(None)
                    else:
                        safe.append(x)
                return safe

            adv_raw = getattr(analyzer, 'extra_indicators', {}) or {}
            adv_safe = {}
            for k, v in adv_raw.items():
                if isinstance(v, np.ndarray):
                    adv_safe[k] = _to_safe_list(v.tolist())
                elif isinstance(v, (list, tuple)):
                    adv_safe[k] = _to_safe_list(v)
                else:
                    adv_safe[k] = v

            result = {
                'stock_info': analyzer.stock_info,
                'price_info': analyzer.get_price_info(),
                'key_indicators': analyzer.get_key_indicators(),
                'ma_levels': analyzer.get_ma_levels(),
                'patterns': analyzer.patterns,
                'signals': analyzer.signals,
                'comprehensive_score': analyzer.综合评分,
                'advanced_indicators': adv_safe,
                'ohlcv': ohlcv,
            }
            
            # Clean all NaN/Infinity values before JSON serialization
            result = _clean_nan_values(result)
            return jsonify(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Serialization Error', 'details': str(e)}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stock_list')
def stock_list():
    try:
        from data_fetcher import DataFetcher
        fetcher = DataFetcher(use_proxy=True)
        stocks = fetcher.get_stock_list()
        return jsonify(stocks.to_dict('records')[:100])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


def _to_datetime_index(df):
    import pandas as pd
    import numpy as np
    data = df.copy()
    if not np.issubdtype(data['date'].dtype, np.datetime64):
        data['date'] = data['date'].astype(str).apply(
            lambda d: datetime.strptime(d, '%Y%m%d') if d.isdigit() and len(d) == 8 else pd.to_datetime(d)
        )
    data = data.set_index('date')
    data.index.name = 'Date'
    return data


def _clean_nan_values(obj):
    """Recursively replace NaN/Infinity with None and convert numpy types for JSON."""
    import math
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: _clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
         return _clean_nan_values(obj.tolist())
    else:
        return obj


def _generate_chart_png(analyzer, png_path: str):
    if not HAVE_REPORT:
        raise RuntimeError('reportlab/mplfinance not installed, cannot export PDF')

    import pandas as pd

    df = analyzer.data.copy()
    df = _to_datetime_index(df)
    cols_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
    for k, v in cols_map.items():
        if k in df.columns:
            df[v] = df[k].astype(float)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

    add_plots = []
    # MA20 & MA60
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    add_plots.append(mpf.make_addplot(df['MA20'], color='#2f7df6', width=1.2))
    add_plots.append(mpf.make_addplot(df['MA60'], color='#ffb703', width=1.2))

    # SuperTrend
    extra = getattr(analyzer, 'extra_indicators', {}) or {}
    st = extra.get('SuperTrend')
    if st is not None and len(st) == len(df):
        df['SuperTrend'] = pd.Series(st, index=df.index)
        add_plots.append(mpf.make_addplot(df['SuperTrend'], color='#26a69a', width=1.0))

    # Ichimoku cloud edges
    sa = extra.get('Ichimoku_SenkouA')
    sb = extra.get('Ichimoku_SenkouB')
    if sa is not None and sb is not None and len(sa) == len(df):
        df['SenkouA'] = pd.Series(sa, index=df.index)
        df['SenkouB'] = pd.Series(sb, index=df.index)
        add_plots.append(mpf.make_addplot(df['SenkouA'], color='#8bc34a', width=0.8, linestyle='--'))
        add_plots.append(mpf.make_addplot(df['SenkouB'], color='#e57373', width=0.8, linestyle='--'))

    # Configure Chinese font style
    # Use a style that supports Chinese (SimHei)
    my_style = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.family': CHINESE_FONT, 'axes.unicode_minus': False})

    mpf.plot(
        df,
        type='candle',
        style=my_style,
        addplot=add_plots,
        volume=True,
        mav=(),
        savefig=dict(fname=png_path, dpi=160, bbox_inches='tight')
    )


def _generate_pdf_report(analyzer, pdf_path: str, chart_png_path: str):
    if not HAVE_REPORT:
        raise RuntimeError('reportlab not installed, cannot export PDF')

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    margin = 2 * cm
    y = h - margin

    # Cover
    c.setFillColorRGB(0.11, 0.19, 0.29)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    
    # Use the registered Chinese font (default size 24 for title)
    c.setFont(CHINESE_FONT, 24)
    c.drawString(margin, y - 1 * cm, 'Stock Technical Analysis Report')
    
    c.setFont(CHINESE_FONT, 14)
    stock_name = analyzer.stock_info.get('name') if analyzer.stock_info else ''
    stock_code = analyzer.stock_info.get('code') if analyzer.stock_info else ''
    c.drawString(margin, y - 2.2 * cm, f'{stock_name} ({stock_code})')
    
    c.setFont(CHINESE_FONT, 10)
    c.drawString(margin, y - 3.2 * cm, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    c.showPage()

    # Summary
    c.setFillColorRGB(1, 1, 1); c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(CHINESE_FONT, 16); c.drawString(margin, h - margin, 'Summary')
    c.setFont(CHINESE_FONT, 11)
    price = analyzer.get_price_info()
    score = analyzer.综合评分 or {}
    lines = [
        f"Close: {price.get('close', 'NA')}",
        f"Change %: {price.get('change_pct', 0):+.2f}%",
        f"Volume: {price.get('volume', 0)}",
        f"Score: {score.get('score', 0):+.1f} / 100",
        f"Recommendation: {score.get('recommendation', 'NA')}",
        f"Regime: {score.get('regime', 'mixed')}",
    ]
    yy = h - margin - 1.2 * cm
    for line in lines:
        c.drawString(margin, yy, line); yy -= 0.8 * cm

    if os.path.exists(chart_png_path):
        img_w = w - 2 * margin
        img_h = img_w * 0.55
        c.drawImage(chart_png_path, margin, margin + 3 * cm, width=img_w, height=img_h, preserveAspectRatio=True)
    c.showPage()

    # Signals
    c.setFillColorRGB(1, 1, 1); c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(CHINESE_FONT, 16); c.drawString(margin, h - margin, 'Signals (Top 15)')
    c.setFont(CHINESE_FONT, 10)
    sigs = analyzer.signals or {}
    ordered = sorted(
        [(k, v) for k, v in sigs.items() if v.get('signal') != 'N/A'],
        key=lambda kv: kv[1].get('strength', 0), reverse=True
    )[:15]
    yy = h - margin - 1.2 * cm
    for name, s in ordered:
        line = f"{name:15s} | {s.get('signal','-'):6s} | {s.get('strength',0):3d} | {s.get('description','')}"
        c.drawString(margin, yy, line)
        yy -= 0.7 * cm
        if yy < margin:
            c.showPage(); yy = h - margin

    c.showPage(); c.save()


@app.route('/export_pdf')
def export_pdf():
    symbol = (request.args.get('symbol') or '').strip()
    if not symbol:
        return jsonify({'error': 'missing symbol'}), 400

    if not HAVE_REPORT:
        return jsonify({'error': 'reportlab/mplfinance not available on server'}), 500

    try:
        from analyzer import StockAnalyzer
    except Exception as e:
        return jsonify({'error': f'Missing backend dependency: {e}'}), 500

    analyzer = StockAnalyzer(use_proxy=True)
    if not analyzer.analyze(symbol, days=120):
        return jsonify({'error': 'analysis failed, check symbol or network'}), 400

    # Use temporary directory for Vercel/Cloud compatibility
    with tempfile.TemporaryDirectory() as tmpdirname:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f"{symbol}_{ts}"
        chart_path = os.path.join(tmpdirname, f"{base}_chart.png")
        pdf_path = os.path.join(tmpdirname, f"{base}_report.pdf")

        try:
            _generate_chart_png(analyzer, chart_path)
            _generate_pdf_report(analyzer, pdf_path, chart_path)

            # Read file into memory to serve it
            return send_file(pdf_path, as_attachment=True, download_name=f"{base}_report.pdf")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'PDF Generation Error: {str(e)}'}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Stock Technical Analyzer - Web UI")
    print("  Visit: http://localhost:5000")
    print("=" * 60 + "\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, threaded=False, host='0.0.0.0', port=port)