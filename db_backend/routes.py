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
@login_required
def researchers_dashboard():
    # Get filter values from the request
    author_name = request.args.get('author_name', '')
    article_name = request.args.get('article_name', '')
    search = request.args.get('search', '')
    theme = request.args.get('theme', '')
    status = request.args.get('status', '')
    sort_by_date = request.args.get('sort_by_date', 'latest')

    # Assuming you have a way to get the logged-in user's ID (e.g., from the session)
    user_id = current_user.id

    # Build the query
    paper_query = Paper.query.filter_by(author_id=user_id)

    if author_name:
        print(f"Filtering by author name: {author_name}")
        paper_query = paper_query.join(User).filter(
            (User.first_name.like(f'%{author_name}%')) | 
            (User.last_name.like(f'%{author_name}%'))
        )
    if article_name:
        print(f"Filtering by article name: {article_name}")
        paper_query = paper_query.filter(Paper.title.like(f'%{article_name}%'))
    if search:
        print(f"Filtering by search: {search}")
        paper_query = paper_query.filter(Paper.description.like(f'%{search}%'))
    if theme:
        print(f"Filtering by theme: {theme}")
        paper_query = paper_query.filter(Paper.theme.like(f'%{theme}%'))
    if status:
        print(f"Filtering by status: {status}")
        paper_query = paper_query.filter(Paper.status == status)
    if sort_by_date == 'latest':
        print("Sorting by latest date")
        paper_query = paper_query.order_by(Paper.submission_date.desc())
    else:
        print("Sorting by earliest date")
        paper_query = paper_query.order_by(Paper.submission_date.asc())

    papers = paper_query.all()
    print(f"Fetched papers: {papers}")

    return render_template('researchers_dashboard.html', papers=papers)

@app.route('/researchers_view_paper/<int:paper_id>', methods=['GET'])
@login_required
def researchers_view_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    return render_template('researchers_view_paper.html', paper=paper)

@app.route('/researchers_check_reviews', methods=['GET'])
@login_required
def researchers_check_reviews():
    # Ensure the user has the role 'researcher' or both 'researcher' and 'reviewer'
    if current_user.role != 'researcher' and current_user.role != 'researcher & reviewer':
        flash("Access denied. Only researchers or users with both 'researcher' and 'reviewer' roles can view this page.", "danger")
        return redirect(url_for('my_home'))
    
    # Fetch all reviews for the current user's submitted papers
    reviews = (
        db.session.query(Review)
        .join(Paper, Review.paper_id == Paper.id)
        .filter(
            Paper.author_id == current_user.id,  # Only the researcher's papers
            Review.is_admin_review == True      # Only admin reviews
        )
        .all()
    )

    # Render the template with the reviews
    return render_template('researchers_check_reviews.html', reviews=reviews)

@app.route('/admins_dashboard', methods=['GET'])
def admins_dashboard():
    # Get filters for papers from the request arguments
    theme = request.args.get('theme')
    # Build the query for fetching papers
    paper_query = Paper.query
    user_query = User.query
    users = user_query.all()
    
    if theme:
        if theme == "Natural Science":
            first_1 = Paper.query.filter(Paper.theme == "Natural Science").all()
            return render_template('admins_dashboard.html', papers=first_1, users=users)
        elif theme == "Social Science":
            second_2 = Paper.query.filter(Paper.theme == "Social Science").all()
            return render_template('admins_dashboard.html', papers=second_2, users=users)
        else:
            third_3 = Paper.query.filter(Paper.theme == "Formal Science").all()
            return render_template('admins_dashboard.html', papers=third_3, users=users)
    papers = paper_query.all()
    return render_template('admins_dashboard.html', papers=papers, users=users)


@app.route('/admins_view_user_details', methods=['GET'])
def admins_view_user_details():
    try:
        # Query all users
        users = User.query.all()  # Proper SQLAlchemy query using the User model
        
        # Convert user data to a list of dictionaries
        user_data = [
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "preferences": user.preferences,
                "role": user.role,
                "approved_papers": user.approved_papers,
                "assigned_papers": user.assigned_papers
            }
            for user in users
        ]
        
        # Render the template and pass the user data
        return render_template('admins_view_user_details.html', users=user_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admins_view_paper_detail/<int:paper_id>', methods=['GET'])
def admins_view_paper_detail(paper_id):
    # Fetch the paper details from the database using the paper_id
    paper = Paper.query.filter_by(id=paper_id).first()
    print("paper : ",paper,"-------------------------------------------------------",type(paper))
    print("paper : ",paper.id,"-------------------------------------------------------",type(paper))


    # If the paper doesn't exist, return a 404 error
    if not paper:   
        abort(404)

    # Fetch the reviewers (if any) associated with the paper
    #print("Type : ",type(db.session.query(User).filter_by(paper.reviewer_id).all()),"-------------------")
    reviewer = User.query.all()

    #reviewer = db.session.query(User).filter(User.id.in_(paper.reviewer_id)).all()
    #print("reviewers : ",reviewer,"---------------------------------------")

    # Return the paper details to the template
    return render_template('admins_view_paper_detail.html', paper=paper, reviewers=reviewer)

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

'''
@app.route('/assign_reviewer', methods=['GET'])
def assign_reviewer():
    # Fetch all users except the admin
    users = User.query.filter(User.role != 'admin').all()
    return render_template('assign_reviewer.html', users=users)

@app.route('/make_reviewer', methods=['POST'])
def make_reviewer():
    user_id = request.form.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.role = 'researcher & reviewer'
            db.session.commit()
            flash(f"{user.first_name} {user.last_name} is now a reviewer.", "success")
        else:
            flash("User not found.", "error")
    else:
        flash("Invalid user ID.", "error")
    return redirect(url_for('assign_reviewer'))
'''
@app.route('/assign_reviewer', methods=['GET'])
def assign_reviewer():
    # Fetch all users except the admin
    users = User.query.filter(User.role != 'admin').all()
    return render_template('assign_reviewer.html', users=users)

@app.route('/make_reviewer', methods=['POST'])
def make_reviewer():
    user_id = request.form.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            # Update the role based on the current role
            if user.role == 'researcher':
                user.role = 'researcher & reviewer'
            else:
                user.role = 'reviewer'
            db.session.commit()
            flash(f"{user.first_name} {user.last_name} is now assigned as a reviewer.", "success")
        else:
            flash("User not found.", "error")
    else:
        flash("Invalid user ID.", "error")
    return redirect(url_for('assign_reviewer'))

@app.route('/reviewers_dashboard', methods=['GET'])
def reviewers_dashboard():
    # Add logic for the reviewer's dashboard here
    return render_template('reviewers_dashboard.html')






@app.route('/submit_paper', methods=['GET', 'POST']) 
@login_required
def submit_paper():
    if request.method == 'POST':
        # Extract form fields
        title = request.form.get('title')
        theme = request.form.get('theme')
        description = request.form.get('description', '')  # Default to an empty string if not provided
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