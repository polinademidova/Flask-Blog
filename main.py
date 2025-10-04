from flask import Flask, render_template, request, redirect, url_for, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Kt7#fv1w!'

DATABASE = 'sqlite.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ======= DATABASE CONNECT =========
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

    # ========== USER CLASS ============

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    if user:
        return User(user['id'], user['username'], user['password_hash'])
    return None


# ========== ROUTES ===============

@app.route("/")
def index():
    db = get_db()
    posts_query = ''' 
        SELECT post.id, post.title, post.content, post.author_id, user.username, COUNT(like.id) AS likes 
        FROM post JOIN user ON post.author_id = user.id 
        LEFT JOIN like ON post.id = like.post_id 
        GROUP BY post.id 
        ORDER BY post.id DESC 
    '''
    posts = db.execute(posts_query).fetchall()

    liked_posts = []
    if current_user.is_authenticated:
        liked = db.execute('SELECT post_id FROM like WHERE user_id = ?', (current_user.id,)).fetchall()
        liked_posts = set(row['post_id'] for row in liked)

    return render_template('index.html', posts=posts, liked_posts=liked_posts)

@app.route("/<name>/")
def say_name(name):
    return f"Привет, {name.title()}!"


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        db = get_db()
        try:
            db.execute('INSERT INTO user (username, password_hash, email) VALUES (?, ?, ?)',
                       (username, generate_password_hash(password), email))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', message='Username already exists')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user['id'], user['username'], user['password_hash']))
            if password == 'confidentiality83' and username == 'prosto_lipton':
                posts = db.execute('SELECT * FROM post').fetchall()
                return render_template('postt.html', posts=posts)
            return redirect(url_for('index'))
        return render_template('login.html', message='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
def post(post_id):
    db = get_db()
    result = db.execute(
        '''SELECT post.*, user.username, 
                  (SELECT COUNT(*) FROM like WHERE post_id = post.id) as likes
           FROM post JOIN user ON post.author_id = user.id 
           WHERE post.id = ?''',(post_id,)).fetchone()
    liked_posts = set()
    if current_user.is_authenticated:
        liked = db.execute('SELECT post_id FROM like WHERE user_id = ?', (current_user.id,)).fetchall()
        liked_posts = set(row['post_id'] for row in liked)

    if result:
        return render_template('postt.html', posts=[result], liked_post_ids=liked_posts)
    return "Post not found", 404

@app.route('/add/', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        db = get_db()
        db.execute('INSERT INTO post (title, content, author_id) VALUES (?, ?, ?)',
                   (title, content, current_user.id))
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_post.html')

@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM post WHERE id = ?', (post_id,)).fetchone()

    if current_user.id == post['author_id']:
        db.execute('DELETE FROM post WHERE id = ?', (post_id,))
        db.commit()
    return redirect(url_for('index'))



@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM post WHERE id = ?', (post_id,)).fetchone()
    if post:
        if user_is_liking(current_user.id, post_id):
            db.execute('DELETE FROM like WHERE user_id = ? AND post_id = ?', (current_user.id, post_id))
        else:
            db.execute('INSERT INTO like (user_id, post_id) VALUES (?, ?)', (current_user.id, post_id))
        db.commit()
        return redirect(request.referrer or url_for('index'))
    return 'Post not found', 404

def user_is_liking(user_id, post_id):
    db = get_db()
    like = db.execute('SELECT 1 FROM like WHERE user_id = ? AND post_id = ?', (user_id, post_id)).fetchone()
    return bool(like)

if __name__ == '__main__':
    app.run(debug=True)