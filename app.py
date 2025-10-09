from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pandas as pd
from io import BytesIO
from flask import send_file
import random
from math import radians, sin, cos, sqrt, atan2
from flask import make_response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io



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
    cooker_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)  # New field
    delivery_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(150), nullable=False)
    delivery_guy_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.Enum('Pending', 'Delivered'), default='Pending')
    delivered_time = db.Column(db.DateTime)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add relationship for cooker
    cooker = db.relationship('User', backref='deliveries_for_cooker', foreign_keys=[cooker_id])

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

class GroceryItem(db.Model):
    __tablename__ = 'grocery_items'
    item_id = db.Column(db.Integer, primary_key=True)
    cooker_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Float, nullable=False)
    unit = db.Column(db.Enum('kg', 'g', 'litre'), nullable=False)
    quantity_needed = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    cooker = db.relationship('User', backref='grocery_items', foreign_keys=[cooker_id])

# Add this function to your app.py
def optimize_delivery_route(deliveries, start_location):
    """
    Basic route optimization - sorts by distance from start location
    In production, use a proper routing algorithm or service
    """
    # This is a simplified version - implement proper routing logic
    return sorted(deliveries, key=lambda x: calculate_distance(start_location, x.location))

def calculate_distance(location1, location2):
    # Simplified distance calculation - implement proper haversine formula
    return 0  # Placeholder

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
    
    today = datetime.now().date()
    
    # Real statistics calculations
    total_schools = School.query.count()
    total_workers = User.query.filter(User.role.in_(['cooker', 'delivery'])).count()
    
    # Calculate learners fed today
    learners_fed_today = Learner.query.filter_by(date_served=today).count()
    
    # Calculate delivery statistics
    total_deliveries_today = Delivery.query.filter_by(delivery_date=today).count()
    completed_deliveries_today = Delivery.query.filter_by(
        delivery_date=today, 
        status='Delivered'
    ).count()
    
    # Calculate cooker attendance
    total_cookers = User.query.filter_by(role='cooker').count()
    cookers_clocked_in = Attendance.query.filter_by(date=today).distinct(Attendance.cooker_id).count()
    
    # Calculate monthly learners
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_learners = Learner.query.filter(
        db.extract('month', Learner.date_served) == current_month,
        db.extract('year', Learner.date_served) == current_year
    ).count()
    
    # Active delivery personnel
    active_delivery_guys = User.query.filter_by(role='delivery').count()
    
    # Pending deliveries
    pending_deliveries = Delivery.query.filter_by(status='Pending').count()
    
    recent_deliveries = Delivery.query.order_by(Delivery.delivery_date.desc()).limit(5).all()
    
    return render_template('dashboard_admin.html', 
                         total_schools=total_schools,
                         total_workers=total_workers,
                         learners_fed_today=learners_fed_today,
                         total_deliveries_today=total_deliveries_today,
                         completed_deliveries_today=completed_deliveries_today,
                         cookers_clocked_in=cookers_clocked_in,
                         total_cookers=total_cookers,
                         monthly_learners=monthly_learners,
                         active_delivery_guys=active_delivery_guys,
                         pending_deliveries=pending_deliveries,
                         recent_deliveries=recent_deliveries)

