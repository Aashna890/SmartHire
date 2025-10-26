# SmartHire

A simple Django-based recruitment platform for recruiters and developers.

## Overview

SmartHire provides basic functionality for posting jobs and applying to them. It contains separate Django apps for accounts, jobs, developers and recruiters, and includes a small resume parsing utility (`resume.py`). The project is configured for development using SQLite.

## Requirements

- Python 3.8+
- Django 5.1.1
- requests
- PyPDF2
- spaCy (plus the language model: `en_core_web_sm`)

You can install the detected dependencies using the included `requirements.txt`.

## How to run (Windows PowerShell)

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Apply migrations and start the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

3. Open http://127.0.0.1:8000/ in your browser.


