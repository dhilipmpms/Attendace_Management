🚀 Features

    User Authentication: Secure login system for administrators and faculty

    Attendance Recording: Mark attendance for students efficiently

    Database Management: Utilizes SQLite for storing user and attendance data

    Responsive Design: Clean and intuitive UI for ease of use

🛠️ Technologies Used

    Backend: Django

    Frontend: HTML, CSS

    Database: SQLite

    Language: Python

📂 Project Structure

    ├── attendance/             # Django app for attendance functionalities
    ├── fast_attendance/        # Additional app/module (if applicable)
    ├── db.sqlite3              # SQLite database file
    ├── manage.py               # Django's command-line utility
    ├── LICENSE                 # Project license (GPL-3.0)
    └── README.md               # Project documentation

🧑‍💻 Getting Started

    Prerequisites
        Python 3.x installed on your system
        pip (Python package installer)

1. Installation

        git clone https://github.com/dhilipmpms/Attendace_Management.git
        cd Attendace_Management

2. Create a virtual environment (optional but recommended):

        python -m venv env
        source env/bin/activate  # On Windows: env\Scripts\activate

3. Install the required packages:

       pip install -r requirements.txt 

4. Apply migrations:

       python manage.py migrate
       python manage.py runserver
   
6. Access the application:

       Open your browser and navigate to http://127.0.0.1:8000/
       To access admin panel need to create superuser
       python manage.py createsuperuser
       Admin Panel: Access Django's built-in admin panel at http://127.0.0.1:8000/admin/ to manage users and attendance records.
📝 License

This project is licensed under the GNU General Public License v3.0. See the LICENSE file for more details.
               
🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.

📧 Contact

For any queries or suggestions, feel free to reach out:

    GitHub: @dhilipmpms


        