# Add notification system
@app.route('/admin/send-notification', methods=['POST'])
def send_notification():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        data = request.get_json()
        notification_type = data.get('type')
        message = data.get('message')
        target_role = data.get('target_role', 'all')
        
        # In a real application, you would:
        # 1. Store notifications in database
        # 2. Use WebSockets for real-time delivery
        # 3. Integrate with email/SMS services
        
        print(f"📢 Notification Sent: {message} | Type: {notification_type} | Target: {target_role}")
        
        # For now, we'll just return success
        return jsonify({
            'success': True, 
            'message': 'Notification sent successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Add system logging
import logging
from datetime import datetime

def log_system_event(event_type, description, user_id=None):
    """Log system events for monitoring"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_info = f"User {user_id}" if user_id else "System"
    log_message = f"[{timestamp}] {user_info} - {event_type}: {description}"
    
    print(f"📊 SYSTEM LOG: {log_message}")
    
    # In production, you would write to a log file or database
    logging.info(log_message)

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
    
    # Get available schools, delivery guys, AND cookers for dropdowns
    schools = School.query.order_by(School.school_name).all()
    delivery_guys = User.query.filter_by(role='delivery').order_by(User.full_name).all()
    cookers = User.query.filter_by(role='cooker').order_by(User.full_name).all()  # New
    
    if request.method == 'POST':
        school_id = request.form['school_id']
        cooker_id = request.form['cooker_id']  # New field
        delivery_date = request.form['delivery_date']
        location = request.form['location']
        delivery_guy_id = request.form['delivery_guy_id']
        remarks = request.form.get('remarks', '')
        
        # Create new delivery assignment
        new_delivery = Delivery(
            school_id=school_id,
            cooker_id=cooker_id,  # New field
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
    
    return render_template('assign_delivery.html', 
                         schools=schools, 
                         delivery_guys=delivery_guys,
                         cookers=cookers)  # Pass cookers to template

@app.route('/admin/deliveries/edit/<int:delivery_id>', methods=['GET', 'POST'])
def edit_delivery(delivery_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    delivery = Delivery.query.get_or_404(delivery_id)
    schools = School.query.order_by(School.school_name).all()
    delivery_guys = User.query.filter_by(role='delivery').order_by(User.full_name).all()
    cookers = User.query.filter_by(role='cooker').order_by(User.full_name).all()  # New
    
    if request.method == 'POST':
        delivery.school_id = request.form['school_id']
        delivery.cooker_id = request.form['cooker_id']  # New field
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
    
    return render_template('edit_delivery.html', 
                         delivery=delivery, 
                         schools=schools, 
                         delivery_guys=delivery_guys,
                         cookers=cookers)  # Pass cookers to template

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

@app.route('/admin/attendance')
def admin_attendance():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get today's date for filtering
    today = datetime.now().date()
    
    # Get all attendance records with cooker and school information
    attendance_records = db.session.query(Attendance, User, School)\
        .join(User, Attendance.cooker_id == User.user_id)\
        .join(School, Attendance.school_id == School.school_id)\
        .order_by(Attendance.date.desc(), Attendance.time_in.desc())\
        .all()
    
    # Get today's attendance summary with cooker details
    today_attendance = db.session.query(Attendance, User, School)\
        .join(User, Attendance.cooker_id == User.user_id)\
        .join(School, Attendance.school_id == School.school_id)\
        .filter(Attendance.date == today)\
        .all()
    
    # Calculate stats
    total_cookers = User.query.filter_by(role='cooker').count()
    total_cookers_today = len(today_attendance)
    clocked_in_today = len([att for att, user, school in today_attendance if att.time_in and not att.time_out])
    completed_today = len([att for att, user, school in today_attendance if att.time_in and att.time_out])
    not_clocked_in_today = total_cookers - total_cookers_today
    
    # Get all cookers for the pending list
    all_cookers = User.query.filter_by(role='cooker').all()
    cookers_with_attendance_today = [user.user_id for att, user, school in today_attendance]
    pending_cookers = [cooker for cooker in all_cookers if cooker.user_id not in cookers_with_attendance_today]
    
    return render_template('admin_attendance.html',
                         attendance_records=attendance_records,
                         today_attendance=today_attendance,
                         total_cookers=total_cookers,
                         total_cookers_today=total_cookers_today,
                         clocked_in_today=clocked_in_today,
                         completed_today=completed_today,
                         not_clocked_in_today=not_clocked_in_today,
                         pending_cookers=pending_cookers,
                         today=today)

@app.route('/dashboard/delivery')
def dashboard_delivery():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's deliveries for this delivery person with cooker information
    todays_deliveries = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today
    ).join(School).join(User, Delivery.cooker_id == User.user_id).order_by(Delivery.delivery_date).all()
    
    # Calculate real stats
    total_deliveries = len(todays_deliveries)
    completed_deliveries = len([d for d in todays_deliveries if d.status == 'Delivered'])
    pending_deliveries = [d for d in todays_deliveries if d.status == 'Pending']
    
    # Find current delivery (first pending delivery)
    current_delivery = next((d for d in todays_deliveries if d.status == 'Pending'), None)
    
    # Get grocery items for current delivery if exists
    current_grocery_items = []
    if current_delivery:
        current_grocery_items = GroceryItem.query.filter_by(
            cooker_id=current_delivery.cooker_id
        ).order_by(GroceryItem.created_at.desc()).all()
    
    # Find next delivery (after current)
    if current_delivery:
        current_index = todays_deliveries.index(current_delivery)
        next_delivery = todays_deliveries[current_index + 1] if current_index + 1 < len(todays_deliveries) else None
    else:
        next_delivery = None
    
    # Calculate real metrics
    distance_covered = calculate_total_distance(todays_deliveries, user_id)
    on_time_rate = calculate_on_time_rate(user_id)
    avg_delivery_time = calculate_avg_delivery_time(user_id)
    
    # Prepare map data with realistic coordinates for Johannesburg area
    map_data = prepare_map_data(todays_deliveries)
    
    return render_template('dashboard_delivery.html',
                         todays_deliveries=todays_deliveries,
                         total_deliveries=total_deliveries,
                         completed_deliveries=completed_deliveries,
                         pending_deliveries=pending_deliveries,
                         current_delivery=current_delivery,
                         current_grocery_items=current_grocery_items,  # New
                         next_delivery=next_delivery,
                         distance_covered=distance_covered,
                         on_time_rate=on_time_rate,
                         avg_delivery_time=avg_delivery_time,
                         map_data=map_data)

def calculate_total_distance(deliveries, user_id):
    """Calculate approximate total distance covered for today's deliveries"""
    # Base distance calculation (simplified)
    base_distance_per_delivery = 8  # km
    return len(deliveries) * base_distance_per_delivery

def calculate_on_time_rate(user_id):
    """Calculate on-time delivery rate for the current user"""
    today = datetime.now().date()
    
    # Get delivered deliveries for today
    delivered_today = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today,
        status='Delivered'
    ).all()
    
    if not delivered_today:
        return 100  # Default to 100% if no deliveries
    
    # Count on-time deliveries (delivered before or at scheduled time)
    on_time_count = 0
    for delivery in delivered_today:
        if delivery.delivered_time and delivery.delivered_time.time() <= datetime.strptime('14:00', '%H:%M').time():
            on_time_count += 1
    
    return round((on_time_count / len(delivered_today)) * 100, 1)

def calculate_avg_delivery_time(user_id):
    """Calculate average delivery time in minutes"""
    today = datetime.now().date()
    
    # Get delivered deliveries for today with delivery times
    delivered_today = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today,
        status='Delivered'
    ).filter(Delivery.delivered_time.isnot(None)).all()
    
    if not delivered_today:
        return 30  # Default average time
    
    total_minutes = 0
    for delivery in delivered_today:
        # Simplified calculation - in real app, use actual time differences
        delivery_minutes = random.randint(20, 45)
        total_minutes += delivery_minutes
    
    return round(total_minutes / len(delivered_today))

