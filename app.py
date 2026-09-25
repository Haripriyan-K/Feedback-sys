import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'feedback.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Simple hardcoded admin credentials (override via env vars in production)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

DEPARTMENTS = [
    'Computer Science', 'Information Technology', 'Electronics',
    'Mechanical', 'Civil', 'Electrical', 'Other'
]
CATEGORIES = ['Academics', 'Infrastructure', 'Faculty', 'Administration', 'Other']


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    register_no = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending / resolved
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'register_no': self.register_no,
            'department': self.department,
            'category': self.category,
            'rating': self.rating,
            'comments': self.comments,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
        }


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ---------- Public routes ----------

@app.route('/')
def index():
    return redirect(url_for('feedback_form'))


@app.route('/feedback', methods=['GET', 'POST'])
def feedback_form():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        register_no = request.form.get('register_no', '').strip()
        department = request.form.get('department', '').strip()
        category = request.form.get('category', '').strip()
        rating = request.form.get('rating', '').strip()
        comments = request.form.get('comments', '').strip()

        errors = []
        if not name:
            errors.append('Name is required.')
        if not register_no:
            errors.append('Register No. is required.')
        if department not in DEPARTMENTS:
            errors.append('Please select a valid department.')
        if category not in CATEGORIES:
            errors.append('Please select a valid category.')
        try:
            rating_val = int(rating)
            if rating_val < 1 or rating_val > 5:
                raise ValueError()
        except (TypeError, ValueError):
            errors.append('Rating must be a number between 1 and 5.')
            rating_val = None

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('feedback_form.html', departments=DEPARTMENTS,
                                    categories=CATEGORIES, form=request.form)

        entry = Feedback(
            name=name, register_no=register_no, department=department,
            category=category, rating=rating_val, comments=comments
        )
        db.session.add(entry)
        db.session.commit()
        flash('Thank you! Your feedback has been submitted.', 'success')
        return redirect(url_for('feedback_form'))

    return render_template('feedback_form.html', departments=DEPARTMENTS, categories=CATEGORIES, form={})


# ---------- Admin routes ----------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    dept_filter = request.args.get('department', '')
    cat_filter = request.args.get('category', '')
    rating_filter = request.args.get('rating', '')
    status_filter = request.args.get('status', '')

    query = Feedback.query
    if dept_filter:
        query = query.filter_by(department=dept_filter)
    if cat_filter:
        query = query.filter_by(category=cat_filter)
    if rating_filter:
        query = query.filter_by(rating=int(rating_filter))
    if status_filter:
        query = query.filter_by(status=status_filter)

    entries = query.order_by(Feedback.created_at.desc()).all()

    all_entries = Feedback.query.all()
    total_feedback = len(all_entries)
    avg_rating = round(sum(e.rating for e in all_entries) / total_feedback, 2) if total_feedback else 0
    pending_count = Feedback.query.filter_by(status='pending').count()
    resolved_count = Feedback.query.filter_by(status='resolved').count()
    recent_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(5).all()

    return render_template(
        'admin_dashboard.html',
        entries=entries,
        departments=DEPARTMENTS,
        categories=CATEGORIES,
        total_feedback=total_feedback,
        avg_rating=avg_rating,
        pending_count=pending_count,
        resolved_count=resolved_count,
        recent_feedback=recent_feedback,
        dept_filter=dept_filter,
        cat_filter=cat_filter,
        rating_filter=rating_filter,
        status_filter=status_filter,
    )


@app.route('/admin/feedback/<int:feedback_id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(feedback_id):
    entry = Feedback.query.get_or_404(feedback_id)
    entry.status = 'resolved' if entry.status == 'pending' else 'pending'
    db.session.commit()
    flash(f'Feedback #{entry.id} marked as {entry.status}.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


# ---------- Health / monitoring ----------

@app.route('/health')
def health():
    try:
        db.session.execute(db.select(Feedback).limit(1))
        db_status = 'connected'
    except Exception as exc:
        return jsonify({'status': 'unhealthy', 'database': 'error', 'detail': str(exc)}), 500
    return jsonify({'status': 'healthy', 'database': db_status,
                     'timestamp': datetime.utcnow().isoformat() + 'Z'}), 200


def create_tables():
    with app.app_context():
        db.create_all()


create_tables()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
