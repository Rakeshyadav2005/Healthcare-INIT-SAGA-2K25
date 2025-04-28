from flask import Flask, request, jsonify
import schedule
import time
import pyttsx3
import datetime
import pandas as pd
import os
import threading
import platform
from typing import Dict, List
from pathlib import Path

app = Flask(__name__)

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

        self.reminders: Dict[str, str] = {}
        self.medicine_prices = self.load_medicine_prices()
        
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

    def set_reminder(self, medicine_name: str, reminder_time: str) -> Dict:
        """Set a reminder for taking medicine at a specific time."""
        try:
            if not self.validate_time_format(reminder_time):
                return {
                    "status": "error",
                    "message": "Invalid time format. Use HH:MM or HH:MM AM/PM"
                }

            time_24hour = self.convert_to_24hour(reminder_time)
            self.reminders[medicine_name] = time_24hour
            
            schedule.clear(medicine_name)
            schedule.every().day.at(time_24hour).do(
                self.alert_reminder, medicine_name
            ).tag(medicine_name)
            
            return {
                "status": "success",
                "message": f"Reminder set for {medicine_name} at {reminder_time}",
                "data": {
                    "medicine": medicine_name,
                    "time": reminder_time,
                    "time_24hour": time_24hour
                }
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def alert_reminder(self, medicine_name: str) -> None:
        """Alert the user when it's time to take medicine."""
        message = f"Time to take your {medicine_name}!"
        print(f"\n{'='*50}")
        print(f"REMINDER: {message}")
        print(f"Current time: {datetime.datetime.now().strftime('%I:%M %p')}")
        print(f"{'='*50}\n")
        
        if self.voice_system_available and self.engine:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Could not play voice alert: {e}")

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

    def list_reminders(self) -> Dict:
        """List all active reminders."""
        if not self.reminders:
            return {
                "status": "success",
                "message": "No active reminders",
                "data": []
            }
        
        reminders_list = []
        for medicine, time in self.reminders.items():
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

# Initialize the MedicineReminder instance
reminder = MedicineReminder()

@app.route('/')
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "success",
        "message": "Medicine Reminder API is running",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/set_reminder', methods=['POST'])
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
    
    result = reminder.set_reminder(medicine_name, reminder_time)
    return jsonify(result)

@app.route('/compare_prices', methods=['POST'])
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
    
    result = reminder.compare_prices(medicine_name)
    return jsonify(result)

@app.route('/list_reminders', methods=['GET'])
def api_list_reminders():
    """API endpoint to list all active reminders."""
    result = reminder.list_reminders()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 