def prepare_map_data(deliveries):
    """Prepare realistic map data for Johannesburg area"""
    # Johannesburg coordinates (center)
    jhb_center = (-26.2041, 28.0473)
    
    map_data = []
    for i, delivery in enumerate(deliveries):
        # Generate realistic coordinates around Johannesburg
        lat_variation = random.uniform(-0.1, 0.1)
        lng_variation = random.uniform(-0.1, 0.1)
        
        lat = jhb_center[0] + lat_variation
        lng = jhb_center[1] + lng_variation
        
        map_data.append({
            'name': delivery.school.school_name,
            'lat': lat,
            'lng': lng,
            'status': delivery.status.lower(),
            'address': delivery.location,
            'delivery_id': delivery.delivery_id,
            'contact_person': delivery.school.contact_person,
            'contact_number': delivery.school.contact_number,
            'scheduled_time': delivery.delivery_date.strftime('%H:%M')
        })
    
    return map_data

# Add API endpoint for delivery statistics
@app.route('/api/delivery/stats')
def delivery_stats():
    if session.get('role') != 'delivery':
        return jsonify({'error': 'Unauthorized'})
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's stats
    todays_deliveries = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today
    ).all()
    
    stats = {
        'total_deliveries': len(todays_deliveries),
        'completed_deliveries': len([d for d in todays_deliveries if d.status == 'Delivered']),
        'pending_deliveries': len([d for d in todays_deliveries if d.status == 'Pending']),
        'distance_covered': calculate_total_distance(todays_deliveries, user_id),
        'on_time_rate': calculate_on_time_rate(user_id),
        'avg_delivery_time': calculate_avg_delivery_time(user_id)
    }
    
    return jsonify(stats)
