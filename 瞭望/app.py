from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import datetime
import os
import sys
from baidu_spider import baidu_spider
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
import tempfile

# 设置默认编码为UTF-8
if sys.version_info[0] >= 3:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于会话加密的密钥
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应中的中文正常显示

# 数据库初始化
def init_db():
    conn = sqlite3.connect('app.db')
    conn.text_factory = str  # 设置文本工厂为str以支持中文
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建搜索结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT NOT NULL,
            cover_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认管理员用户
    try:
        cursor.execute('''
            INSERT INTO users (username, password) VALUES (?, ?)
        ''', ('admin', 'admin888'))
    except sqlite3.IntegrityError:
        # 用户已存在
        pass
    
    conn.commit()
    conn.close()

# 登录页面
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('app.db')
        conn.text_factory = str  # 设置文本工厂为str以支持中文
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# 登出功能
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 后台主页
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# 搜索功能
@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    keyword = request.form['keyword']
    if not keyword:
        flash('请输入搜索关键字')
        return redirect(url_for('dashboard'))
    
    # 调用百度爬虫
    results = baidu_spider(keyword)
    session['search_results'] = results
    session['current_keyword'] = keyword
    
    return render_template('search_results.html', results=results, keyword=keyword)

# 保存搜索结果到数据库
@app.route('/save_results', methods=['POST'])
def save_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    results = session.get('search_results', [])
    keyword = session.get('current_keyword', '')
    
    if not results:
        flash('没有可保存的搜索结果')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('app.db')
    conn.text_factory = str  # 设置文本工厂为str以支持中文
    cursor = conn.cursor()
    
    try:
        for result in results:
            cursor.execute('''
                INSERT INTO search_results (keyword, title, summary, url, cover_url) 
                VALUES (?, ?, ?, ?, ?)
            ''', (keyword, result['title'], result['summary'], result['url'], result['cover_url']))
        conn.commit()
        flash(f'成功保存 {len(results)} 条搜索结果')
    except Exception as e:
        flash(f'保存失败: {str(e)}')
    finally:
        conn.close()
    
    return redirect(url_for('data_warehouse'))

# 数据仓库页面
@app.route('/data_warehouse')
def data_warehouse():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('app.db')
    conn.text_factory = str  # 设置文本工厂为str以支持中文
    cursor = conn.cursor()
    
    # 获取所有搜索结果
    cursor.execute('SELECT * FROM search_results ORDER BY created_at DESC')
    results = cursor.fetchall()
    conn.close()
    
    return render_template('data_warehouse.html', results=results)

# 搜索结果检索
@app.route('/search_data', methods=['POST'])
def search_data():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    keyword = request.form['search_keyword']
    
    conn = sqlite3.connect('app.db')
    conn.text_factory = str  # 设置文本工厂为str以支持中文
    cursor = conn.cursor()
    
    # 根据关键字搜索
    cursor.execute('''
        SELECT * FROM search_results 
        WHERE keyword LIKE ? OR title LIKE ? OR summary LIKE ? 
        ORDER BY created_at DESC
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    results = cursor.fetchall()
    conn.close()
    
    return render_template('data_warehouse.html', results=results, search_keyword=keyword)

# 生成PDF报告
@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # 验证用户是否登录
    if 'username' not in session:
        return redirect(url_for('login'))
    
    search_keyword = request.form.get('search_keyword', '')
    
    # 连接数据库
    conn = sqlite3.connect('app.db')
    conn.text_factory = str  # 设置文本工厂为str以支持中文
    cursor = conn.cursor()
    
    # 查询数据
    if search_keyword:
        cursor.execute('''
            SELECT * FROM search_results WHERE keyword LIKE ? OR title LIKE ? OR summary LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{search_keyword}%', f'%{search_keyword}%', f'%{search_keyword}%'))
    else:
        cursor.execute('SELECT * FROM search_results ORDER BY created_at DESC')
    
    results = cursor.fetchall()
    conn.close()
    
    # 创建临时PDF文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        temp_pdf_path = temp_pdf.name
    
    # 创建PDF文档
    doc = SimpleDocTemplate(temp_pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # 居中对齐
        spaceAfter=12,
        textColor=colors.HexColor('#000000')
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.HexColor('#333333')
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        textColor=colors.HexColor('#000000')
    )
    
    # 构建PDF内容
    story = []
    
    # 添加标题
    story.append(Paragraph('智能瞭望数据分析处理系统报告', title_style))
    story.append(Spacer(1, 12))
    
    # 添加报告信息
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f'生成时间: {current_time}', normal_style))
    story.append(Paragraph(f'数据数量: {len(results)}', normal_style))
    if search_keyword:
        story.append(Paragraph(f'搜索关键字: {search_keyword}', normal_style))
    story.append(Spacer(1, 12))
    
    # 添加数据表格
    if results:
        # 表格标题
        story.append(Paragraph('数据概览', heading_style))
        story.append(Spacer(1, 6))
        
        # 表格数据
        table_data = [['关键字', '标题', 'URL', '日期']]
        for result in results:
            keyword = result[1]
            title = result[2][:30] + '...' if len(result[2]) > 30 else result[2]
            url = result[4][:40] + '...' if len(result[4]) > 40 else result[4]
            date_str = result[6][:10] if len(result[6]) >= 10 else result[6]
            table_data.append([keyword, title, url, date_str])
        
        # 创建表格
        table = Table(table_data, colWidths=[4 * cm, 6 * cm, 8 * cm, 2 * cm])
        
        # 设置表格样式
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CCCCCC')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
        ]))
        
        story.append(table)
        story.append(Spacer(1, 12))
        
        # 添加详细内容
        story.append(Paragraph('详细内容', heading_style))
        story.append(Spacer(1, 6))
        
        for i, result in enumerate(results, 1):
            story.append(Paragraph(f'第 {i} 条数据', ParagraphStyle(
                'DataItem',
                parent=styles['Heading3'],
                fontSize=11,
                spaceAfter=6
            )))
            
            story.append(Paragraph(f'关键字: {result[1]}', normal_style))
            story.append(Paragraph(f'标题: {result[2]}', normal_style))
            story.append(Paragraph(f'URL: {result[4]}', normal_style))
            story.append(Paragraph(f'日期: {result[6]}', normal_style))
            
            if result[3]:
                story.append(Paragraph('概要:', ParagraphStyle(
                    'SummaryLabel',
                    parent=styles['Normal'],
                    fontSize=10,
                    spaceAfter=2,
                    fontName='Helvetica-Bold'
                )))
                story.append(Paragraph(result[3], normal_style))
            
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph('没有找到数据', normal_style))
    
    # 生成PDF
    doc.build(story)
    
    # 返回PDF文件
    return send_file(temp_pdf_path, as_attachment=True, download_name=f'智能瞭望报告_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)