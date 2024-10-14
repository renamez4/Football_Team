from flask import Flask, request, render_template, redirect, url_for, flash, session
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'


db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'host': 'localhost',
    'database': 'project2'
}


def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection


@app.route('/')
def login():
    return render_template('login.html')


@app.route('/login_register', methods=['POST'])
def login_register():
    action_type = request.form.get('action_type')

    if action_type == 'login':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            'SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:
            session['loggedin'] = True
            session['username'] = user['username']
            flash('Success to login')
            return redirect(url_for('index'))
        else:
            print('Fail')
            flash('Invalid email or password, please try again.')
            return redirect(url_for('login'))

    elif action_type == 'register':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            flash('Account already exists!')
        else:

            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
            connection.commit()
            flash('You have successfully registered!')

        cursor.close()
        connection.close()
        return redirect(url_for('login'))


@app.route('/index')
def index():
    if 'loggedin' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect(url_for('login'))


@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        team_name = request.form['team_name']
        description = request.form['description']  
        players = []
        substitutes = []

        for i in range(1, 12):
            position = request.form[f'player{i}']
            players.append((position, f'Player {i}'))

        for i in range(1, 6):
            sub_position = request.form[f'sub{i}']
            substitutes.append((sub_position, f'Substitute {i}'))

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            for position, player_name in players:
                cursor.execute(
                    "INSERT INTO create_team (player_position, player_name, team_name, description) VALUES (%s, %s, %s, %s)",
                    (position, player_name, team_name, description)
                )

            for sub_position, sub_name in substitutes:
                cursor.execute(
                    "INSERT INTO substitutes (player_position, player_name, team_name) VALUES (%s, %s, %s)",
                    (sub_position, sub_name, team_name)
                )

            connection.commit()
            flash(f'Team {team_name} created successfully!', 'success')

        except Exception as e:
            connection.rollback()
            flash(f'Error: {str(e)}', 'danger')

        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('viewteam'))

    return render_template('create.html')


@app.route('/viewteam', methods=['GET', 'POST'])
def viewteam():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':

        for team_id, new_team_name in request.form.items():
            if team_id.startswith('team_name_'):
                
                team_id_value = team_id.split('_')[2]

                cursor.execute("SELECT team_name FROM create_team WHERE team_id = %s", (team_id_value,))
                current_team_name = cursor.fetchone()['team_name']

                
                if current_team_name != new_team_name:
                    
                    cursor.execute("""
                        UPDATE create_team
                        SET team_name = %s
                        WHERE team_name = %s
                    """, (new_team_name, current_team_name))

        connection.commit()
        flash('Team names updated successfully for all matching entries!')

    cursor.execute("SELECT team_id, team_name FROM create_team")
    teams = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('viewteam.html', teams=teams)


@app.route('/sport')
def sport():
    return render_template('sport.html')


@app.route('/join')
def join():
    return render_template('join.html')


@app.route('/account')
def account():
    return render_template('account.html')


# Route for logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
