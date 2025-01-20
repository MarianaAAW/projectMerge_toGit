import datetime
import os
from flask import  abort, render_template, request, redirect, url_for, flash, session, jsonify
from db_backend import app,db
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from db_backend.models import  Draft, Notification, User, Paper, Review # I
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user



def allowed_file(filename):
    """Check if the uploaded file is a PDF."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET'])
@app.route('/research_page', methods=['GET'])
def research_page():
    search_query = request.args.get('search')
    author_query = request.args.get('author')
    theme_query = request.args.get('theme')
    article_name = request.args.get('article_name')
    sort_by_date = request.args.get('sort_by_date', 'latest')

    # Query papers based on search/filter criteria
    query = Paper.query.filter(Paper.status == 'published')  # Only show published papers

    # Apply search filters
    if article_name:
        query = query.filter(Paper.title.contains(article_name))

    if search_query:
        query = query.filter(Paper.title.contains(search_query) | Paper.content.contains(search_query))

    if author_query:
        query = query.filter(Paper.author.first_name.like(f'%{author_query}%') | Paper.author.last_name.like(f'%{author_query}%'))

    if theme_query:
        query = query.filter(Paper.theme.contains(theme_query))

    if sort_by_date == 'latest':
        query = query.order_by(Paper.publish_date.desc())
    elif sort_by_date == 'oldest':
        query = query.order_by(Paper.publish_date.asc())

    papers = query.all()

    return render_template('research_page.html', papers=papers)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        preferences = request.form.getlist('preferences')  # Get selected preferences as a list
        
        # Check preferences length, must be at least one
        if len(preferences) < 1:
            flash('Please select at least one preference.', 'danger')
            return render_template('register.html')
        
        # Validate password length
        if len(password) < 4 or len(password) > 10:
            flash('Password must be between 4 and 10 characters.', 'danger')
            return render_template('register.html')

        # Check if the email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('This email is already registered. Please login or use a different email.', 'danger')
            return render_template('register.html')

        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # If email is admin, set as admin user
        if email == 'admin@gmail.com':
            role = 'admin'
            new_user = User(
                email=email, 
                password=hashed_password, 
                first_name='admin', 
                last_name='editor', 
                preferences=', '.join(preferences),  # Convert list to comma-separated string
                role=role
            )
        else:
            role = 'researcher'  # Default role for others
            new_user = User(
                email=email, 
                password=hashed_password, 
                first_name=first_name, 
                last_name=last_name, 
                preferences=', '.join(preferences),  # Convert list to comma-separated string
                role=role
            )

        # Add user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User registered successfully!', 'success')
            return redirect(url_for('login'))  # Redirect to login page after successful registration
        except Exception as e:
            db.session.rollback()  # Rollback in case of any error
            flash(f'Error: {str(e)}', 'danger')

    return render_template('register.html')

'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
           # session['user_id'] = user.id
           # session['role'] = user.role
           # added
           login_user(user)
           return redirect(url_for('my_home'))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for('login'))
    
    return render_template('login.html')
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            # Redirect to the next page or a default page
            next_page = request.args.get('next')
            return redirect(next_page or url_for('my_home'))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Clear specific session keys or clear the entire session
    session.pop('user_id', None)
    session.pop('role', None)
    
    # Flash a logout success message
    flash('Logged out successfully!', 'success')
    
    # Redirect to the login page
    return redirect(url_for('login'))

@app.route('/my_home', methods=['GET'])
def my_home():
    search_query = request.args.get('search')
    author_query = request.args.get('author')
    theme_query = request.args.get('theme')
    sort_by_date = request.args.get('sort_by_date', 'latest')
    article_name = request.args.get('article_name')


    query = Paper.query.filter(Paper.status == 'published')  # Only show published papers
    
    if article_name:
        query = query.filter(Paper.title.contains(article_name))

    if search_query:
        query = query.filter(Paper.title.contains(search_query) | Paper.content.contains(search_query))

    if author_query:
        query = query.filter(Paper.author.first_name.like(f'%{author_query}%') | Paper.author.last_name.like(f'%{author_query}%'))

    if theme_query:
        query = query.filter(Paper.theme.contains(theme_query))

    if sort_by_date == 'latest':
        query = query.order_by(Paper.publish_date.desc())
    elif sort_by_date == 'oldest':
        query = query.order_by(Paper.publish_date.asc())

    papers = query.all()

    return render_template('my_home.html', papers=papers)

@app.route('/my_profile')
def my_profile():
    # Check if the user is logged in
    if not current_user.is_authenticated:
        flash("Please log in to access your profile.")
        return redirect(url_for('login', next=request.path))

    # Fetch the user from the database
    user = User.query.get(current_user.id)
    
    if not user:
        flash("User not found!")
        return redirect(url_for('login'))

    # Render the My Profile page with role-based visibility
    return render_template('my_profile.html', user=user)

@app.route('/researchers_dashboard', methods=['GET'])
def researchers_dashboard():
    # Get filter values from the request
    author_name = request.args.get('author_name', '')
    article_name = request.args.get('article_name', '')
    search = request.args.get('search', '')
    theme = request.args.get('theme', '')
    status = request.args.get('status', '')
    sort_by_date = request.args.get('sort_by_date', 'latest')

    # Assuming you have a way to get the logged-in user's ID (e.g., from the session)
    researcher_id = session.get('user_id')  # Replace with your actual session logic

    # Create the query for filtering papers
    query = Paper.query.join(Paper.author)  # Assuming Paper model has a relationship with the Author model

    # Filter papers by the logged-in researcher
    query = query.filter(Paper.author_id == researcher_id)

    # Filter by author name
    if author_name:
        query = query.filter(Paper.author.first_name.ilike(f'%{author_name}%') | Paper.author.last_name.ilike(f'%{author_name}%'))

    # Filter by article name (title)
    if article_name:
        query = query.filter(Paper.title.ilike(f'%{article_name}%'))

    # Filter by theme
    if theme:
        query = query.filter(Paper.theme == theme)

    # Filter by status
    if status:
        query = query.filter(Paper.status == status)

    # Search papers by title, description, or author
    if search:
        query = query.filter(
            Paper.title.ilike(f'%{search}%') |
            Paper.description.ilike(f'%{search}%') |
            (Paper.author.first_name.ilike(f'%{search}%')) |
            (Paper.author.last_name.ilike(f'%{search}%'))
        )

    # Sort by date (latest or oldest)
    if sort_by_date == 'latest':
        query = query.order_by(Paper.submission_date.desc())
    else:
        query = query.order_by(Paper.submission_date.asc())

    # Fetch the papers
    papers = query.all()

    return render_template('researchers_dashboard.html', papers=papers)

@app.route('/admins_dashboard', methods=['GET'])
def admins_dashboard():
    # Get filters for papers from the request arguments
    author_name = request.args.get('author_name')
    article_name = request.args.get('article_name')
    theme = request.args.get('theme')
    status = request.args.get('status')
    search_query = request.args.get('search')
    sort_by_date = request.args.get('sort_by_date', 'latest')

    # Get filters for users from the request arguments
    user_name = request.args.get('name')
    approved_papers = request.args.get('approved_papers')
    assigned_papers = request.args.get('assigned_papers')
    preferences = request.args.getlist('preferences')

    # Build the query for fetching papers
    paper_query = Paper.query
    if author_name:
        paper_query = paper_query.filter(Paper.author.contains(author_name))
    if article_name:
        paper_query = paper_query.filter(Paper.title.contains(article_name))
    if search_query:
        paper_query = paper_query.filter(Paper.title.contains(search_query) | Paper.content.contains(search_query))
    if theme:
        paper_query = paper_query.filter(Paper.theme == theme)
    if sort_by_date == 'latest':
        paper_query = paper_query.order_by(Paper.submission_date.desc())
    elif sort_by_date == 'oldest':
        paper_query = paper_query.order_by(Paper.submission_date.asc())
    if status:
        paper_query = paper_query.filter(Paper.status == status)
    papers = paper_query.all()

    # Build the query for fetching users
    user_query = User.query
    if user_name:
        user_query = user_query.filter(User.first_name.contains(user_name) | User.last_name.contains(user_name))
    if approved_papers:
        if approved_papers == 'most':
            user_query = user_query.order_by(User.approved_papers.desc())
        elif approved_papers == 'least':
            user_query = user_query.order_by(User.approved_papers.asc())
    if assigned_papers:
        if assigned_papers == 'most':
            user_query = user_query.order_by(User.assigned_papers.desc())
        elif assigned_papers == 'least':
            user_query = user_query.order_by(User.assigned_papers.asc())
    if preferences:
        user_query = user_query.filter(User.preferences.any(preferences.in_(preferences)))

    users = user_query.all()

    return render_template(
        'admins_dashboard.html',
        papers=papers,
        users=users
    )

#make a reviewer


@app.route('/admins_view_user_details', methods=['GET'])
def admins_view_user_details():
    try:
        # Query all users
        users = session.query(User).all()
        
        # Convert user data to a list of dictionaries
        user_data = [
            {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "preferences": user.preferences
            }
            for user in users
        ]
        
        # Return data as JSON or render it in a template
        return jsonify(user_data)  # For API response
        # return render_template('admins_view_user_details.html', users=user_data)  # For HTML response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_paper_by_id(paper_id):
    # Fetch paper from database by its ID
    return Paper.query.get(paper_id)

def get_reviewers_for_paper(paper_id):
    # Assuming Paper has a relationship with User for reviewers
    paper = Paper.query.get(paper_id)
    if paper:
        return User.query.filter(User.id.in_(paper.reviewers)).all()  # Modify based on your relationship setup
    return []  # Return empty list if no reviewers found

@app.route('/admins_view_paper_details/<paper_id>')
def admins_view_paper_details(paper_id):
    paper = get_paper_by_id(paper_id)
    if not paper:
        return "Paper not found", 404  # Return a 404 if the paper is not found
    
    reviewers = get_reviewers_for_paper(paper_id)
    return render_template('admins_view_paper_details.html', paper=paper, reviewers=reviewers)

@app.route('/admins_review/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def admins_review(paper_id):
    if current_user.role != 'admin':
        flash("You do not have permission to access this page.")
        return redirect(url_for('my_home'))  # Redirect to home if the user isn't an admin

    paper = Paper.query.get_or_404(paper_id)
    reviews = Review.query.filter_by(paper_id=paper_id).all()

    # Check if the admin already provided a review
    admin_review = Review.query.filter_by(paper_id=paper_id, reviewer_id=current_user.id, is_admin_review=True).first()

    if request.method == 'POST':
        # If there's an existing review, update it
        if admin_review:
            admin_review.review_text = request.form['review_text']
        else:
            # Otherwise, create a new admin review
            new_review = Review(
                review_text=request.form['review_text'],
                status='received',
                reviewer_id=current_user.id,
                paper_id=paper_id,
                is_admin_review=True
            )
            db.session.add(new_review)
        
        db.session.commit()
        flash("Review submitted successfully.")
        return redirect(url_for('admin_final_review', paper_id=paper_id))  # Redirect to final review page

    return render_template('admins_review.html', paper=paper, reviews=reviews, admin_review=admin_review)

# Route for Admin's Final Review Page (admins_final_review.html)
@app.route('/admins_final_review/<int:paper_id>')
@login_required
def admins_final_review(paper_id):
    if current_user.role != 'admin':
        flash("You do not have permission to access this page.")
        return redirect(url_for('my_home'))  # Redirect to home if the user isn't an admin

    paper = Paper.query.get_or_404(paper_id)
    reviews = Review.query.filter_by(paper_id=paper_id).all()

    # Get the admin's final review
    admin_review = Review.query.filter_by(paper_id=paper_id, reviewer_id=current_user.id, is_admin_review=True).first()

    if not admin_review:
        flash("You must provide a review before viewing the final review.")
        return redirect(url_for('admins_final_review', paper_id=paper_id))  # Redirect to the editable review page

    return render_template('admins_final_review.html', paper=paper, reviews=reviews, admin_review=admin_review)

@app.route('/submit_paper', methods=['GET', 'POST']) 
@login_required
def submit_paper():
    print(current_user)
    print(current_user.is_authenticated)
    if request.method == 'POST':
        # Extract form fields
        title = request.form.get('title')
        theme = request.form.get('theme')
        description = request.form.get('description')
        content = request.form.get('content')  # Content from CKEditor

        # Validate mandatory fields
        if not title or not theme or not content.strip():
            flash('Title, theme, and content are required.', 'error')
            return redirect(url_for('submit_paper'))

        # Handle optional file upload
        file = request.files.get('pdf')
        if file and not allowed_file(file.filename):
            flash('Invalid file format. Please upload a PDF.', 'error')
            return redirect(url_for('submit_paper'))

        # Save the file if provided
        filename = None
        if file:
            filename = f"{title.replace(' ', '_')}.pdf"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(file_path)
            except OSError as e:
                flash(f"Error saving file: {e}", 'error')
                return redirect(url_for('submit_paper'))

        # Status is always "needs reviewer"
        status = "needs reviewer"

        # Create new Paper object
        new_paper = Paper(
            title=title,
            theme=theme,
            description=description,
            content=content,
            author_id=current_user.id,
            status=status,
            pdf_filename=filename  # Store the filename if a PDF is uploaded
        )

        # Add to database
        try:
            db.session.add(new_paper)
            db.session.commit()
            flash('Paper submitted successfully!', 'success')
            return redirect(url_for('my_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving paper: {e}", 'error')
            return redirect(url_for('submit_paper'))

    # If GET request, render the form
    return render_template('submit_paper.html')

@app.route('/resubmit_paper/<int:paper_id>', methods=['POST'])
@login_required
def resubmit_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    if paper.status != "needs amendments":
        flash("This paper cannot be resubmitted.", "error")
        return redirect(url_for('my_profile'))

    new_version = Paper(
        title=paper.title,
        theme=paper.theme,
        content=paper.content,
        author_id=current_user.id,
        status="needs reviewer",
        old_version_id=paper.id,
        pdf_filename=paper.pdf_filename
    )
    try:
        paper.status = "archived"  # Mark old paper as archived
        db.session.add(new_version)
        db.session.commit()
        flash("Paper resubmitted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resubmitting paper: {e}", "error")

    return redirect(url_for('my_profile'))

'''
# Optionally, create a notification for the author
    notification = Notification(user_id=paper.author_id, message="Your paper has been resubmitted as an old version.")
    db.session.add(notification)
    db.session.commit()

    return "Paper resubmitted successfully."


    # Create a notification for the author
    notification = Notification(user_id=paper.author_id, message="Your paper has been resubmitted and marked as an old version.")
    db.session.add(notification)
    db.session.commit()
'''

@app.route('/notifications')
def notifications():
    user = User.query.get(current_user.id)  # Assuming you're using Flask-Login for user session
    unread_notifications = Notification.query.filter_by(user_id=user.id, status="unread").all()
    
    # Optionally, mark notifications as read when viewed
    for notification in unread_notifications:
        notification.status = "read"
    db.session.commit()

    return render_template('notifications.html', notifications=unread_notifications)
'''
@app.route('/drafts')
def drafts():
    drafts = Paper.query.filter_by(author_id=current_user.id, status="draft").all()
    return render_template('drafts.html', drafts=drafts)

@app.route('/submit-draft/<int:draft_id>', methods=['POST'])
def submit_draft(draft_id):
    draft = Draft.query.get(draft_id)
    if not draft:
        return jsonify({"error": "Draft not found."}), 404

    # Convert draft to paper
    paper = Paper(
        title=draft.title,
        content=draft.content,
        author_id=draft.author_id,
        theme=draft.theme,
        submission_date=datetime.utcnow(),
        status="draft"
    )
    db.session.add(paper)
    db.session.delete(draft)  # Remove the draft after submission
    db.session.commit()
    return jsonify({"message": "Draft submitted successfully.", "paper_id": paper.id}), 200


@app.route('/edit_draft/<int:paper_id>', methods=['GET', 'POST'])
def edit_draft(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    if paper.author_id != current_user.id or paper.status != "draft":
        flash('Unauthorized access!', 'error')
        return redirect(url_for('drafts'))

    if request.method == 'POST':
        paper.title = request.form.get('title')
        paper.theme = request.form.get('theme')
        paper.content = request.form.get('content')
        action = request.form.get('action')

        paper.status = "needs reviewer" if action == "submit" else "draft"
        try:
            db.session.commit()
            if paper.status == "draft":
                flash('Draft updated successfully!', 'success')
            else:
                flash('Paper submitted successfully!', 'success')
            return redirect(url_for('my_profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')

    return render_template('submit_paper.html', paper=paper)

@app.route('/delete_draft/<int:paper_id>', methods=['POST'])
def delete_draft(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    if paper.author_id != current_user.id or paper.status != "draft":
        flash('Unauthorized access!', 'error')
        return redirect(url_for('drafts'))

    try:
        db.session.delete(paper)
        db.session.commit()
        flash('Draft deleted successfully!', 'success')
        return redirect(url_for('view_drafts'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')
def assign_reviewer(paper_id, reviewer_id):
    # Create a notification for the reviewer
    notification = Notification(user_id=reviewer_id, message=f"You have been assigned to review the paper {paper_id}.")
    db.session.add(notification)
    db.session.commit()

def update_paper_status(paper_id, new_status):
    paper = Paper.query.get(paper_id)
    paper.status = new_status
    db.session.commit()

    # Create a notification for the author
    notification = Notification(user_id=paper.author_id, message=f"Your paper status has been updated to {new_status}.")
    db.session.add(notification)
    db.session.commit()

@app.route('/notifications/<int:user_id>', methods=['GET'])
def get_notifications(user_id):
    notifications = Notification.query.filter_by(user_id=user_id, status="unread").all()
    return jsonify([{
        "id": n.id,
        "message": n.message,
        "timestamp": n.timestamp
    } for n in notifications])

@app.route('/notifications/mark-as-read/<int:notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification:
        notification.status = "read"
        db.session.commit()
        return jsonify({"message": "Notification marked as read."}), 200
    return jsonify({"error": "Notification not found."}), 404
'''