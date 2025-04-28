# Medicine Reminder and Price Comparison Tool

A Python-based CLI tool for setting medicine reminders and comparing medicine prices across different pharmacies.

## Features

- Set medicine reminders with voice alerts
- Compare medicine prices across multiple pharmacies
- Simple CLI interface
- Support for both 12-hour and 24-hour time formats

## Requirements

- Python 3.6 or higher
- Windows Speech Recognition (for voice alerts)
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

Run the program:
```bash
python medicine_reminder.py
```

### Menu Options

1. Set a reminder
   - Enter medicine name
   - Enter time (HH:MM or HH:MM AM/PM)

2. Compare prices
   - Enter medicine name to see price comparison

3. List active reminders
   - View all currently set reminders

4. Exit program

## Voice Alerts

The program uses Windows Speech Recognition for voice alerts. Make sure:
- Windows Speech Recognition is installed
- Audio system is working properly
- Speakers/headphones are connected

## Contributing

Feel free to submit issues and enhancement requests. 