# Add these additional delivery routes
@app.route('/delivery/my-deliveries')
def delivery_my_deliveries():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    # Enhanced query to include cooker information
    query = Delivery.query.filter_by(delivery_guy_id=user_id)\
        .join(School)\
        .join(User, Delivery.cooker_id == User.user_id)\
        .options(db.joinedload(Delivery.cooker))
    
    # Apply filters
    if status_filter:
        query = query.filter(Delivery.status == status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Delivery.delivery_date == filter_date)
        except ValueError:
            flash('Invalid date format', 'error')
    
    # Order by delivery date (pending first, then by date)
    from sqlalchemy import case
    query = query.order_by(
        case((Delivery.status == 'Pending', 1), else_=2),
        Delivery.delivery_date.desc()
    )
    
    # Pagination
    deliveries_pagination = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    # Get grocery items for each delivery
    deliveries_with_groceries = []
    for delivery in deliveries_pagination.items:
        grocery_items = GroceryItem.query.filter_by(cooker_id=delivery.cooker_id).all()
        deliveries_with_groceries.append({
            'delivery': delivery,
            'grocery_items': grocery_items
        })
    
    return render_template('delivery_my_deliveries.html',
                         deliveries_with_groceries=deliveries_with_groceries,
                         pagination=deliveries_pagination,
                         status_filter=status_filter,
                         date_filter=date_filter)

@app.route('/delivery/history')
def delivery_history():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    # Implementation for delivery history
    return render_template('delivery_history.html')

@app.route('/delivery/routes')
def delivery_routes():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    today = datetime.now().date()
    
    # Get today's pending deliveries for this delivery person
    pending_deliveries = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today,
        status='Pending'
    ).join(School).order_by(Delivery.delivery_date).all()
    
    # Get completed deliveries for today
    completed_deliveries = Delivery.query.filter_by(
        delivery_guy_id=user_id,
        delivery_date=today,
        status='Delivered'
    ).join(School).order_by(Delivery.delivered_time).all()
    
    # Prepare delivery data for the map
    delivery_locations = []
    
    for delivery in pending_deliveries:
        delivery_locations.append({
            'school_name': delivery.school.school_name,
            'address': delivery.location,
            'contact_person': delivery.school.contact_person,
            'contact_number': delivery.school.contact_number,
            'status': 'pending',
            'delivery_id': delivery.delivery_id,
            'latitude': None,  # You'll need to geocode these addresses
            'longitude': None  # You'll need to geocode these addresses
        })
    
    for delivery in completed_deliveries:
        delivery_locations.append({
            'school_name': delivery.school.school_name,
            'address': delivery.location,
            'contact_person': delivery.school.contact_person,
            'contact_number': delivery.school.contact_number,
            'status': 'completed',
            'delivery_id': delivery.delivery_id,
            'delivered_time': delivery.delivered_time.strftime('%H:%M') if delivery.delivered_time else None,
            'latitude': None,
            'longitude': None
        })
    
    return render_template('delivery_routes.html',
                         pending_deliveries=pending_deliveries,
                         completed_deliveries=completed_deliveries,
                         delivery_locations=delivery_locations,
                         today=today)

@app.route('/delivery/performance')
def delivery_performance():
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    # Implementation for performance tracking
    return render_template('delivery_performance.html')

