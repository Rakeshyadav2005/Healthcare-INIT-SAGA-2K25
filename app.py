from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import schedule
import time
import pyttsx3
import datetime
import pandas as pd
import os
import threading
import platform
import json
from typing import Dict, List
from pathlib import Path
import hashlib
import uuid
from functools import wraps
import base64
from werkzeug.utils import secure_filename
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'mediremind_secret_key_2025'  # For session management
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mediremind.app@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your_app_password'  # Replace with your app password

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class User:
    def __init__(self, name, email, password_hash, user_id=None):
        self.user_id = user_id or str(uuid.uuid4())
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.reminders = {}
        self.medications = []
        self.price_checks = []
        self.streak_days = 0
        self.email_notifications = True  # Default to enabled
        
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'password_hash': self.password_hash,
            'reminders': self.reminders,
            'medications': self.medications,
            'price_checks': self.price_checks,
            'streak_days': self.streak_days,
            'email_notifications': self.email_notifications
        }
    
    @classmethod
    def from_dict(cls, data):
        user = cls(
            name=data['name'],
            email=data['email'],
            password_hash=data['password_hash'],
            user_id=data['user_id']
        )
        user.reminders = data.get('reminders', {})
        user.medications = data.get('medications', [])
        user.price_checks = data.get('price_checks', [])
        user.streak_days = data.get('streak_days', 0)
        user.email_notifications = data.get('email_notifications', True)
        return user

