from flask import Flask, jsonify, render_template, send_file, abort,session, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, UserMixin, login_required
# from numpy import error_message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date,timedelta,datetime
import pandas as pd
import os
import matplotlib
import matplotlib.pyplot as plt
import io
import numpy as np
import requests
from bs4 import BeautifulSoup

matplotlib.use('Agg')

backup_directory = 'C:\\Users\\User\\Desktop\\python project'
# קשור לsqlAlchemy
if not os.path.exists(backup_directory):
    os.makedirs(backup_directory)

app = Flask(__name__)
app.secret_key = 'your_unique_secret_key_here'
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.init_app(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shop.db"
db = SQLAlchemy(app)
# קשור לsqlAlchemy עד כאן

# מחלקת user
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    # מחלקת user עד כאן

    def get_id(self):
        return self.user_id

# טוען ובודק עם יש משתמש
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# מחלקת purchase
class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    item_name = db.Column(db.String, nullable=False)
    qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
# מחלקת purchase עד כאן

# יצירת טבלאות
with app.app_context():
    db.create_all()

@app.route("/")
def get():
    if current_user.is_authenticated:
        logout_user()
    return render_template("index.html")

@app.route("/Register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("Register.html")
    else:
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            error_message = "אנא הכנס אימייל וסיסמא בכדי להרשם"
            return render_template("Register.html",error_message=error_message)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template("Login.html", user=existing_user, existing_user_message="משתמש כבר קיים במערכת")
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user,remember=True)
        return redirect(url_for("personal_area"))

@app.route("/Login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("Login.html")
    else:
        email = request.form['email']
        password = request.form['password']
        if not email or not password:
            return render_template("Login.html", existing_user_message="אנא הכנס אימייל וסיסמא בכדי שתוכל להתחבר")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for("personal_area"))
        elif user:
            return render_template("Login.html", existing_user_message="סיסמא לא נכונה")
        else:
            return render_template("Register.html", error_message="עדיין לא נרשמת למערכת")
@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('get'))

@app.route("/personal_area")
def personal_area():
        if current_user.is_authenticated:
            user_id = current_user.user_id
            one_week_ago = datetime.now() - timedelta(weeks=1)
            purchases = Purchase.query.filter(Purchase.user_id == user_id, Purchase.date >= one_week_ago).all()
            return render_template("Personal_area.html", purchases=purchases, user=current_user)
        else:
            return render_template("Login.html", user=current_user)

@app.route("/add_purchase", methods=["GET", "POST"])
@login_required
def add_purchase():
    if request.method == "GET":
        return render_template("Add_purchase.html", user=current_user)
    else:
        if current_user.is_authenticated:
            item_name = request.form['item_name']
            qty = request.form['qty']
            price = request.form['price']
            category = request.form['category']
            error_messages = []
            if not item_name:
                error_messages.append("אנא הכנס שם פריט")
            if not qty:
                error_messages.append("אנא הכנס כמות")
            if not price:
                error_messages.append("אנא הכנס מחיר")
            if not category:
                error_messages.append("אנא הכנס קטגוריה")
            if error_messages:
                return render_template("Add_purchase.html", user=current_user, error_messages=error_messages)

            new_purchase = Purchase(user_id=current_user.user_id, item_name=item_name, qty=int(qty), price=float(price), category=category, date=datetime.now())
            db.session.add(new_purchase)
            db.session.commit()
            one_week_ago = datetime.now() - timedelta(weeks=1)
            purchases = Purchase.query.filter(Purchase.user_id == current_user.user_id,Purchase.date >= one_week_ago).all()
            return redirect(url_for('personal_area'))
        else:
            return render_template("Register.html", user=None)

@app.route("/delete_purchase/<int:purchase_id>", methods=["POST"])
@login_required
def delete_purchase(purchase_id):
    purchase = Purchase.query.get(purchase_id)
    if purchase and purchase.user_id == current_user.user_id:
        db.session.delete(purchase)
        db.session.commit()
    return redirect(url_for('get_more_purchases'))

