from datetime import datetime
from db_backend import db
from flask_login import UserMixin


# User Model
class User(UserMixin,db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    preferences = db.Column(db.String(100), nullable=False)  # e.g., Natural, Social, Formal
    role = db.Column(db.String(50), nullable=False, default='researcher')  # admin, researcher, reviewer
    papers = db.relationship('Paper', backref='author', lazy=True)
    reviews = db.relationship('Review', backref='reviewer', lazy=True)
    approved_papers = db.Column(db.Integer, default=0)
    assigned_papers = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    @property
    def is_active(self):
        return self.active

    def __repr__(self):
        return f'<User {self.email}>'

# Paper Model
class Paper(db.Model):
    __tablename__ = 'paper'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(100), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    publish_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(100), default="needs reviewer")  
    pdf_filename = db.Column(db.String(255), nullable=True)  # Optional
    reviewers = db.relationship('User', backref='paper', lazy=True)
    old_version_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=True)  # Link to the old version
    description = db.Column(db.String(500), nullable=False)  # New column for short description

    # Relationship to track old version
    old_version = db.relationship('Paper', remote_side=[id], backref='resubmitted_paper')

    def __repr__(self):
        return f'<Paper {self.title}>'

# Review Model
class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    review_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(100), default="pending")  # e.g., pending, received
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    review_date = db.Column(db.Date, default=datetime.utcnow)
    is_admin_review = db.Column(db.Boolean, default=False)  # New column to indicate admin review
    def __repr__(self):
        return f'<Review {self.id}>'

# ReviewerAssignment Model
class ReviewerAssignment(db.Model):
    __tablename__ = 'reviewer_assignments'
    assignment_id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String, default="not assigned") #not assigned

    def __repr__(self):
        return f'<ReviewerAssignment {self.assignment_id}>'
    
# StatusHistory Model
class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    history_id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    status = db.Column(db.String, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    change_date = db.Column(db.Date, default=datetime.utcnow)

    def __repr__(self):
        return f'<StatusHistory {self.history_id}>'

# Draft Model
class Draft(db.Model):
    __tablename__ = 'draft'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(100), nullable=False)
    draft_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Draft {self.title}>'

# Notification Model
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(100), default="unread")  # unread or read
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')