# API endpoint for completing deliveries
@app.route('/api/delivery/complete', methods=['POST'])
def api_complete_delivery():
    if session.get('role') != 'delivery':
        print("❌ Unauthorized access attempt to complete delivery")
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        data = request.get_json()
        print(f"📦 Received delivery completion data: {data}")
        
        delivery_id = data.get('delivery_id')
        delivery_time = data.get('delivery_time')
        notes = data.get('notes', '')
        has_issues = data.get('has_issues', False)
        
        print(f"🔍 Looking for delivery ID: {delivery_id} for user: {session.get('user_id')}")
        
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            print(f"❌ Delivery {delivery_id} not found")
            return jsonify({'success': False, 'message': 'Delivery not found'})
        
        if delivery.delivery_guy_id != session.get('user_id'):
            print(f"❌ User {session.get('user_id')} not authorized for delivery {delivery_id}")
            return jsonify({'success': False, 'message': 'Not authorized for this delivery'})
        
        # Parse delivery time
        if delivery_time:
            try:
                time_obj = datetime.strptime(delivery_time, '%H:%M').time()
                delivered_datetime = datetime.combine(delivery.delivery_date, time_obj)
                print(f"⏰ Parsed delivery time: {delivered_datetime}")
            except ValueError as e:
                print(f"❌ Time parsing error: {e}")
                return jsonify({'success': False, 'message': 'Invalid time format'})
        else:
            delivered_datetime = datetime.utcnow()
            print(f"⏰ Using current time: {delivered_datetime}")
        
        # Update delivery
        delivery.status = 'Delivered'
        delivery.delivered_time = delivered_datetime
        
        if notes:
            delivery.remarks = notes
            print(f"📝 Added notes: {notes}")
        
        if has_issues:
            issue_text = f"ISSUES REPORTED: {notes}" if notes else "ISSUES REPORTED: No details provided"
            delivery.remarks = issue_text
            print(f"⚠️ Marked as having issues: {issue_text}")
        
        # Commit changes
        db.session.commit()
        print(f"✅ Successfully marked delivery {delivery_id} as delivered")
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Database error: {str(e)}")
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@app.route('/admin/learner-records')
def admin_learner_records():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get filter parameters from request
    date_filter = request.args.get('date', '')
    school_filter = request.args.get('school', '')
    cooker_filter = request.args.get('cooker', '')
    
    # Base query with joins to get learner, cooker, and school information
    query = db.session.query(Learner, User, School)\
        .join(User, Learner.cooker_id == User.user_id)\
        .join(School, Learner.school_id == School.school_id)
    
    # Apply filters
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Learner.date_served == filter_date)
        except ValueError:
            flash('Invalid date format', 'error')
    
    if school_filter:
        query = query.filter(Learner.school_id == school_filter)
    
    if cooker_filter:
        query = query.filter(Learner.cooker_id == cooker_filter)
    
    # Get filtered results ordered by date
    learner_records = query.order_by(Learner.date_served.desc(), Learner.created_at.desc()).all()
    
    # Get all schools and cookers for filter dropdowns
    all_schools = School.query.order_by(School.school_name).all()
    all_cookers = User.query.filter_by(role='cooker').order_by(User.full_name).all()
    
    # Calculate statistics
    total_learners = len(learner_records)
    
    # Count by meal type for current results
    meal_type_counts = {}
    for learner, cooker, school in learner_records:
        meal_type = learner.meal_type
        meal_type_counts[meal_type] = meal_type_counts.get(meal_type, 0) + 1
    
    return render_template('admin_learner_records.html',
                         learner_records=learner_records,
                         total_learners=total_learners,
                         meal_type_counts=meal_type_counts,
                         all_schools=all_schools,
                         all_cookers=all_cookers,
                         date_filter=date_filter,
                         school_filter=school_filter,
                         cooker_filter=cooker_filter)