class UserManager:
    def __init__(self):
        self.users = {}
        self.users_file = 'users.json'
        self.load_users()
        
    def load_users(self):
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_id, user_data in users_data.items():
                        self.users[user_id] = User.from_dict(user_data)
                print(f"Loaded {len(self.users)} users from {self.users_file}")
            else:
                print(f"No users file found at {self.users_file}")
        except Exception as e:
            print(f"Error loading users: {e}")
            
    def save_users(self):
        try:
            users_data = {user_id: user.to_dict() for user_id, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=4)
            print(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            print(f"Error saving users: {e}")
            
    def get_user_by_email(self, email):
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None
        
    def get_user_by_id(self, user_id):
        return self.users.get(user_id)
        
    def create_user(self, name, email, password):
        # Check if user with email already exists
        if self.get_user_by_email(email):
            return None
            
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create new user
        user = User(name, email, password_hash)
        self.users[user.user_id] = user
        self.save_users()
        return user
        
    def authenticate_user(self, email, password):
        user = self.get_user_by_email(email)
        if not user:
            return None
            
        password_hash = self._hash_password(password)
        if user.password_hash == password_hash:
            return user
        return None
        
    def update_user(self, user_id, name=None, email=None, password=None, email_notifications=None):
        user = self.get_user_by_id(user_id)
        if not user:
            return False
            
        if name:
            user.name = name
        if email:
            user.email = email
        if password:
            user.password_hash = self._hash_password(password)
        if email_notifications is not None:
            user.email_notifications = email_notifications
            
        self.save_users()
        return True
        
    def _hash_password(self, password):
        # Simple password hashing - in production, use a more secure method
        return hashlib.sha256(password.encode()).hexdigest()

class MedicineReminder:
    def __init__(self):
        self.voice_system_available = False
        try:
            self.engine = pyttsx3.init()
            # Test the voice system
            self.engine.say("Voice system initialized")
            self.engine.runAndWait()
            self.voice_system_available = True
            print("\nVoice alert system is ready!")
        except Exception as e:
            print(f"\nWarning: Could not initialize voice system: {e}")
            print("Reminders will still work, but without voice alerts.")
            self.engine = None

        self.medicine_prices = self.load_medicine_prices()
        self.user_manager = UserManager()
        
        # Start the scheduler in a separate thread
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()

    def load_medicine_prices(self) -> Dict:
        """Load medicine prices from CSV file."""
        try:
            csv_path = Path("medicine_prices.csv")
            if not csv_path.exists():
                print("Warning: medicine_prices.csv not found. Using empty price database.")
                return {}
            
            df = pd.read_csv(csv_path)
            prices_dict = {}
            for _, row in df.iterrows():
                medicine = row['Medicine Name']
                pharmacy = row['Pharmacy Name']
                price = float(row['Price'])
                
                if medicine not in prices_dict:
                    prices_dict[medicine] = {}
                prices_dict[medicine][pharmacy] = price
            
            return prices_dict
        except Exception as e:
            print(f"Error loading medicine prices: {e}")
            return {}

    def validate_time_format(self, time_str: str) -> bool:
        """Validate if the time string is in correct format."""
        try:
            datetime.datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            try:
                datetime.datetime.strptime(time_str, '%I:%M %p')
                return True
            except ValueError:
                return False

    def convert_to_24hour(self, time_str: str) -> str:
        """Convert time string to 24-hour format."""
        try:
            datetime.datetime.strptime(time_str, '%H:%M')
            return time_str
        except ValueError:
            try:
                time_obj = datetime.datetime.strptime(time_str, '%I:%M %p')
                return time_obj.strftime('%H:%M')
            except ValueError:
                raise ValueError("Invalid time format")

    def set_reminder(self, user_id: str, medicine_name: str, reminder_time: str) -> Dict:
        """Set a reminder for taking medicine at a specific time."""
        try:
            user = self.user_manager.get_user_by_id(user_id)
            if not user:
                return {
                    "status": "error",
                    "message": "User not found"
                }
                
            if not self.validate_time_format(reminder_time):
                return {
                    "status": "error",
                    "message": "Invalid time format. Use HH:MM or HH:MM AM/PM"
                }

            time_24hour = self.convert_to_24hour(reminder_time)
            
            # Store reminder in user's reminders
            if medicine_name not in user.reminders:
                user.reminders[medicine_name] = time_24hour
                
                # Add medication to user's list if not already there
                if medicine_name not in user.medications:
                    user.medications.append(medicine_name)
                
                # Save updated user data
                self.user_manager.save_users()
            
            # Set up scheduler
            schedule_tag = f"{user_id}_{medicine_name}"
            schedule.clear(schedule_tag)
            schedule.every().day.at(time_24hour).do(
                self.alert_reminder, user_id, medicine_name
            ).tag(schedule_tag)
            
            # Format time for display
            time_obj = datetime.datetime.strptime(time_24hour, '%H:%M')
            time_display = time_obj.strftime('%I:%M %p')
            
            return {
                "status": "success",
                "message": f"Reminder set for {medicine_name} at {time_display}",
                "data": {
                    "medicine": medicine_name,
                    "time": reminder_time,
                    "time_24hour": time_24hour,
                    "time_display": time_display
                }
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def alert_reminder(self, user_id: str, medicine_name: str) -> None:
        """Alert the user when it's time to take medicine."""
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            print(f"User {user_id} not found for reminder")
            return
            
        message = f"Time to take your {medicine_name}!"
        print(f"\n{'='*50}")
        print(f"REMINDER for {user.name}: {message}")
        print(f"Current time: {datetime.datetime.now().strftime('%I:%M %p')}")
        print(f"{'='*50}\n")
        
        # Voice alert
        if self.voice_system_available and self.engine:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Could not play voice alert: {e}")
        
        # Email alert - only send if user has email notifications enabled
        if user.email_notifications:
            try:
                self.send_reminder_email(user.email, user.name, medicine_name)
                print(f"Email reminder sent to {user.email}")
            except Exception as e:
                print(f"Failed to send email reminder: {e}")
        else:
            print(f"Email notifications disabled for user {user.name}")

    def send_reminder_email(self, email: str, user_name: str, medicine_name: str) -> None:
        """Send an email reminder to the user."""
        try:
            current_time = datetime.datetime.now().strftime('%I:%M %p')
            
            msg = MIMEMultipart()
            msg['Subject'] = f"MediRemind: Time to take {medicine_name}"
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = email
            
            # Email content
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4a90e2; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f8f9fa; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Medicine Reminder</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {user_name},</h2>
                        <p>It's time to take your medication:</p>
                        <p style="font-size: 18px; font-weight: bold; color: #4a90e2;">{medicine_name}</p>
                        <p>Current time: {current_time}</p>
                        <p>Stay healthy!</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated reminder from MediRemind.</p>
                        <p>&copy; 2025 MediRemind - Healthcare INIT-SAGA</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Connect to the SMTP server and send the email
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)
                
        except Exception as e:
            raise Exception(f"Failed to send email: {str(e)}")

    def compare_prices(self, medicine_name: str) -> Dict:
        """Compare prices of a medicine across different pharmacies."""
        if not self.medicine_prices:
            return {
                "status": "error",
                "message": "Medicine price database is not available"
            }

        if medicine_name in self.medicine_prices:
            return {
                "status": "success",
                "data": {
                    "medicine": medicine_name,
                    "prices": self.medicine_prices[medicine_name]
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Medicine '{medicine_name}' not found",
                "available_medicines": sorted(list(self.medicine_prices.keys()))
            }

    def list_reminders(self, user_id: str) -> Dict:
        """List all active reminders for a user."""
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            return {
                "status": "error",
                "message": "User not found"
            }
            
        if not user.reminders:
            return {
                "status": "success",
                "message": "No active reminders",
                "data": []
            }
        
        reminders_list = []
        for medicine, time in user.reminders.items():
            time_obj = datetime.datetime.strptime(time, '%H:%M')
            display_time = time_obj.strftime('%I:%M %p')
            reminders_list.append({
                "medicine": medicine,
                "time_24hour": time,
                "time_display": display_time
            })
        
        return {
            "status": "success",
            "data": reminders_list
        }

    def run_scheduler(self) -> None:
        """Run the scheduler in a separate thread."""
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    def record_price_check(self, user_id: str, medicine_name: str) -> bool:
        """Record a price check for a user."""
        user = self.user_manager.get_user_by_id(user_id)
        if not user or medicine_name not in self.medicine_prices:
            return False
            
        prices = self.medicine_prices[medicine_name]
        price_values = list(prices.values())
        
        check = {
            "medicine": medicine_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "min_price": min(price_values),
            "max_price": max(price_values)
        }
        
        # Add to the beginning of the list (most recent first)
        user.price_checks.insert(0, check)
        
        # Keep only the last 10 checks
        user.price_checks = user.price_checks[:10]
        
        # Save updated user data
        self.user_manager.save_users()
        return True

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize the MedicineReminder instance
reminder = MedicineReminder()

@app.route('/')
def landing():
    """Landing page with registration and login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user = reminder.user_manager.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('landing'))
        
    # Get active reminders
    reminders_result = reminder.list_reminders(user.user_id)
    upcoming_reminders = reminders_result.get('data', [])
    
    return render_template(
        'dashboard.html', 
        user=user, 
        active_reminders_count=len(user.reminders),
        medications_count=len(user.medications),
        streak_days=user.streak_days,
        upcoming_reminders=upcoming_reminders,
        recent_price_checks=user.price_checks
    )

@app.route('/reminders')
@login_required
def reminders_page():
    """Reminders page."""
    return render_template('index.html')

@app.route('/prices')
@login_required
def prices_page():
    """Price comparison page."""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: name, email, and password"
        }), 400
    
    # Create the user
    user = reminder.user_manager.create_user(name, email, password)
    
    if not user:
        return jsonify({
            "status": "error",
            "message": "Email already registered"
        }), 400
    
    return jsonify({
        "status": "success",
        "message": "User registered successfully",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email
        }
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: email and password"
        }), 400
    
    # Authenticate the user
    user = reminder.user_manager.authenticate_user(email, password)
    
    if not user:
        return jsonify({
            "status": "error",
            "message": "Invalid email or password"
        }), 401
    
    # Set the user's ID in the session
    session['user_id'] = user.user_id
    
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email
        }
    })

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint for user logout."""
    session.clear()
    return jsonify({
        "status": "success",
        "message": "Logout successful"
    })

@app.route('/api/profile', methods=['GET'])
@login_required
def api_get_profile():
    """API endpoint to get user profile."""
    user = reminder.user_manager.get_user_by_id(session['user_id'])
    
    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404
    
    return jsonify({
        "status": "success",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email
        }
    })

@app.route('/api/profile', methods=['PUT'])
@login_required
def api_update_profile():
    """API endpoint to update user profile."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    name = data.get('name')
    email = data.get('email')
    email_notifications = data.get('email_notifications')
    
    if not name and not email and email_notifications is None:
        return jsonify({
            "status": "error",
            "message": "No fields to update"
        }), 400
    
    # Update the user
    success = reminder.user_manager.update_user(
        session['user_id'],
        name=name,
        email=email,
        email_notifications=email_notifications
    )
    
    if not success:
        return jsonify({
            "status": "error",
            "message": "Failed to update profile"
        }), 500
    
    user = reminder.user_manager.get_user_by_id(session['user_id'])
    
    return jsonify({
        "status": "success",
        "message": "Profile updated successfully",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "email_notifications": user.email_notifications
        }
    })

@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    """API endpoint to change user password."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: current_password and new_password"
        }), 400
    
    # Verify current password
    user = reminder.user_manager.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404
    
    if user.password_hash != reminder.user_manager._hash_password(current_password):
        return jsonify({
            "status": "error",
            "message": "Current password is incorrect"
        }), 401
    
    # Update password
    success = reminder.user_manager.update_user(
        session['user_id'],
        password=new_password
    )
    
    if not success:
        return jsonify({
            "status": "error",
            "message": "Failed to update password"
        }), 500
    
    return jsonify({
        "status": "success",
        "message": "Password updated successfully"
    })

