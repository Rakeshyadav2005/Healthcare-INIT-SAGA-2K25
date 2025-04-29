# MediRemind: Medicine Reminder and Price Comparison

A web application that helps users set reminders for taking medications and compare medicine prices across different pharmacies.

## Features

- **Medicine Reminders**: Set reminders for taking medicines at specific times
- **Voice & Email Alerts**: Receive voice notifications and email reminders when it's time to take medicine
- **Price Comparison**: Compare medicine prices across different pharmacies
- **Prescription Upload**: Upload prescription images and automatically analyze for medications
- **User Authentication**: Secure login and registration with proper error handling
- **Visual Charts**: See price comparisons in an easy-to-understand chart format
- **Responsive UI**: Works on desktop and mobile devices
- **User Profile Management**: Update personal information and email notification preferences

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Data Visualization**: Chart.js
- **Voice Alerts**: pyttsx3
- **Email Notifications**: SMTP via Python's smtplib
- **Image Processing**: Basic pattern recognition (simulation for prescription analysis)

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/medicine-reminder.git
   cd medicine-reminder
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure email settings:
   Open `app.py` and update the email configuration with your email provider details:
   ```python
   # Email configuration
   app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change as needed
   app.config['MAIL_PORT'] = 587
   app.config['MAIL_USE_TLS'] = True
   app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
   app.config['MAIL_PASSWORD'] = 'your-app-password'
   ```
   Note: For Gmail, you'll need to use an "App Password" if you have 2FA enabled.

5. Run the application:
   ```
   python app.py
   ```

6. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

### Setting a Reminder

1. Click on the "Reminders" tab
2. Enter the medicine name
3. Select the time for the reminder
4. Click "Set Reminder"
5. You'll receive both in-app and email notifications at the scheduled time

### Comparing Medicine Prices

1. Click on the "Price Comparison" tab
2. Either:
   - Enter the name of the medicine manually, or
   - Upload a prescription image for automatic analysis
3. View the comparison chart and table showing prices at different pharmacies

### Managing Email Notifications

1. Log in to your account
2. Navigate to "My Profile"
3. Under "Reminder Settings," toggle the "Receive email reminders" option
4. Click "Save Changes"

### Viewing Active Reminders

1. Click on the "Active Reminders" tab
2. See all your currently scheduled reminders
3. Use the "Refresh" button to update the list

## Customizing Medicine Prices

The medicine prices are stored in `medicine_prices.csv`. You can edit this file to add more medicines or pharmacies.

Format:
```
Medicine Name,Pharmacy Name,Price
Paracetamol,Pharmacy A,10.99
```

## Troubleshooting

- **Voice alerts not working**: Make sure you have the necessary audio drivers installed on your system
- **Email notifications not received**: Check your spam folder and verify email settings in app.py
- **Prescription upload issues**: Ensure you're using a clear image in a supported format (JPG, PNG)
- **Reminders not triggering**: Keep the application running in the background
- **Error with time format**: Use 24-hour format (HH:MM) for setting reminders
- **Login issues**: If you're seeing "Incorrect email or password" errors, double-check your credentials

## Data Storage

User data, including reminders and medication lists, are stored in `users.json`. This file is created automatically when the first user registers.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [Chart.js](https://www.chartjs.org/)
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3)
- [Schedule](https://github.com/dbader/schedule) 