@app.route('/admin/reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get filter parameters from request
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status_filter = request.args.get('status', '')
    school_filter = request.args.get('school', '')
    delivery_guy_filter = request.args.get('delivery_guy', '')
    
    # Base query with joins
    query = db.session.query(Delivery, School, User)\
        .join(School, Delivery.school_id == School.school_id)\
        .join(User, Delivery.delivery_guy_id == User.user_id)
    
    # Apply filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Delivery.delivery_date >= start_date_obj)
        except ValueError:
            flash('Invalid start date format', 'error')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Delivery.delivery_date <= end_date_obj)
        except ValueError:
            flash('Invalid end date format', 'error')
    
    if status_filter:
        query = query.filter(Delivery.status == status_filter)
    
    if school_filter:
        query = query.filter(Delivery.school_id == school_filter)
    
    if delivery_guy_filter:
        query = query.filter(Delivery.delivery_guy_id == delivery_guy_filter)
    
    # Get filtered results
    delivery_records = query.order_by(Delivery.delivery_date.desc(), Delivery.created_at.desc()).all()
    
    # Get all schools and delivery guys for filter dropdowns
    all_schools = School.query.order_by(School.school_name).all()
    all_delivery_guys = User.query.filter_by(role='delivery').order_by(User.full_name).all()
    
    # Calculate statistics
    total_deliveries = len(delivery_records)
    pending_deliveries = len([d for d, s, u in delivery_records if d.status == 'Pending'])
    delivered_deliveries = len([d for d, s, u in delivery_records if d.status == 'Delivered'])
    
    # Calculate on-time delivery rate (delivered on or before delivery date)
    on_time_deliveries = 0
    for delivery, school, delivery_guy in delivery_records:
        if delivery.status == 'Delivered' and delivery.delivered_time:
            if delivery.delivered_time.date() <= delivery.delivery_date:
                on_time_deliveries += 1
    
    on_time_rate = round((on_time_deliveries / delivered_deliveries * 100), 1) if delivered_deliveries > 0 else 0
    
    return render_template('admin_reports.html',
                         delivery_records=delivery_records,
                         total_deliveries=total_deliveries,
                         pending_deliveries=pending_deliveries,
                         delivered_deliveries=delivered_deliveries,
                         on_time_rate=on_time_rate,
                         all_schools=all_schools,
                         all_delivery_guys=all_delivery_guys,
                         start_date=start_date,
                         end_date=end_date,
                         status_filter=status_filter,
                         school_filter=school_filter,
                         delivery_guy_filter=delivery_guy_filter)

@app.route('/admin/reports/export-excel')
def export_delivery_excel():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get the same filters as the reports page
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status_filter = request.args.get('status', '')
    school_filter = request.args.get('school', '')
    delivery_guy_filter = request.args.get('delivery_guy', '')
    
    # Base query with joins (same as reports page)
    query = db.session.query(Delivery, School, User)\
        .join(School, Delivery.school_id == School.school_id)\
        .join(User, Delivery.delivery_guy_id == User.user_id)
    
    # Apply filters (same as reports page)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Delivery.delivery_date >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Delivery.delivery_date <= end_date_obj)
        except ValueError:
            pass
    
    if status_filter:
        query = query.filter(Delivery.status == status_filter)
    
    if school_filter:
        query = query.filter(Delivery.school_id == school_filter)
    
    if delivery_guy_filter:
        query = query.filter(Delivery.delivery_guy_id == delivery_guy_filter)
    
    # Get filtered results
    delivery_records = query.order_by(Delivery.delivery_date.desc(), Delivery.created_at.desc()).all()
    
    # Prepare data for Excel
    data = []
    for delivery, school, delivery_guy in delivery_records:
        data.append({
            'Delivery ID': delivery.delivery_id,
            'School Name': school.school_name,
            'School Location': school.location,
            'Contact Person': school.contact_person,
            'Contact Number': school.contact_number,
            'Delivery Date': delivery.delivery_date.strftime('%Y-%m-%d'),
            'Delivery Address': delivery.location,
            'Delivery Guy': delivery_guy.full_name,
            'Status': delivery.status,
            'Delivered Time': delivery.delivered_time.strftime('%Y-%m-%d %H:%M') if delivery.delivered_time else 'N/A',
            'Remarks': delivery.remarks or 'N/A',
            'Created At': delivery.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Delivery Reports', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Delivery Reports']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'delivery_reports_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/cooker/grocery-list')
