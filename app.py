from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///manqinenyathi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models (unchanged)
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'cooker', 'delivery'), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    deliveries = db.relationship('Delivery', backref='delivery_guy', foreign_keys='Delivery.delivery_guy_id')
    attendance = db.relationship('Attendance', backref='cooker', foreign_keys='Attendance.cooker_id')
    learners = db.relationship('Learner', backref='cooker', foreign_keys='Learner.cooker_id')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class School(db.Model):
    __tablename__ = 'schools'
    school_id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    deliveries = db.relationship('Delivery', backref='school')
    attendance = db.relationship('Attendance', backref='school')
    learners = db.relationship('Learner', backref='school')

class Delivery(db.Model):
    __tablename__ = 'deliveries'
    delivery_id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(150), nullable=False)
    delivery_guy_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.Enum('Pending', 'Delivered'), default='Pending')
    delivered_time = db.Column(db.DateTime)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    attendance_id = db.Column(db.Integer, primary_key=True)
    cooker_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_in = db.Column(db.DateTime)
    time_out = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Learner(db.Model):
    __tablename__ = 'learners'
    learner_id = db.Column(db.Integer, primary_key=True)
    learner_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    cooker_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.school_id'), nullable=False)
    date_served = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(20), default='Lunch') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Updated Routes with Email Authentication
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        
        print(f"Login attempt: {email}")  # Debug print
        
        # Query user by email instead of username
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"User found: {user.email}, Role: {user.role}")  # Debug print
            print(f"Password check: {user.check_password(password)}")  # Debug print
            
        if user and user.check_password(password):
            session['user_id'] = user.user_id
            session['username'] = user.full_name
            session['email'] = user.email
            session['role'] = user.role
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('dashboard_admin'))
            elif user.role == 'cooker':
                return redirect(url_for('dashboard_cooker'))
            elif user.role == 'delivery':
                return redirect(url_for('dashboard_delivery'))
        else:
            print("Invalid credentials")  # Debug print
            return render_template('home.html', error="Invalid email or password")
    
    return render_template('home.html', error=None)

@app.route('/dashboard/admin')
def dashboard_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    total_schools = School.query.count()
    total_workers = User.query.count()
    recent_deliveries = Delivery.query.order_by(Delivery.delivery_date.desc()).limit(5).all()
    
    return render_template('dashboard_admin.html', 
                         total_schools=total_schools,
                         total_workers=total_workers,
                         recent_deliveries=recent_deliveries)

@app.route('/dashboard/cooker')
def dashboard_cooker():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Get assigned school for the cooker
    assigned_school = School.query.first()  # Modify this based on your assignment logic
    
    # Get today's learners count
    learners_fed_today = Learner.query.filter_by(
        cooker_id=user_id, 
        date_served=today
    ).count()
    
    # Get today's attendance record
    today_attendance = Attendance.query.filter_by(
        cooker_id=user_id, 
        date=today
    ).first()
    
    # Calculate work hours for today
    work_hours = 0
    if today_attendance and today_attendance.time_in and today_attendance.time_out:
        time_diff = today_attendance.time_out - today_attendance.time_in
        work_hours = round(time_diff.total_seconds() / 3600, 1)
    
    # Calculate days worked this month
    days_worked_this_month = Attendance.query.filter(
        Attendance.cooker_id == user_id,
        db.extract('month', Attendance.date) == current_month,
        db.extract('year', Attendance.date) == current_year,
        Attendance.time_in.isnot(None)
    ).count()
    
    # Total days in current month
    import calendar
    total_days_in_month = calendar.monthrange(current_year, current_month)[1]
    
    return render_template('dashboard_cooker.html',
                         assigned_school=assigned_school,
                         learners_fed_today=learners_fed_today,
                         work_hours=work_hours,
                         days_worked=f"{days_worked_this_month}/{total_days_in_month}",
                         today_attendance=today_attendance,
                         today=today)

@app.route('/dashboard/delivery')
def dashboard_delivery():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    return render_template('dashboard_delivery.html')

# School Management Routes
@app.route('/admin/schools')
def manage_schools():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    schools = School.query.order_by(School.school_name).all()
    return render_template('manage_schools.html', schools=schools)