@app.route("/edit_purchase/<int:purchase_id>", methods=["GET", "POST"])
@login_required
def edit_purchase(purchase_id):
    purchase = Purchase.query.get(purchase_id)
    if purchase is None or purchase.user_id != current_user.user_id:
        abort(404)

    if request.method == "POST":
        item_name = request.form['item_name']
        qty = request.form['qty']
        price = request.form['price']
        category = request.form['category']

        # עדכון המידע
        purchase.item_name = item_name
        purchase.qty = int(qty)
        purchase.price = float(price)
        purchase.category = category
        db.session.commit()

        return redirect(url_for('get_more_purchases'))

    return render_template("Edit_purchase.html", purchase=purchase)

@app.route("/profile/getMore", methods=["GET"])
def get_more_purchases():
    user_id = current_user.user_id
    more_purchases = Purchase.query.filter(Purchase.user_id == user_id).all()
    return render_template("Personal_area.html", purchases=more_purchases)

@app.route("/saveData", methods=["GET"])
@login_required
def save_data():
    if not current_user.is_authenticated:
        abort(403)
    user_id = current_user.user_id
    purchases = Purchase.query.filter_by(user_id=user_id).all()
    data = [{
        'item_name': purchase.item_name,
        'qty': purchase.qty,
        'price': purchase.price,
        'category': purchase.category,
        'date': purchase.date
    } for purchase in purchases]

    df = pd.DataFrame(data)

    backup_directory = 'C:\\Users\\User\\Desktop\\python project'
    # וצר
    # נתיב
    # לקובץ
    # CSV
    # שבו
    # יישמרו
    # הנתונים
    file_path = os.path.join(backup_directory, f'backup_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    # שומר
    # את
    # ה - DataFrame
    # לקובץ
    # CSV
    # בנתיב
    # שנוצר
    df.to_csv(file_path, index=False)
    return redirect(url_for('personal_area'))


@app.route("/downloadData", methods=["GET"])
def download_data():
    backup_directory = 'C:\\Users\\User\\Desktop\\python project'
    csv_files = [f for f in os.listdir(backup_directory) if f.endswith('.csv')]

    if not csv_files:
        abort(404)

    latest_file = max(csv_files, key=lambda f: os.path.getctime(os.path.join(backup_directory, f)))

    return send_file(os.path.join(backup_directory, latest_file), as_attachment=True)


@app.route("/graph1")
@login_required
def graph1():
    user_id = current_user.user_id
    purchases = Purchase.query.filter_by(user_id=user_id).all()

    df = pd.DataFrame([{
        'date': purchase.date,
        'price': purchase.price
    } for purchase in purchases])
# not non
    df.dropna(subset=['price'], inplace=True)
    df.set_index('date', inplace=True)
    # מחשב
    weekly_expenses = df.resample('W').sum()
    # יוצר גודל וכו''
    plt.figure(figsize=(10, 5))
    # מייצר
    plt.plot(weekly_expenses.index, weekly_expenses['price'], marker='o')
    # כותרות
    plt.title('Total expenses each week')
    plt.xlabel('date')
    plt.ylabel('expenses')
    plt.grid()

    img_path = os.path.join('static', 'graphs', f'weekly_expenses_{user_id}.png')
    plt.savefig(img_path)
    plt.close()

    return redirect(url_for('show_graphs', graph1=f'weekly_expenses_{user_id}.png'))

@app.route("/graph2")
@login_required
def graph2():
    user_id = current_user.user_id
    purchases = Purchase.query.filter_by(user_id=user_id).all()

    df = pd.DataFrame([{
        'date': purchase.date,
        'price': purchase.price,
        'category': purchase.category
    } for purchase in purchases])

    df.dropna(subset=['price'], inplace=True)
# ממיר
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    # מחשב
    monthly_expenses = df.groupby('month')['price'].sum()

    plt.figure(figsize=(10, 5))
    monthly_expenses.plot(kind='bar')
    plt.title('Monthly Expenses Comparison')
    plt.xlabel('Month')
    plt.ylabel('Total Expenses')
    plt.grid()

    img_path = os.path.join('static', 'graphs', f'monthly_expenses_{user_id}.png')
    plt.savefig(img_path)
    plt.close()

    return redirect(url_for('show_graphs', graph2=f'monthly_expenses_{user_id}.png'))

@app.route("/graphs")
@login_required
def show_graphs():
    graph1 = request.args.get('graph1')
    graph2 = request.args.get('graph2')
    return render_template('graphs.html', graph1=graph1, graph2=graph2)

def create_graph1(data):
    plt.figure(figsize=(10, 5))
    plt.plot(data['Date'], data['Price'], marker='o')
    plt.title('Purchases Over Time')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid()
    graph_path = os.path.join('static', 'graphs', 'demo_graph1.png')
    plt.savefig(graph_path)
    plt.close()
    return graph_path

def create_graph2(data):
    plt.figure(figsize=(10, 5))
    # מחשב
    data.groupby('Name')['Price'].sum().plot(kind='bar')
    plt.title('Total Price per Item')
    plt.xlabel('Item')
    plt.ylabel('Total Price')
    plt.grid()
    graph_path = os.path.join('static', 'graphs', 'demo_graph2.png')
    plt.savefig(graph_path)
    plt.close()
    return graph_path

@app.route("/demoProfile", methods=["GET"])
def demo_profile():
    purchase_codes = np.array([1, 2, 3, 4, 5])
    purchase_names = np.array(['לחם', 'חלב', 'ביצים', 'סוכר', 'קפה'])
    purchase_prices = np.array([6.5, 6.8, 35, 4.7, 32.9])
    purchase_dates = np.array(['2025-02-01', '2025-04-22', '2025-03-03', '2025-04-18', '2025-01-05'])

    #  רשימה של רכישות
    purchases = [{'Code': code, 'Name': name, 'Price': price, 'Date': date}
                 for code, name, price, date in zip(purchase_codes, purchase_names, purchase_prices, purchase_dates)]

    df = pd.DataFrame(purchases)

    last_week = datetime.now() - timedelta(days=7)
    df['Date'] = pd.to_datetime(df['Date'])
    recent_purchases = df[df['Date'] >= last_week]

    return render_template('Demo_profile.html', df=recent_purchases)

@app.route("/demoProfile/getMore", methods=["GET"])
def get_more_purchases_Demo():
    # נתונים קבועים עם numpy
    purchase_codes = np.array([1, 2, 3, 4, 5])
    purchase_names = np.array(['לחם', 'חלב', 'ביצים', 'סוכר', 'קפה'])
    purchase_prices = np.array([6.5, 6.8, 35, 4.7, 32.9])
    purchase_dates = np.array(['2025-02-01', '2025-04-22', '2025-03-03', '2025-04-18', '2025-01-05'])

    purchases = [{'Code': code, 'Name': name, 'Price': price, 'Date': date}
                 for code, name, price, date in zip(purchase_codes, purchase_names, purchase_prices, purchase_dates)]

    df = pd.DataFrame(purchases)
    if df.empty:
        return render_template('Demo_profile.html', df=df)  # זה יגרום להציג "אין קניות להציג"

    df['Date'] = pd.to_datetime(df['Date'])

    return render_template('Demo_profile.html', df=df)


@app.route("/optimize_purchases", methods=["GET"])
@login_required
def optimize_purchases():
    user_id = current_user.user_id
    purchases = Purchase.query.filter_by(user_id=user_id).all()

    with open('templates/Shop.html', 'r',encoding='utf-8') as htmlFile:
        content = htmlFile.read()
        soup = BeautifulSoup(content, 'html.parser')

    products = {}
    for product in soup.findAll('div'):
        name = product.find('h3').text.strip()
        price = float(product.find('p').text.strip().replace(' ש"ח', '').replace(',', '.'))  # המרת מחיר ל-float
        products[name] = price

    optimized_purchases=[]
    for purchase in purchases:
        item_name=purchase.item_name
        price=purchase.price
        if item_name in products:
            shop_price = products[item_name]
            if shop_price < price:
                optimized_purchases.append({
                    'item_name': item_name,
                    'price_paid': price,
                    'shop_price': shop_price
                })
    return render_template("Optimized_purchases.html", optimized_purchases=optimized_purchases)

if __name__ == "__main__":
    print(os.getcwd())
    app.run(debug=True)