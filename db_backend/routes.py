import datetime
import os
from flask import  abort, render_template, request, redirect, url_for, flash, session, jsonify
from db_backend import app,db
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from db_backend.models import  Draft, Notification, ReviewerAssignment, User, Paper, Review # I
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


@app.route('/view_paper/<int:paper_id>', methods=['GET'])
def view_paper(paper_id):
    # Fetch the paper by its ID from the database
    paper = Paper.query.get_or_404(paper_id)

    # Ensure the paper is published before allowing access
    if paper.status != 'published':
        return redirect(url_for('research_page'))

    # Render the paper in a template
    return render_template('view_paper.html', paper=paper)


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
    theme = request.args.get('theme')
    submission_date = request.args.get('submission_date')

    paper_query = Paper.query.filter(Paper.status == 'published')  # Only show published papers
    #user_query = User.query
    #users = user_query.all()
    papers = paper_query

    if theme:
        if theme == "Natural Science":
            first_1 = Paper.query.filter(Paper.theme == "Natural Science", Paper.status == 'published')
            return render_template('my_home.html', papers=first_1)#, users=users)
        elif theme == "Social Science":
            second_2 = Paper.query.filter(Paper.theme == "Social Science", Paper.status == 'published')
            return render_template('my_home.html', papers=second_2)#, users=users)
        else:
            third_3 = Paper.query.filter(Paper.theme == "Formal Science", Paper.status == 'published')
            return render_template('my_home.html', papers=third_3)#, users=users)
    if submission_date:
        if submission_date == "old to new":
            new = Paper.query.filter(Paper.status == 'published').order_by(Paper.submission_date)
            return render_template('my_home.html', papers=new)#, users=users)
        elif submission_date == "new to old":
            late = Paper.query.filter(Paper.status == 'published').order_by(Paper.submission_date.desc())
            return render_template('my_home.html', papers=late)#, users=users)
        else:
            return render_template('my_home.html', papers=papers)#, users=users)
    return render_template('my_home.html', papers=papers)#, users=users)
  

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
    author_id = request.args.get('author_id')
    theme = request.args.get('theme')
    submission_date = request.args.get('submission_date')
    user_id = current_user.id
    # Build the query
    paper_query = Paper.query.filter(Paper.author_id == user_id)
    papers = paper_query

    if theme:
        if theme == "Natural Science":
            first_1 = Paper.query.filter(Paper.theme == "Natural Science", Paper.author_id == user_id)
            return render_template('researchers_dashboard.html', papers=first_1)
        elif theme == "Social Science":
            second_2 = Paper.query.filter(Paper.theme == "Social Science", Paper.author_id ==user_id)
            return render_template('researchers_dashboard.html', papers=second_2)
        else:
            third_3 = Paper.query.filter(Paper.theme == "Formal Science", Paper.author_id ==user_id)
            return render_template('researchers_dashboard.html', papers=third_3)
    if submission_date:
        if submission_date == "old to new":
            new = Paper.query.filter(Paper.author_id == user_id).order_by(Paper.submission_date)
            return render_template('researchers_dashboard.html', papers=new)
        elif submission_date == "new to old":
            late = Paper.query.filter(Paper.author_id == user_id).order_by(Paper.submission_date.desc())
            return render_template('researchers_dashboard.html', papers=late)
        else:
            return render_template('researchers_dashboard.html', papers=papers)
    return render_template('researchers_dashboard.html', papers=papers)
    
    papers = paper_query.all()

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
    role = request.args.get('role')
    submission_date = request.args.get('submission_date')
    # Build the query for fetching papers
    paper_query = Paper.query
    user_query = User.query
    users = user_query.all()
    papers = paper_query.all()

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
    
    if submission_date:
        if submission_date == "old to new":
            new = Paper.query.order_by(Paper.submission_date).all()
            return render_template('admins_dashboard.html', papers=new, users=users)
        elif submission_date == "new to old":
            late = Paper.query.order_by(Paper.submission_date.desc()).all()
            return render_template('admins_dashboard.html', papers=late, users=users)
        else:
            return render_template('admins_dashboard.html', papers=papers, users=users)
        
    if role:
        print("role:",role,type(role))
        if role == "researcher":
            usr_1 = User.query.filter(User.role == "researcher").all()
            return render_template('admins_dashboard.html', papers=papers, users=usr_1)
        else: 
            usr_2 = User.query.filter(User.role == "researcher & reviewer").all()
            return render_template('admins_dashboard.html', papers=papers, users=usr_2)
        
    return render_template('admins_dashboard.html', papers=papers, users=users)

