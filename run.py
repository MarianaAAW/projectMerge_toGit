from db_backend import app  # Import the app instance from routes

if __name__ == '__main__':
    with app.app_context():
        from db_backend import db
        db.create_all()  # Ensure all tables are created
    app.run(debug=True)
    