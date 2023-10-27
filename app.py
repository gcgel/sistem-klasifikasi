from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import category_encoders as ce
import hashlib
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import joblib 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/latihan_skripsi'
db = SQLAlchemy(app)

db_host = 'localhost'
db_user = 'root'
db_password = ''
db_name = 'db_skripsi'
table_name = 'data'

engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
db_connection = engine.connect()

label_encoder = LabelEncoder()

clf = None
encoder = None

try:
    clf = joblib.load('model.pkl')
    encoder = joblib.load('encoder.pkl')
except FileNotFoundError:
    print("File model atau encoder tidak ditemukan. Pastikan Anda telah menjalankan skrip untuk melatih model dan menyimpannya.")

def update_data_train():
    query = f"SELECT * FROM {table_name}"
    data_train = pd.read_sql(query, db_connection)

    label_encoder.fit(data_train['label'])
    data_train['label_encoded'] = label_encoder.transform(data_train['label'])
    data_train['label_decoded'] = label_encoder.inverse_transform(data_train['label_encoded'])

    return data_train

def update_classifier(data_train):
    encoder = ce.OneHotEncoder(cols=['pendidikan', 'pekerjaan', 'status_kepemilikan', 'kondisi_rumah'])
    fitur_train = encoder.fit_transform(data_train.drop(['id', 'nama', 'no_kk', 'alamat', 'label', 'label_encoded', 'label_decoded'], axis=1))
    target_train = data_train["label_encoded"]

    clf = MultinomialNB()
    clf.fit(fitur_train, target_train)

    return clf, encoder

data_train = update_data_train()

@app.route('/classify', methods=['POST'])
def classify():
    try:
        nama = request.form['nama']
        no_kk = request.form['no_kk']
        alamat = request.form['alamat']
        jumlah_tanggungan = int(request.form['jumlah_tanggungan'])
        pendidikan = request.form['pendidikan']
        pekerjaan = request.form['pekerjaan']
        penghasilan = int(request.form['penghasilan'])
        jumlah_mobil = int(request.form['jumlah_mobil'])
        jumlah_motor = int(request.form['jumlah_motor'])
        status_kepemilikan = request.form['status_kepemilikan']
        kondisi_rumah = request.form['kondisi_rumah']
 
        new_data = pd.DataFrame({
            'jumlah_tanggungan': [jumlah_tanggungan],
            'pendidikan': [pendidikan],
            'pekerjaan': [pekerjaan],
            'penghasilan': [penghasilan],
            'jumlah_mobil': [jumlah_mobil],
            'jumlah_motor': [jumlah_motor],
            'status_kepemilikan': [status_kepemilikan],
            'kondisi_rumah': [kondisi_rumah]
        })
 
        data_train = update_data_train()
        clf, encoder = update_classifier(data_train)
        new_data_encoded = encoder.transform(new_data)
        prediction_encoded = clf.predict(new_data_encoded)[0]
        prediction_label = label_encoder.inverse_transform([prediction_encoded])[0]

        new_data_with_names = pd.DataFrame({
            'nama': [nama],
            'no_kk': [no_kk],
            'alamat': [alamat],
            'jumlah_tanggungan': [jumlah_tanggungan],
            'pendidikan': [pendidikan],
            'pekerjaan': [pekerjaan],
            'penghasilan': [penghasilan],
            'jumlah_mobil': [jumlah_mobil],
            'jumlah_motor': [jumlah_motor],
            'status_kepemilikan': [status_kepemilikan],
            'kondisi_rumah': [kondisi_rumah],
            'label': [prediction_label]
        })

        new_data_with_names.to_sql(table_name, db_connection, if_exists='append', index=False)
        db_connection.commit()
        
        flash("Data berhasil ditambahkan.", "success") 
        flash(f'Hasil prediksi: {prediction_label}', 'info')
        
        return render_template('klasifikasi.html')
    except Exception as e:
        error = "An error occurred during classification: " + str(e)
        return render_template('klasifikasi.html', error=error)
    
@app.route('/')
def index():
    if 'user' in session:  
        return render_template('index.html', datatrain=data_train)
    else:
        return redirect('/login')
    
@app.route('/dashboard', methods=['POST'])
def dashboard():
    return render_template('index.html', datatrain=data_train)

@app.route('/get_data/<int:page>')
def get_data(page):
    per_page = 15
    start = (page - 1) * per_page

    query = f"SELECT * FROM {table_name} LIMIT {start}, {per_page}"
    data_for_page = pd.read_sql(query, db_connection)

    total_data_query = f"SELECT COUNT(*) FROM {table_name}"
    total_data = int(pd.read_sql(total_data_query, db_connection).iloc[0, 0])

    data_dict = data_for_page.to_dict(orient='records')

    total_pages = total_data // per_page + (1 if total_data % per_page > 0 else 0)

    response = {
        'data': data_dict,
        'totalPages': total_pages
    }

    return jsonify(response), 200

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        hashed_password = hashlib.md5(password.encode()).hexdigest()

        login_query = text("SELECT * FROM users WHERE `username` = :username AND `password` = :password")
        data_user = pd.read_sql(login_query, db_connection, params={'username': username, 'password': hashed_password})

        if not data_user.empty:
            if username == data_user['username'].iloc[0] and hashed_password == data_user['password'].iloc[0]:
                session['user'] = username
                flash(f"Login berhasil, Selamat datang {data_user['nama_user'].iloc[0]}!", "success")
                return redirect(url_for('index'))
            else:
                error = "Login gagal. Periksa kembali username dan password Anda."
                flash(error, "danger")
                return render_template('login.html', error=error)
        else:
            error = "Login gagal. Periksa kembali username dan password Anda."
            flash(error, "danger")
            return render_template('login.html', error=error)
    return render_template('login.html')

# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect('/login') 

# Classify route
@app.route('/klasifikasi', methods=['POST'])
def klasifikasi():
    return render_template('klasifikasi.html') 

# Manajemen admin route
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    query = text("SELECT * FROM users")
    admin_data = pd.read_sql(query, db_connection)

    return render_template('admin.html', admin_data=admin_data)

# Endpoint untuk menghapus data
@app.route('/delete_data/<int:data_id>', methods=['POST'])
def delete_data(data_id):
    try:
        delete_query = text(f"DELETE FROM {table_name} WHERE id = :data_id")
        db_connection.execute(delete_query, {'data_id': data_id})
        db_connection.commit()

        flash("Data berhasil dihapus.", "success")  

        return redirect(url_for('index'))
    except Exception as e:
        error = "Terjadi Kesalahan: " + str(e)
        return render_template('index.html', error=error)

def check_username(username, user_id):
    check_query = text("SELECT COUNT(*) FROM users WHERE username = :username AND id != :user_id")
    result = db_connection.execute(check_query, {'username': username, 'user_id': user_id}).scalar()
    return result > 0

# Endpoint untuk menghapus user
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        delete_query = text("DELETE FROM users WHERE id = :user_id")
        db_connection.execute(delete_query, {'user_id': user_id})
        db_connection.commit()

        flash("Admin berhasil dihapus.", "success")

        return redirect(url_for('admin')) 
    except Exception as e:
        error = "Terjadi Kesalahan: " + str(e)
        return render_template('admin.html', error=error)

# Endpoint untuk edit user
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user' in session:
        if request.method == 'POST':
            user_query = text("SELECT * FROM users WHERE id = :user_id")
            user_data = pd.read_sql(user_query, db_connection, params={'user_id': user_id})
            
            if user_data.empty:
                flash("Admin tidak ditemukan.", "danger")
                return redirect(url_for('admin'))

            new_nama_user = request.form.get('new_nama_user')
            new_username = request.form.get('new_username')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not new_nama_user or not new_username:
                flash("Nama Lengkap dan Username harus diisi.", "danger")
                return render_template('edit-user.html', user_data=user_data.iloc[0])
            
            if not new_password:
                new_password = user_data['password'].iloc[0]

            if not confirm_password:
                confirm_password = user_data['password'].iloc[0]

            if new_password != confirm_password:
                flash("Password dan konfirmasi password tidak cocok.", "danger")
                return render_template('edit-user.html', user_data=user_data.iloc[0])

            if new_password != user_data['password'].iloc[0]:
                hashed_password = hashlib.md5(new_password.encode()).hexdigest()
            else:
                hashed_password = new_password

            if check_username(new_username, user_id):
                flash("Username sudah ada. Silakan pilih username lain.", "danger")
                return render_template('edit-user.html', user_data=user_data.iloc[0])

            try:
                update_query = text("UPDATE users SET nama_user = :new_nama_user, username = :new_username, password = :new_password WHERE id = :user_id")
                db_connection.execute(update_query, {'new_nama_user': new_nama_user, 'new_username': new_username, 'new_password': hashed_password, 'user_id': user_id})
                db_connection.commit()

                flash(f"Data pengguna {user_data['nama_user'].iloc[0]} berhasil diubah.", "success")

                return redirect(url_for('admin'))
            except Exception as e:
                flash("Terjadi Kesalahan: " + str(e), "danger")
                return render_template('edit-user.html', user_data=user_data.iloc[0])
        else:
            user_query = text("SELECT * FROM users WHERE id = :user_id")
            user_data = pd.read_sql(user_query, db_connection, params={'user_id': user_id})

            if not user_data.empty:
                return render_template('edit-user.html', user_data=user_data.iloc[0])
            else:
                flash("User tidak ditemukan.", "danger")
                return redirect(url_for('admin'))

# Endpoint untuk menambah admin
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user' in session:
        if request.method == 'POST':
            new_nama_user = request.form.get('new_nama_user')
            new_username = request.form.get('new_username')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not new_password or not confirm_password:
                return render_template('add-user.html')

            if new_password != confirm_password:
                flash("Password dan konfirmasi password tidak cocok.", "danger")
                return render_template('add-user.html')

            hashed_password = hashlib.md5(new_password.encode()).hexdigest()

            try:
                if check_username(new_username, user_id=None):
                    flash("Username sudah ada. Silakan pilih username lain.", "danger")
                    return render_template('add-user.html')

                insert_query = text("INSERT INTO users (nama_user, username, password) VALUES (:new_nama_user, :new_username, :new_password)")
                db_connection.execute(insert_query, {'new_nama_user': new_nama_user, 'new_username': new_username, 'new_password': hashed_password})
                db_connection.commit()

                flash("Pengguna baru berhasil ditambahkan.", "success")

                return redirect(url_for('admin'))
            except IntegrityError as e:
                db_connection.rollback()
                error = "Terjadi Kesalahan: " + str(e)
                return render_template('add-user.html', error=error)
        else:
            return render_template('add-user.html')

if __name__ == '__main__':
    app.run(debug=True)