@app.route('/admins_view_user_details/<int:user_id>', methods=['GET'])
def admins_view_user_details(user_id):
    try:
        # Query the specific user by ID
        user = User.query.get(user_id)

        # If user does not exist, handle the error
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Convert user data to a dictionary
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "preferences": user.preferences,
            "role": user.role,
            "approved_papers": user.approved_papers,
            "assigned_papers": user.assigned_papers,
        }

        # Render the template and pass the user data
        return render_template('admins_view_user_details.html', user=user_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admins_view_paper_detail/<int:paper_id>', methods=['GET', 'POST'])
def admins_view_paper_detail(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    reviewers = paper.reviewers

    if request.method == 'POST':
        new_status = request.form.get('status')
        if new_status and new_status != paper.status:
            paper.status = new_status
            db.session.commit()
            flash("Paper status updated successfully.")

    return render_template('admins_view_paper_detail.html', paper=paper, reviewers=reviewers)


@app.route('/admin_review/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def admin_review(paper_id):
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

    return render_template('admin_review.html', paper=paper, reviews=reviews, admin_review=admin_review)

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

@app.route('/assign_reviewer/<int:paper_id>', methods=['GET', 'POST'])
def assign_reviewer(paper_id):
    print(f"Accessing assign_reviewer with paper_id: {paper_id}")
    paper = Paper.query.get_or_404(paper_id)
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        print(f"Received POST request with user_id: {user_id}")
        user = User.query.get(user_id)
        if user:
            if 'reviewer' not in user.role:
                user.role += ' & reviewer'
            paper.reviewers.append(user)
            db.session.commit()
            flash(f'{user.first_name} {user.last_name} has been assigned as a reviewer.', 'success')
            return redirect(url_for('assign_reviewer', paper_id=paper_id))
        else:
            flash('User not found.', 'error')
    
    users = User.query.filter(User.role != 'admin').all()
    return render_template('assign_reviewer.html', users=users, paper=paper)

@app.route('/make_reviewer', methods=['POST'])
def make_reviewer():
    user_id = request.form.get('user_id')
    paper_id = request.form.get('paper_id')
    if user_id and paper_id:
        user = User.query.get(user_id)
        if user:
            if 'reviewer' not in user.role:
                user.role += ' & reviewer'
                db.session.commit()
                print(f"User {user.first_name} {user.last_name} has been made a reviewer")
                flash(f'{user.first_name} {user.last_name} has been made a reviewer.', 'success')
            else:
                flash(f'{user.first_name} {user.last_name} is already a reviewer.', 'info')
        else:
            flash('User not found.', 'error')
    else:
        flash('Missing user_id or paper_id.', 'error')
    return redirect(url_for('assign_reviewer', paper_id=paper_id))

@app.route('/reviewers_dashboard', methods=['GET'])
@login_required
def reviewers_dashboard():
    # Assuming current_user is the logged-in user
    theme = request.args.get('theme')
    submission_date = request.args.get('submission_date')
    user_id = current_user.id

    assigned_papers = Paper.query.filter(Paper.reviewers.any(id=current_user.id)).all()
    papers = assigned_papers

    if theme:
        if theme == "Natural Science":
            first_1 = Paper.query.filter(Paper.theme == "Natural Science", Paper.reviewers.any(id=current_user.id)).all()
            return render_template('reviewers_dashboard.html', papers=first_1)
        elif theme == "Social Science":
            second_2 = Paper.query.filter(Paper.theme == "Social Science", Paper.reviewers.any(id=current_user.id)).all()
            return render_template('reviewers_dashboard.html', papers=second_2)
        else:
            third_3 = Paper.query.filter(Paper.theme == "Formal Science", Paper.reviewers.any(id=current_user.id)).all()
            return render_template('reviewers_dashboard.html', papers=third_3)
    if submission_date:
        if submission_date == "old to new":
            new = Paper.query.filter(Paper.reviewers.any(id=current_user.id)).order_by(Paper.submission_date)
            return render_template('reviewers_dashboard.html', papers=new)
        elif submission_date == "new to old":
            late = Paper.query.filter(Paper.reviewers.any(id=current_user.id)).order_by(Paper.submission_date.desc())
            return render_template('reviewers_dashboard.html', papers=late)
        else:
            return render_template('reviewers_dashboard.html', papers=papers)
    
    return render_template('reviewers_dashboard.html', papers=assigned_papers)

@app.route('/reviewers_review/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def reviewers_review(paper_id):
    # Fetch the paper
    paper = Paper.query.get_or_404(paper_id)
    
    # Check if the logged-in user is the assigned reviewer
    if current_user not in paper.reviewers:
        flash("You are not authorized to review this paper.", "danger")
        return redirect(url_for('reviewers_dashboard'))
    
    if request.method == 'POST':
        # Capture review details from the form
        review_text = request.form.get('review_text')
        status = request.form.get('status')  # e.g., 'approved', 'needs_revision', 'rejected'
        
        if not review_text or not status:
            flash("Please provide all required details.", "warning")
            return redirect(request.url)
        
        # Save the review to the database
        review = Review(
            paper_id=paper_id,
            reviewer_id=current_user.id,
            review_text=review_text,
            status=status,
            review_date=datetime.utcnow()
        )
        db.session.add(review)
        
        # Update paper status if necessary
        paper.status = status
        db.session.commit()
        
        flash("Review submitted successfully.", "success")
        return redirect(url_for('reviewers_dashboard'))
    
    return render_template('reviewers_review.html', paper=paper)

@app.route('/reviewers_view_paper/<int:paper_id>', methods=['GET'])
@login_required
def reviewers_view_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    return render_template('reviewers_view_paper.html', paper=paper)

@app.route('/submit_paper', methods=['GET', 'POST']) 
@login_required
def submit_paper():
    if request.method == 'POST':
        # Extract form fields
        title = request.form.get('title')
        theme = request.form.get('theme')
        description = request.form.get('Description')  # Default to an empty string if not provided
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