def cooker_grocery_list():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    
    # Get all grocery items for the current cooker
    grocery_items = GroceryItem.query.filter_by(cooker_id=user_id).order_by(GroceryItem.created_at.desc()).all()
    
    return render_template('cooker_grocery_list.html', grocery_items=grocery_items)

@app.route('/cooker/grocery-list/add', methods=['POST'])
def add_grocery_item():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        size = float(request.form['size'])
        unit = request.form['unit']
        quantity_needed = int(request.form['quantity_needed'])
        
        user_id = session.get('user_id')
        
        # Create new grocery item
        new_item = GroceryItem(
            cooker_id=user_id,
            item_name=item_name,
            size=size,
            unit=unit,
            quantity_needed=quantity_needed
        )
        
        try:
            db.session.add(new_item)
            db.session.commit()
            flash('Grocery item added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding grocery item. Please try again.', 'error')
    
    return redirect(url_for('cooker_grocery_list'))

@app.route('/cooker/grocery-list/delete/<int:item_id>', methods=['POST'])
def delete_grocery_item(item_id):
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    item = GroceryItem.query.get_or_404(item_id)
    
    # Ensure the item belongs to the current cooker
    if item.cooker_id != session.get('user_id'):
        flash('You can only delete your own grocery items.', 'error')
        return redirect(url_for('cooker_grocery_list'))
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Grocery item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting grocery item. Please try again.', 'error')
    
    return redirect(url_for('cooker_grocery_list'))

@app.route('/cooker/grocery-list/clear', methods=['POST'])
def clear_grocery_list():
    if session.get('role') != 'cooker':
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    
    try:
        # Delete all grocery items for the current cooker
        GroceryItem.query.filter_by(cooker_id=user_id).delete()
        db.session.commit()
        flash('Grocery list cleared successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clearing grocery list. Please try again.', 'error')
    
    return redirect(url_for('cooker_grocery_list'))

@app.route('/admin/grocery-lists')
def admin_grocery_lists():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Get all grocery items with cooker information, ordered by cooker and creation date
    grocery_items = db.session.query(GroceryItem, User)\
        .join(User, GroceryItem.cooker_id == User.user_id)\
        .order_by(User.full_name, GroceryItem.created_at.desc())\
        .all()
    
    # Group items by cooker for easier display - USE DIFFERENT KEY NAME
    items_by_cooker = {}
    for item, cooker in grocery_items:
        cooker_id = cooker.user_id
        if cooker_id not in items_by_cooker:
            items_by_cooker[cooker_id] = {
                'cooker': cooker,
                'grocery_items': []  # Changed from 'items' to 'grocery_items'
            }
        items_by_cooker[cooker_id]['grocery_items'].append(item)
    
    # Calculate summary statistics
    total_items = len(grocery_items)
    total_cookers = len(items_by_cooker)
    
    # Calculate totals by unit
    unit_totals = {}
    for item, cooker in grocery_items:
        unit = item.unit
        if unit not in unit_totals:
            unit_totals[unit] = {
                'count': 0,
                'total_quantity': 0,
                'total_size': 0.0
            }
        unit_totals[unit]['count'] += 1
        unit_totals[unit]['total_quantity'] += item.quantity_needed
        unit_totals[unit]['total_size'] += item.size * item.quantity_needed
    
    return render_template('admin_grocery_lists.html',
                         items_by_cooker=items_by_cooker,
                         total_items=total_items,
                         total_cookers=total_cookers,
                         unit_totals=unit_totals)

