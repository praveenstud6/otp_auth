# Import statements
from flask import Flask, render_template, request, redirect, url_for, session
from twilio.rest import Client
import random
import secrets
import psycopg2
from psycopg2 import sql
from datetime import datetime

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(24)

# PostgreSQL credentials
db_params = {
    'dbname': 'otp_auth',
    'user': 'postgres',
    'password': 'pk2512',
    'host': '127.0.0.1',
    'port': '5432',
}

# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(**db_params)
cur = conn.cursor()

# Create the table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS otp_auth (
        phone_number VARCHAR(15) PRIMARY KEY,
        otp VARCHAR(4),
        count INTEGER DEFAULT 1,
        last_verified_time TIMESTAMP
    )
""")
conn.commit()

# Twilio credentials
account_sid = 'AC92e1a22aaced6e30cb15e61ecc0a3c48'
auth_token = 'e7298edb9cede0bed52433c1bd34084e'
twilio_phone_number = '+14437362768'
client = Client(account_sid, auth_token)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    user_phone_number = request.form.get('phone_number')
    otp = generate_otp()

    # Check if the phone number exists in the database
    cur.execute(sql.SQL("SELECT * FROM otp_auth WHERE phone_number = {}").format(sql.Literal(user_phone_number)))
    existing_record = cur.fetchone()

    if existing_record:
        # If the phone number exists, update the OTP and increment the count
        cur.execute(sql.SQL("""
            UPDATE otp_auth
            SET otp = {},
                count = count + 1
            WHERE phone_number = {}
        """).format(sql.Literal(otp), sql.Literal(user_phone_number)))
    else:
        # If the phone number doesn't exist, insert a new record
        cur.execute("""
            INSERT INTO otp_auth (phone_number, otp, count)
            VALUES (%s, %s, 1)
        """, (user_phone_number, otp))

    conn.commit()

    # Reset OTP verification status in the session
    session['otp_verified'] = False
    send_otp_message(user_phone_number, otp)
    session['phone_number'] = user_phone_number
    session['otp'] = otp

    return redirect(url_for('verify_otp', phone_number=user_phone_number))

@app.route('/verify_otp/<phone_number>', methods=['GET', 'POST'])
def verify_otp(phone_number):
    error_message = None  # Initialize error message variable

    if request.method == 'POST':
        user_otp = request.form.get('otp')
        stored_otp = session.get('otp')

        if stored_otp and user_otp == stored_otp:
            # Update the last_verified_time in the database
            cur.execute(sql.SQL("""
                UPDATE otp_auth
                SET last_verified_time = {}
                WHERE phone_number = {}
            """).format(sql.Literal(datetime.now()), sql.Literal(phone_number)))

            conn.commit()

            session['otp_verified'] = True  # Set OTP verification status
            return redirect(url_for('welcome'))

        else:
            error_message = 'Invalid OTP. Please try again.'

    return render_template('verify_otp.html', phone_number=phone_number, error_message=error_message)

@app.route('/welcome')
def welcome():
    if not session.get('otp_verified'):
        return redirect(url_for('index'))

    return render_template('welcome.html')

# Helper functions
def generate_otp():
    return str(random.randint(1000, 9999))

def send_otp_message(to, otp):
    message = client.messages.create(
        body=f'Your OTP is: {otp}',
        from_=twilio_phone_number,
        to=to
    )
    print(f"OTP sent with SID: {message.sid}")

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