@app.route('/admin/schools/add', methods=['GET', 'POST'])
def add_school():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        school_name = request.form['school_name']
        location = request.form['location']
        contact_person = request.form['contact_person']
        contact_number = request.form['contact_number']
        
        # Check if school already exists
        existing_school = School.query.filter_by(school_name=school_name).first()
        if existing_school:
            flash('A school with this name already exists!', 'error')
            return render_template('add_school.html')
        
        # Create new school
        new_school = School(
            school_name=school_name,
            location=location,
            contact_person=contact_person,
            contact_number=contact_number
        )
        
        try:
            db.session.add(new_school)
            db.session.commit()
            flash('School added successfully!', 'success')
            return redirect(url_for('manage_schools'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding school. Please try again.', 'error')
    
    return render_template('add_school.html')

@app.route('/admin/schools/edit/<int:school_id>', methods=['GET', 'POST'])
def edit_school(school_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        school.school_name = request.form['school_name']
        school.location = request.form['location']
        school.contact_person = request.form['contact_person']
        school.contact_number = request.form['contact_number']
        
        try:
            db.session.commit()
            flash('School updated successfully!', 'success')
            return redirect(url_for('manage_schools'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating school. Please try again.', 'error')
    
    return render_template('edit_school.html', school=school)

@app.route('/admin/schools/delete/<int:school_id>', methods=['POST'])
def delete_school(school_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    school = School.query.get_or_404(school_id)
    
    try:
        # Check if school has related records
        has_deliveries = Delivery.query.filter_by(school_id=school_id).first()
        has_attendance = Attendance.query.filter_by(school_id=school_id).first()
        has_learners = Learner.query.filter_by(school_id=school_id).first()
        
        if has_deliveries or has_attendance or has_learners:
            flash('Cannot delete school. There are related records in the system.', 'error')
        else:
            db.session.delete(school)
            db.session.commit()
            flash('School deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting school. Please try again.', 'error')
    
    return redirect(url_for('manage_schools'))

# Worker Management Routes
@app.route('/admin/workers')
def manage_workers():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    workers = User.query.filter(User.role.in_(['cooker', 'delivery'])).order_by(User.full_name).all()
    return render_template('manage_workers.html', workers=workers)

@app.route('/admin/workers/add', methods=['GET', 'POST'])
def add_worker():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        phone = request.form['phone']
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A worker with this email already exists!', 'error')
            return render_template('add_worker.html')
        
        # Create new worker
        new_worker = User(
            full_name=full_name,
            email=email,
            role=role,
            phone=phone
        )
        new_worker.set_password(password)
        
        try:
            db.session.add(new_worker)
            db.session.commit()
            flash('Worker added successfully!', 'success')
            return redirect(url_for('manage_workers'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding worker. Please try again.', 'error')
    
    return render_template('add_worker.html')

@app.route('/admin/workers/edit/<int:worker_id>', methods=['GET', 'POST'])
def edit_worker(worker_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    worker = User.query.get_or_404(worker_id)
    
    # Only allow editing workers (not admins)
    if worker.role == 'admin':
        flash('Cannot edit admin users.', 'error')
        return redirect(url_for('manage_workers'))
    
    if request.method == 'POST':
        worker.full_name = request.form['full_name']
        worker.email = request.form['email']
        worker.role = request.form['role']
        worker.phone = request.form['phone']
        
        # Update password only if provided
        new_password = request.form.get('password')
        if new_password:
            worker.set_password(new_password)
        
        try:
            db.session.commit()
            flash('Worker updated successfully!', 'success')
            return redirect(url_for('manage_workers'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating worker. Please try again.', 'error')
    
    return render_template('edit_worker.html', worker=worker)

@app.route('/admin/workers/delete/<int:worker_id>', methods=['POST'])
def delete_worker(worker_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    worker = User.query.get_or_404(worker_id)
    
    # Prevent deleting admin users and users with related records
    if worker.role == 'admin':
        flash('Cannot delete admin users.', 'error')
        return redirect(url_for('manage_workers'))
    
    try:
        # Check if worker has related records
        has_deliveries = Delivery.query.filter_by(delivery_guy_id=worker_id).first()
        has_attendance = Attendance.query.filter_by(cooker_id=worker_id).first()
        has_learners = Learner.query.filter_by(cooker_id=worker_id).first()
        
        if has_deliveries or has_attendance or has_learners:
            flash('Cannot delete worker. There are related records in the system.', 'error')
        else:
            db.session.delete(worker)
            db.session.commit()
            flash('Worker deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting worker. Please try again.', 'error')
    
    return redirect(url_for('manage_workers'))

# Delivery Management Routes
@app.route('/admin/deliveries')
def manage_deliveries():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    deliveries = Delivery.query.order_by(Delivery.delivery_date.desc()).all()
    return render_template('manage_deliveries.html', deliveries=deliveries)

@app.route('/admin/deliveries/assign', methods=['GET', 'POST'])
def assign_delivery():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get available schools and delivery guys for dropdowns
    schools = School.query.order_by(School.school_name).all()
    delivery_guys = User.query.filter_by(role='delivery').order_by(User.full_name).all()
    
    if request.method == 'POST':
        school_id = request.form['school_id']
        delivery_date = request.form['delivery_date']
        location = request.form['location']
        delivery_guy_id = request.form['delivery_guy_id']
        remarks = request.form.get('remarks', '')
        
        # Create new delivery assignment
        new_delivery = Delivery(
            school_id=school_id,
            delivery_date=datetime.strptime(delivery_date, '%Y-%m-%d').date(),
            location=location,
            delivery_guy_id=delivery_guy_id,
            remarks=remarks,
            status='Pending'
        )
        
        try:
            db.session.add(new_delivery)
            db.session.commit()
            flash('Delivery assigned successfully!', 'success')
            return redirect(url_for('manage_deliveries'))
        except Exception as e:
            db.session.rollback()
            flash('Error assigning delivery. Please try again.', 'error')
    
    return render_template('assign_delivery.html', schools=schools, delivery_guys=delivery_guys)

@app.route('/admin/deliveries/edit/<int:delivery_id>', methods=['GET', 'POST'])
def edit_delivery(delivery_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    delivery = Delivery.query.get_or_404(delivery_id)
    schools = School.query.order_by(School.school_name).all()
    delivery_guys = User.query.filter_by(role='delivery').order_by(User.full_name).all()
    
    if request.method == 'POST':
        delivery.school_id = request.form['school_id']
        delivery.delivery_date = datetime.strptime(request.form['delivery_date'], '%Y-%m-%d').date()
        delivery.location = request.form['location']
        delivery.delivery_guy_id = request.form['delivery_guy_id']
        delivery.remarks = request.form.get('remarks', '')
        delivery.status = request.form['status']
        
        # If marked as delivered, set delivered time
        if delivery.status == 'Delivered' and not delivery.delivered_time:
            delivery.delivered_time = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Delivery updated successfully!', 'success')
            return redirect(url_for('manage_deliveries'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating delivery. Please try again.', 'error')
    
    return render_template('edit_delivery.html', delivery=delivery, schools=schools, delivery_guys=delivery_guys)

@app.route('/admin/deliveries/delete/<int:delivery_id>', methods=['POST'])
def delete_delivery(delivery_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    delivery = Delivery.query.get_or_404(delivery_id)
    
    try:
        db.session.delete(delivery)
        db.session.commit()
        flash('Delivery assignment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting delivery assignment. Please try again.', 'error')
    
    return redirect(url_for('manage_deliveries'))

@app.route('/admin/deliveries/mark_delivered/<int:delivery_id>', methods=['POST'])
def mark_delivery_delivered(delivery_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    delivery = Delivery.query.get_or_404(delivery_id)
    
    try:
        delivery.status = 'Delivered'
        delivery.delivered_time = datetime.utcnow()
        db.session.commit()
        flash('Delivery marked as delivered!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating delivery status. Please try again.', 'error')
    
    return redirect(url_for('manage_deliveries'))

# Attendance Management Routes
@app.route('/cooker/attendance')
def cooker_attendance():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    # Get current user's attendance records
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's attendance record
    today_attendance = Attendance.query.filter_by(
        cooker_id=user_id, 
        date=today
    ).first()
    
    # Get attendance history (last 30 days)
    attendance_history = Attendance.query.filter_by(
        cooker_id=user_id
    ).order_by(Attendance.date.desc()).limit(30).all()
    
    # Calculate monthly stats
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_attendance = Attendance.query.filter(
        Attendance.cooker_id == user_id,
        db.extract('month', Attendance.date) == current_month,
        db.extract('year', Attendance.date) == current_year
    ).all()
    
    days_worked = len(monthly_attendance)
    total_hours = sum(
        (att.time_out - att.time_in).total_seconds() / 3600 
        for att in monthly_attendance 
        if att.time_in and att.time_out
    )
    
    return render_template('cooker_attendance.html',
                         today_attendance=today_attendance,
                         attendance_history=attendance_history,
                         days_worked=days_worked,
                         total_hours=total_hours,
                         today=today)

@app.route('/cooker/attendance/clock_in', methods=['POST'])
def clock_in():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Check if already clocked in today
    existing_attendance = Attendance.query.filter_by(
        cooker_id=user_id, 
        date=today
    ).first()
    
    if existing_attendance:
        flash('You have already clocked in today!', 'error')
        return redirect(url_for('cooker_attendance'))
    
    # Get assigned school for the cooker
    # You might need to modify this based on your school assignment logic
    assigned_school = School.query.first()  # Default to first school for now
    
    new_attendance = Attendance(
        cooker_id=user_id,
        school_id=assigned_school.school_id if assigned_school else 1,
        date=today,
        time_in=datetime.now(),
        time_out=None
    )
    
    try:
        db.session.add(new_attendance)
        db.session.commit()
        flash('Successfully clocked in!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clocking in. Please try again.', 'error')
    
    return redirect(url_for('cooker_attendance'))

@app.route('/cooker/attendance/clock_out', methods=['POST'])
def clock_out():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's attendance record
    attendance = Attendance.query.filter_by(
        cooker_id=user_id, 
        date=today
    ).first()
    
    if not attendance:
        flash('You need to clock in first!', 'error')
        return redirect(url_for('cooker_attendance'))
    
    if attendance.time_out:
        flash('You have already clocked out today!', 'error')
        return redirect(url_for('cooker_attendance'))
    
    try:
        attendance.time_out = datetime.now()
        db.session.commit()
        flash('Successfully clocked out!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clocking out. Please try again.', 'error')
    
    return redirect(url_for('cooker_attendance'))

# Learner Management Routes for Cookers
@app.route('/cooker/learners/add', methods=['POST'])
def add_learner():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        learner_name = request.form['learner_name']
        grade = request.form['grade']
        meal_type = request.form['meal_type']
        
        # Get current user and their assigned school
        user_id = session.get('user_id')
        today = datetime.now().date()
        
        # Get the cooker's assigned school (you may need to modify this logic)
        assigned_school = School.query.first()  # Default to first school for now
        
        # Create new learner record
        new_learner = Learner(
            learner_name=learner_name,
            grade=grade,
            cooker_id=user_id,
            school_id=assigned_school.school_id if assigned_school else 1,
            date_served=today,
            meal_type=meal_type
        )
        
        try:
            db.session.add(new_learner)
            db.session.commit()
            flash('Learner record added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding learner record. Please try again.', 'error')
    
    return redirect(url_for('cooker_learners_records'))

# Route to view learner records
@app.route('/cooker/learners')
def cooker_learners():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's learners
    todays_learners = Learner.query.filter_by(
        cooker_id=user_id, 
        date_served=today
    ).order_by(Learner.created_at.desc()).all()
    
    return render_template('cooker_learners.html', 
                         learners=todays_learners, 
                         today=today)
@app.route('/cooker/learners/delete/<int:learner_id>', methods=['POST'])
def delete_learner(learner_id):
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    learner = Learner.query.get_or_404(learner_id)
    
    # Ensure the learner belongs to the current cooker
    if learner.cooker_id != session.get('user_id'):
        flash('You can only delete your own learner records.', 'error')
        return redirect(url_for('cooker_learners_records'))
    
    try:
        db.session.delete(learner)
        db.session.commit()
        flash('Learner record deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting learner record. Please try again.', 'error')
    
    return redirect(url_for('cooker_learners_records'))
@app.route('/cooker/learners/records', methods=['GET'])
def cooker_learners_records():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's learners and all learners for the current cooker
    todays_learners = Learner.query.filter_by(
        cooker_id=user_id, 
        date_served=today
    ).order_by(Learner.created_at.desc()).all()
    
    # Get assigned school for the cooker
    assigned_school = School.query.first()  # Modify this based on your school assignment logic
    
    return render_template('cooker_learners_records.html', 
                         todays_learners=todays_learners,
                         assigned_school=assigned_school,
                         today=today)

@app.route('/debug/users')
def debug_users():
    """Debug route to check if users are created"""
    users = User.query.all()
    result = []
    for user in users:
        result.append({
            'id': user.user_id,
            'name': user.full_name,
            'email': user.email,
            'role': user.role,
            'created': user.created_at
        })
    return {'users': result}

@app.route('/reset-db')
def reset_db():
    """Reset database and create default users (for development only)"""
    db.drop_all()
    db.create_all()
    init_db()
    return 'Database reset successfully!'

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

# Initialize database with hashed passwords
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default users if they don't exist
        default_users = [
            {
                'full_name': 'System Administrator',
                'email': 'admin@manqinenyathi.com',
                'password': 'admin123',
                'role': 'admin',
                'phone': '+1234567890'
            },
            {
                'full_name': 'Head Cooker',
                'email': 'cooker@manqinenyathi.com', 
                'password': 'cook123',
                'role': 'cooker',
                'phone': '+1234567891'
            },
            {
                'full_name': 'Delivery Coordinator',
                'email': 'delivery@manqinenyathi.com',
                'password': 'deliver123', 
                'role': 'delivery',
                'phone': '+1234567892'
            }
        ]
        
        for user_data in default_users:
            if not User.query.filter_by(email=user_data['email']).first():
                user = User(
                    full_name=user_data['full_name'],
                    email=user_data['email'],
                    role=user_data['role'],
                    phone=user_data['phone']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                print(f"Created user: {user_data['email']}")  # Debug print
        
        db.session.commit()
        print("Database initialization completed!")  # Debug print

if __name__ == "__main__":
    init_db()
    app.run(debug=True)