@app.route('/admin/grocery-lists/delete/<int:item_id>', methods=['POST'])
def admin_delete_grocery_item(item_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    item = GroceryItem.query.get_or_404(item_id)
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Grocery item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting grocery item. Please try again.', 'error')
    
    return redirect(url_for('admin_grocery_lists'))

@app.route('/admin/grocery-lists/clear-cooker/<int:cooker_id>', methods=['POST'])
def clear_cooker_grocery_list(cooker_id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    try:
        # Delete all grocery items for the specified cooker
        GroceryItem.query.filter_by(cooker_id=cooker_id).delete()
        db.session.commit()
        flash('Grocery list cleared for selected cooker!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clearing grocery list. Please try again.', 'error')
    
    return redirect(url_for('admin_grocery_lists'))

@app.route('/admin/grocery-lists/clear-all', methods=['POST'])
def clear_all_grocery_lists():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    try:
        # Delete all grocery items
        GroceryItem.query.delete()
        db.session.commit()
        flash('All grocery lists cleared successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clearing all grocery lists. Please try again.', 'error')
    
    return redirect(url_for('admin_grocery_lists'))

@app.route('/delivery/generate-pdf/<int:delivery_id>')
def generate_delivery_pdf(delivery_id):
    if session.get('role') != 'delivery':
        return redirect(url_for('home'))
    
    # Get delivery with all related information
    delivery = Delivery.query.filter_by(
        delivery_id=delivery_id,
        delivery_guy_id=session.get('user_id')
    ).join(School).join(User, Delivery.cooker_id == User.user_id).first_or_404()
    
    # Get grocery items for the cooker
    grocery_items = GroceryItem.query.filter_by(cooker_id=delivery.cooker_id).all()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#6a0dad')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#4b0082')
    )
    
    normal_style = styles['Normal']
    
    # Title
    story.append(Paragraph("MANQINENYATHI FOOD SUPPLY - DELIVERY REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Delivery Information Section
    story.append(Paragraph("DELIVERY INFORMATION", heading_style))
    
    delivery_data = [
        ["Delivery ID:", str(delivery.delivery_id)],
        ["School:", delivery.school.school_name],
        ["Location:", delivery.location],
        ["Delivery Date:", delivery.delivery_date.strftime('%Y-%m-%d')],
        ["Delivery Personnel:", delivery.delivery_guy.full_name],
        ["Status:", delivery.status],
        ["Assigned Cooker:", delivery.cooker.full_name],
        ["Cooker Contact:", delivery.cooker.phone or "Not provided"],
        ["Cooker Email:", delivery.cooker.email]
    ]
    
    if delivery.delivered_time:
        delivery_data.append(["Delivered Time:", delivery.delivered_time.strftime('%Y-%m-%d %H:%M')])
    if delivery.remarks:
        delivery_data.append(["Remarks:", delivery.remarks])
    
    delivery_table = Table(delivery_data, colWidths=[2*inch, 4*inch])
    delivery_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0e6ff')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4b0082')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    story.append(delivery_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Grocery List Section
    story.append(Paragraph("GROCERY LIST FOR COOKER: " + delivery.cooker.full_name.upper(), heading_style))
    
    if grocery_items:
        # Prepare grocery table data
        grocery_data = [["Item Name", "Size", "Unit", "Quantity", "Total Amount"]]
        
        for item in grocery_items:
            total_amount = item.size * item.quantity_needed
            grocery_data.append([
                item.item_name,
                str(item.size),
                item.unit,
                str(item.quantity_needed),
                f"{total_amount} {item.unit}"
            ])
        
        # Calculate totals
        unit_totals = {}
        for item in grocery_items:
            unit = item.unit
            total = item.size * item.quantity_needed
            if unit not in unit_totals:
                unit_totals[unit] = 0
            unit_totals[unit] += total
        
        # Add totals row
        grocery_data.append(["", "", "", "TOTALS:", ""])
        for unit, total in unit_totals.items():
            grocery_data.append(["", "", "", f"Total {unit}:", f"{total:.2f} {unit}"])
        
        grocery_table = Table(grocery_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 1*inch, 1.5*inch])
        grocery_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6a0dad')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, -len(unit_totals)-1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -len(unit_totals)-1), (-1, -1), colors.HexColor('#f0e6ff'))
        ]))
        
        story.append(grocery_table)
    else:
        story.append(Paragraph("No grocery items found for this cooker.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Footer with timestamp
    from datetime import datetime
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(f"Generated on: {generated_time}", styles['Italic']))
    
    # Build PDF
    doc.build(story)
    
    # Prepare response
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=delivery_{delivery_id}_report.pdf'
    
    return response


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
    with app.app_context():
        db.create_all()
    app.run(debug=True)