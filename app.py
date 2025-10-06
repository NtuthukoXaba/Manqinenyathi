from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Simulated user roles
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "cooker": {"password": "cook123", "role": "cooker"},
    "delivery": {"password": "deliver123", "role": "delivery"}
}

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = USERS.get(username)

        if user and user['password'] == password:
            role = user['role']
            if role == 'admin':
                return redirect(url_for('dashboard_admin'))
            elif role == 'cooker':
                return redirect(url_for('dashboard_cooker'))
            elif role == 'delivery':
                return redirect(url_for('dashboard_delivery'))
        else:
            return render_template('home.html', error="Invalid username or password")
    return render_template('home.html', error=None)

@app.route('/dashboard/admin')
def dashboard_admin():
    return render_template('dashboard_admin.html')

@app.route('/dashboard/cooker')
def dashboard_cooker():
    return render_template('dashboard_cooker.html')

@app.route('/dashboard/delivery')
def dashboard_delivery():
    return render_template('dashboard_delivery.html')

if __name__ == "__main__":
    app.run(debug=True)
