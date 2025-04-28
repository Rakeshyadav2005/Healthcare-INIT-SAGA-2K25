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
            print("To enable voice alerts, please ensure you have:")
            if platform.system() == 'Windows':
                print("- Windows Speech Recognition installed")
            elif platform.system() == 'Darwin':  # macOS
                print("- macOS text-to-speech enabled")
            else:  # Linux
                print("- espeak or festival installed")
            self.engine = None

        self.reminders: Dict[str, str] = {}
        # Initialize medicine prices from CSV
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
            # Convert DataFrame to nested dictionary
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
            print("Using empty price database.")
            return {}

    def validate_time_format(self, time_str: str) -> bool:
        """Validate if the time string is in correct format."""
        try:
            # Try parsing in 24-hour format
            datetime.datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            try:
                # Try parsing in 12-hour format with AM/PM
                datetime.datetime.strptime(time_str, '%I:%M %p')
                return True
            except ValueError:
                return False

    def convert_to_24hour(self, time_str: str) -> str:
        """Convert time string to 24-hour format."""
        try:
            # If already in 24-hour format
            datetime.datetime.strptime(time_str, '%H:%M')
            return time_str
        except ValueError:
            try:
                # Convert from 12-hour format
                time_obj = datetime.datetime.strptime(time_str, '%I:%M %p')
                return time_obj.strftime('%H:%M')
            except ValueError:
                raise ValueError("Invalid time format")

    def set_reminder(self, medicine_name: str, reminder_time: str) -> None:
        """Set a reminder for taking medicine at a specific time."""
        try:
            if not self.validate_time_format(reminder_time):
                print("\nInvalid time format. Please use one of these formats:")
                print("24-hour format: HH:MM (e.g., 14:30)")
                print("12-hour format: HH:MM AM/PM (e.g., 2:30 PM)")
                return

            # Convert to 24-hour format for internal use
            time_24hour = self.convert_to_24hour(reminder_time)
            self.reminders[medicine_name] = time_24hour
            
            # Clear any existing schedule for this medicine
            schedule.clear(medicine_name)
            
            # Schedule the reminder
            schedule.every().day.at(time_24hour).do(
                self.alert_reminder, medicine_name
            ).tag(medicine_name)
            
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            print(f"\nReminder set for {medicine_name} at {reminder_time}")
            print(f"Current system time: {current_time}")
            print("The reminder will alert you at the specified time.")
            if self.voice_system_available:
                print("Voice alert will play when the reminder triggers.")
            else:
                print("Note: Voice alerts are not available. Only visual alerts will be shown.")
        except ValueError as e:
            print(f"Error: {e}")

    def alert_reminder(self, medicine_name: str) -> None:
        """Alert the user when it's time to take medicine."""
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        message = f"Time to take your {medicine_name}!"
        print(f"\n{'='*50}")
        print(f"REMINDER: {message}")
        print(f"Current time: {current_time}")
        print(f"{'='*50}\n")
        
        # Try to speak the reminder if voice system is available
        if self.voice_system_available and self.engine:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Could not play voice alert: {e}")
                print("Visual alert will still work.")

    def compare_prices(self, medicine_name: str) -> None:
        """Compare prices of a medicine across different pharmacies."""
        if not self.medicine_prices:
            print("\nError: Medicine price database is not available.")
            print("Please make sure medicine_prices.csv exists in the same directory.")
            return

        if medicine_name in self.medicine_prices:
            print(f"\nPrice comparison for {medicine_name}:")
            print("-" * 40)
            for pharmacy, price in self.medicine_prices[medicine_name].items():
                print(f"{pharmacy}: ${price:.2f}")
            print("-" * 40)
        else:
            print(f"\nMedicine '{medicine_name}' not found in our database.")
            print("Available medicines:")
            print("-" * 40)
            for med in sorted(self.medicine_prices.keys()):
                print(f"- {med}")
            print("-" * 40)

    def run_scheduler(self) -> None:
        """Run the scheduler in a separate thread."""
        while True:
            schedule.run_pending()
            time.sleep(1)

    def list_reminders(self) -> None:
        """List all active reminders."""
        if not self.reminders:
            print("\nNo active reminders.")
            return
            
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        print("\nActive Reminders:")
        print("-" * 40)
        print(f"Current system time: {current_time}")
        print("-" * 40)
        for medicine, time in self.reminders.items():
            # Convert 24-hour time to 12-hour format for display
            time_obj = datetime.datetime.strptime(time, '%H:%M')
            display_time = time_obj.strftime('%I:%M %p')
            print(f"{medicine}: {display_time}")
        print("-" * 40)
        if not self.voice_system_available:
            print("Note: Voice alerts are not available. Only visual alerts will be shown.")

def main():
    reminder = MedicineReminder()
    
    while True:
        print("\nMedicine Reminder and Price Comparison Tool")
        print("1. Set a reminder")
        print("2. Compare prices")
        print("3. List active reminders")
        print("4. Exit program")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            medicine_name = input("Enter medicine name: ")
            print("\nEnter time in either format:")
            print("24-hour format: HH:MM (e.g., 14:30)")
            print("12-hour format: HH:MM AM/PM (e.g., 2:30 PM)")
            reminder_time = input("Enter reminder time: ")
            reminder.set_reminder(medicine_name, reminder_time)
            
        elif choice == "2":
            medicine_name = input("Enter medicine name: ")
            reminder.compare_prices(medicine_name)
            
        elif choice == "3":
            reminder.list_reminders()
            
        elif choice == "4":
            print("Exiting program. Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 