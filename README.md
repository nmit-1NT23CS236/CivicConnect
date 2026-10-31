# CivicConnect – Public Grievance Management Portal

CivicConnect is a web-based Public Grievance Management System designed to simplify the process of reporting, managing, and tracking public complaints. It provides a centralized platform where citizens can submit complaints related to civic issues and administrators can review, manage, and update their progress.

The system improves transparency, accessibility, and communication between citizens and administrators through complaint status tracking.

## Problem Statement

Citizens often face difficulties reporting public issues and tracking whether their complaints have been addressed. Traditional complaint-handling processes can lack transparency, timely updates, and centralized management.

CivicConnect aims to address these challenges through a simple and accessible digital grievance management platform.

## Objectives

- Provide citizens with an easy-to-use platform to submit public complaints.
- Generate unique reference IDs for submitted complaints.
- Allow administrators to manage and resolve complaints.
- Enable citizens to track complaint progress.
- Improve transparency through complaint status history.
- Protect citizen information through role-based access.

## Features

### Citizen Module
- Citizen registration and login.
- Secure password hashing.
- Submit complaints under different categories:
  - Road
  - Water
  - Electricity
  - Garbage
  - Other
- Add complaint descriptions and locations.
- Upload supporting complaint images.
- Receive a unique complaint reference ID.
- View submitted complaints through a personal dashboard.
- Search and filter complaints by category and status.
- View complaint progress and status history.

### Admin Module
- Secure administrator login.
- View and manage submitted complaints.
- Update complaint statuses:
  - Pending
  - In Progress
  - Resolved
- Add remarks while updating complaint status.
- View complaint status history.
- Dashboard statistics and analytics.
- Category-wise complaint charts.
- Date-based filtering and complaint management.

### Public Complaint Tracking
- Track complaints without logging in.
- Search using the unique complaint reference ID.
- View complaint details and current status.
- View chronological status history and administrator remarks.
- Access tracking without exposing private citizen information.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database |
| Flask-SQLAlchemy | Database ORM |
| HTML5 | Page structure |
| CSS3 | Styling and responsive design |
| JavaScript | Client-side interactions |
| Bootstrap | UI components |
| Werkzeug | Password hashing and security utilities |

## System Architecture

```text
        CITIZEN                  ADMIN
           |                       |
           v                       v
     Web Interface           Admin Dashboard
           |                       |
           +-----------+-----------+
                       |
                       v
                Flask Backend
                       |
              Authentication
              Complaint Routes
              Tracking Routes
                       |
                       v
               SQLAlchemy ORM
                       |
                       v
                 SQLite DB
```

## Project Structure

```text
CivicConnect/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── user_dashboard.html
│   ├── admin_dashboard.html
│   ├── submit_complaint.html
│   └── track_complaint.html
│
└── static/
    └── style.css
```

*Note: The local SQLite database and uploaded complaint evidence are excluded from the Git repository.*

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/nmit-1NT23CS236/CivicConnect.git
```

### 2. Navigate to the project directory

```bash
cd CivicConnect
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows:**

```powershell
venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure the application secret key

Set a secure secret key before running the application.

**PowerShell:**

```powershell
$env:SECRET_KEY = "replace-with-a-secure-random-secret"
```

Use a securely generated secret in your local environment. Do not commit secrets to GitHub.

### 7. Run the application

```bash
python app.py
```

### 8. Open in your browser

```text
http://127.0.0.1:5000
```

## Application Workflow

1. A citizen registers and logs into CivicConnect.
2. The citizen submits a complaint with its category, description, location, and optional image.
3. The application generates a unique complaint reference ID.
4. The administrator reviews the submitted complaint.
5. The administrator updates the complaint status and adds remarks.
6. The citizen can view progress through their dashboard.
7. Anyone with the complaint reference ID can access the public tracking page without logging in.

## Security Features

- Password hashing using Werkzeug.
- Session-based authentication.
- Role-based access control for citizens and administrators.
- Input validation.
- Uploaded image type and size validation.
- Secure filenames for uploaded files.
- Privacy-conscious public complaint tracking.

## Future Enhancements

- Email and SMS notifications for complaint updates.
- Interactive maps for complaint locations.
- Advanced complaint analytics.
- AI-based complaint categorization and prioritization.
- Mobile application integration.
- Multilingual support.

## Project Repository

GitHub: https://github.com/nmit-1NT23CS236/CivicConnect

## License

This project is developed for educational and hackathon purposes. A formal open-source license can be added if the project is released for public reuse.

---

**CivicConnect – Making Public Grievance Reporting More Accessible, Transparent, and Accountable.**