@app.route('/set_reminder', methods=['POST'])
@login_required
def api_set_reminder():
    """API endpoint to set a medicine reminder."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    medicine_name = data.get('medicine_name')
    reminder_time = data.get('reminder_time')
    
    if not medicine_name or not reminder_time:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: medicine_name and reminder_time"
        }), 400
    
    result = reminder.set_reminder(session['user_id'], medicine_name, reminder_time)
    return jsonify(result)

@app.route('/compare_prices', methods=['POST'])
@login_required
def api_compare_prices():
    """API endpoint to compare medicine prices."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400
    
    medicine_name = data.get('medicine_name')
    
    if not medicine_name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: medicine_name"
        }), 400
    
    # Record price check
    reminder.record_price_check(session['user_id'], medicine_name)
    
    result = reminder.compare_prices(medicine_name)
    return jsonify(result)

@app.route('/list_reminders', methods=['GET'])
@login_required
def api_list_reminders():
    """API endpoint to list all active reminders."""
    result = reminder.list_reminders(session['user_id'])
    return jsonify(result)

@app.route('/analyze_prescription', methods=['POST'])
@login_required
def api_analyze_prescription():
    """API endpoint to analyze a prescription image and extract medicines."""
    if 'prescription_image' not in request.files:
        return jsonify({
            "status": "error",
            "message": "No prescription image uploaded"
        }), 400
    
    file = request.files['prescription_image']
    
    if file.filename == '':
        return jsonify({
            "status": "error",
            "message": "No file selected"
        }), 400
    
    if file:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Placeholder for actual OCR/prescription analysis
            # In a real implementation, this would use OCR and ML to detect medicines
            # Instead, we'll simulate medicine detection for demo purposes
            
            # Basic pattern matching for medicine names in the image name
            # This is just a placeholder - real implementation would use actual image processing
            medicine_names = []
            
            # First check if any of our known medicines appear in the filename
            for medicine in reminder.medicine_prices.keys():
                # Case insensitive search for medicine name in filename
                if re.search(rf'\b{re.escape(medicine)}\b', filename, re.IGNORECASE):
                    medicine_names.append(medicine)
            
            # If no matches in filename, add some common medicines for demonstration
            if not medicine_names and reminder.medicine_prices:
                # Take up to 3 random medicines from our database
                import random
                available_medicines = list(reminder.medicine_prices.keys())
                sample_size = min(3, len(available_medicines))
                medicine_names = random.sample(available_medicines, sample_size)
            
            # Process detected medicines
            medicines_data = []
            for medicine in medicine_names:
                if medicine in reminder.medicine_prices:
                    prices = reminder.medicine_prices[medicine]
                    # Find best price
                    best_price = float('inf')
                    best_pharmacy = ""
                    
                    for pharmacy, price in prices.items():
                        if price < best_price:
                            best_price = price
                            best_pharmacy = pharmacy
                    
                    medicines_data.append({
                        "name": medicine,
                        "prices": prices,
                        "best_price": best_price,
                        "best_pharmacy": best_pharmacy
                    })
            
            # Record the price check for each medicine
            user_id = session['user_id']
            for medicine in medicine_names:
                reminder.record_price_check(user_id, medicine)
            
            return jsonify({
                "status": "success",
                "message": f"Found {len(medicines_data)} medicines in prescription",
                "data": {
                    "medicines": medicines_data,
                    "image_path": file_path
                }
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error analyzing prescription: {str(e)}"
            }), 500
        finally:
            # In a production app, you might want to keep the file for audit or cleanup later
            # For this demo, we'll delete it immediately to save space
            try:
                os.remove(file_path)
            except:
                pass
    
    return jsonify({
        "status": "error",
        "message": "Invalid file format"
    }), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 