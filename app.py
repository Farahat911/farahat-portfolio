import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

# ==========================================
# حل مشكلة الـ 500 Error على PythonAnywhere
# تحديد المسار الكامل لملفات المشروع
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'portfolio.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

app = Flask(__name__)
app.secret_key = 'farahat_2026_secure'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH) # استخدام المسار الثابت
    conn.row_factory = sqlite3.Row
    return conn

def upgrade_db():
    conn = get_db_connection()
    new_columns = ['link', 'github_link', 'video_link', 'full_description', 'extra_image_1', 'extra_image_2']
    for col in new_columns:
        try:
            conn.execute(f'ALTER TABLE projects ADD COLUMN {col} TEXT DEFAULT ""')
        except:
            pass
    conn.commit()
    conn.close()

upgrade_db()

@app.route('/')
def index():
    conn = get_db_connection()
    try:
        settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
        settings_dict = {row['key']: row['value'] for row in settings_rows}
        projects = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
    except:
        settings_dict = {}
        projects = []
    conn.close()
    return render_template('index.html', settings=settings_dict, projects=projects)

@app.route('/projects/<category>')
def projects(category):
    conn = get_db_connection()
    projects_data = conn.execute('SELECT * FROM projects WHERE category = ? ORDER BY id DESC', (category,)).fetchall()
    settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
    settings_dict = {row['key']: row['value'] for row in settings_rows}
    conn.close()
    
    titles = {
        "software": "Software & AI Projects",
        "automation": "Automation Projects",
        "arduino": "Arduino & Hardware Projects"
    }
    page_title = titles.get(category, "Projects")
    return render_template('projects.html', projects=projects_data, page_title=page_title, settings=settings_dict)

@app.route('/project/<int:id>')
def project_detail(id):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (id,)).fetchone()
    settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
    settings_dict = {row['key']: row['value'] for row in settings_rows}
    conn.close()
    
    if not project:
        return redirect(url_for('index'))
        
    return render_template('project_detail.html', project=project, settings=settings_dict)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        if user == 'admin' and pw == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Invalid Credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
    messages = conn.execute('SELECT * FROM messages ORDER BY id DESC').fetchall()
    settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
    settings_dict = {row['key']: row['value'] for row in settings_rows}
    conn.close()
    return render_template('admin.html', projects=projects, messages=messages, settings=settings_dict)

@app.route('/admin/update_settings', methods=['POST'])
def update_settings():
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    keys = ['hero_name', 'hero_job', 'about_text', 'contact_email', 'footer_text']
    for key in keys:
        if key in request.form:
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (request.form[key], key))
    if 'hero_image' in request.files:
        file = request.files['hero_image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE settings SET value = ? WHERE key = 'hero_image'", (filename,))
    conn.commit()
    conn.close()
    flash('Updated Successfully!')
    return redirect(url_for('admin'))

@app.route('/admin/add_project', methods=['POST'])
def add_project():
    if 'admin' not in session: return redirect(url_for('login'))
    
    title = request.form.get('title', '')
    cat = request.form.get('category', '')
    tags = request.form.get('tags', '')
    desc = request.form.get('description', '')
    link = request.form.get('link', '')
    github_link = request.form.get('github_link', '')
    video_link = request.form.get('video_link', '')
    full_desc = request.form.get('full_description', '')
    
    filename = ''
    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    extra1 = ''
    if 'extra_image_1' in request.files and request.files['extra_image_1'].filename != '':
        f1 = request.files['extra_image_1']
        extra1 = secure_filename(f1.filename)
        f1.save(os.path.join(app.config['UPLOAD_FOLDER'], extra1))
        
    extra2 = ''
    if 'extra_image_2' in request.files and request.files['extra_image_2'].filename != '':
        f2 = request.files['extra_image_2']
        extra2 = secure_filename(f2.filename)
        f2.save(os.path.join(app.config['UPLOAD_FOLDER'], extra2))
            
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO projects 
        (title, category, tags, description, image, link, github_link, video_link, full_description, extra_image_1, extra_image_2) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, cat, tags, desc, filename, link, github_link, video_link, full_desc, extra1, extra2))
    conn.commit()
    conn.close()
    flash('Project Added')
    return redirect(url_for('admin'))

@app.route('/admin/edit_project/<int:id>', methods=['POST'])
def edit_project(id):
    if 'admin' not in session: return redirect(url_for('login'))
    
    title = request.form.get('title', '')
    cat = request.form.get('category', '')
    tags = request.form.get('tags', '')
    desc = request.form.get('description', '')
    link = request.form.get('link', '')
    github_link = request.form.get('github_link', '')
    video_link = request.form.get('video_link', '')
    full_desc = request.form.get('full_description', '')
    
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE projects 
        SET title=?, category=?, tags=?, description=?, link=?, github_link=?, video_link=?, full_description=? 
        WHERE id=?
    ''', (title, cat, tags, desc, link, github_link, video_link, full_desc, id))
    
    if 'image' in request.files and request.files['image'].filename != '':
        f = request.files['image']
        filename = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn.execute("UPDATE projects SET image=? WHERE id=?", (filename, id))
        
    if 'extra_image_1' in request.files and request.files['extra_image_1'].filename != '':
        f1 = request.files['extra_image_1']
        extra1 = secure_filename(f1.filename)
        f1.save(os.path.join(app.config['UPLOAD_FOLDER'], extra1))
        conn.execute("UPDATE projects SET extra_image_1=? WHERE id=?", (extra1, id))
        
    if 'extra_image_2' in request.files and request.files['extra_image_2'].filename != '':
        f2 = request.files['extra_image_2']
        extra2 = secure_filename(f2.filename)
        f2.save(os.path.join(app.config['UPLOAD_FOLDER'], extra2))
        conn.execute("UPDATE projects SET extra_image_2=? WHERE id=?", (extra2, id))

    conn.commit()
    conn.close()
    flash('Project Edited')
    return redirect(url_for('admin'))

@app.route('/admin/delete_project/<int:id>')
def delete_project(id):
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM projects WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    sub = request.form.get('subject', '')
    msg = request.form.get('message', '')
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (name, email, subject, message) VALUES (?, ?, ?, ?)', (name, email, sub, msg))
    conn.commit()
    conn.close()
    flash('Message sent successfully!')
    return redirect(url_for('index'))

@app.route('/admin/delete_msg/<int:id>')
def delete_msg(id):
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM messages WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)