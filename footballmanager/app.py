from flask import Flask, request, render_template, redirect, url_for, flash, session
import mysql.connector
import os
from dotenv import load_dotenv
import bcrypt
import json
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
    if 'loggedin' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login_register', methods=['POST'])
def login_register():
    action_type = request.form.get('action_type')

    if action_type == 'login':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get the user data from the database
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')): 
            # Set session data
            session['loggedin'] = True
            session['user_id'] = str(user['user_id'])
            session['username'] = user['username']
            flash('Success to login')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password, please try again.')
            return redirect(url_for('login'))

    # Handle registration
    elif action_type == 'register':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')  # Encode password to bytes for bcrypt

        # Hash the password with bcrypt
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if the account already exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            flash('Account already exists!')
        else:
            # Insert new user with hashed password into the database
            cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                           (username, email, hashed_password.decode('utf-8')))
            connection.commit()
            flash('You have successfully registered!')

        cursor.close()
        connection.close()
        return redirect(url_for('login'))

@app.route('/accountmodify', methods=['POST'])
def accountmodify():
    if 'loggedin' in session:
        action_type = request.form.get('action_type')

        if action_type == 'modify':
            user_id = session['user_id']

            username = request.form.get('username')
            email = request.form.get('email')
            phone = request.form.get('phone')
            bio = request.form.get('bio')
            ability1 = request.form.get('ability1')
            ability2 = request.form.get('ability2')
            ability3 = request.form.get('ability3')

            connection = get_db_connection()
            cursor = connection.cursor()

            try:
                # Check if the new email already exists for another user
                cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                existing_user = cursor.fetchone()

                if existing_user:
                    flash('Email is already taken by another account.', 'danger')
                    return redirect(url_for('index'))

                # Update user details if email is unique
                cursor.execute("""
                    UPDATE users SET username = %s, email = %s, phone = %s, bio = %s, 
                                    ability1 = %s, ability2 = %s, ability3 = %s
                    WHERE user_id = %s
                """, (username, email, phone, bio, ability1, ability2, ability3, user_id))

                connection.commit()

                flash('Account updated successfully!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                connection.rollback()
                flash(f'Error updating account: {str(e)}', 'danger')
            finally:
                connection.close()

            return redirect(url_for('account'))
    else:
        return redirect(url_for('login'))


@app.route('/index')
def index():
    if 'loggedin' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/create')
def create():
    if 'loggedin' in session:
        return render_template('create.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/createteam', methods=['GET', 'POST'])
def createteam():
    if 'loggedin' in session:
        action_type = request.form.get('action_type')
        if action_type == 'create-naja':
            username = session['username']
            team_name = request.form.get('team_name') 
            players = [
                request.form.get(f'player{i}') for i in range(1, 12)
            ]
            substitutes = [
                request.form.get(f'sub{i}') for i in range(1, 6)
            ]
            description = request.form.get('description')

            team_data = {
                'players': players,
                'substitutes': substitutes
            }

            connection = get_db_connection()
            cursor = connection.cursor()
            try:
                cursor.execute("""
                    INSERT INTO create_team (owner, team_name, teamdata, description)
                    VALUES (%s, %s, %s, %s)
                """, (username, team_name, json.dumps(team_data), description))

                connection.commit()
                flash('Team created successfully!', 'success')
            except Exception as e:
                connection.rollback()
                flash(f'Error creating team: {str(e)}', 'danger')
            finally:
                connection.close()
            return redirect(url_for('join')) 

    else:
        return redirect(url_for('login'))



@app.route('/viewteam', methods=['GET', 'POST'])
def viewteam():
    if 'loggedin' in session:
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

        return render_template('viewteam.html', teams=teams, username=session['username'])
    
    else:
        return redirect(url_for('login'))


@app.route('/sport')
def sport():
    if 'loggedin' in session:
        return render_template('sport.html', username=session['username'])
    else:
        return redirect(url_for('login' , username=session['username']))


@app.route('/join')
def join():
    if 'loggedin' in session:
        username = session['username']

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Fetch the team data for the logged-in user
            cursor.execute("""
                SELECT owner, team_name, teamdata, description 
                FROM create_team 
                WHERE owner = %s
            """, (username,))
            team = cursor.fetchone()

            if team:
                # Parse the teamdata from JSON format
                teamdata = json.loads(team[2])  # team[2] corresponds to the 'teamdata' column

                # Pass the team data to the template
                return render_template('join.html', 
                                       username=session['username'],
                                       team_name=team[1],
                                       teamdata=teamdata,
                                       description=team[3])
            else:
                flash('No team found for this user.', 'danger')
                return redirect(url_for('create'))  # Redirect to create team if none found
        except Exception as e:
            flash(f'Error fetching team data: {str(e)}', 'danger')
            return redirect(url_for('login'))
        finally:
            connection.close()
    else:
        return redirect(url_for('login'))

@app.route('/account')
def account():
    if 'loggedin' in session:
        user_id = session['user_id']

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Wrap user_id in a tuple
            cursor.execute("SELECT username, email, phone, bio, ability1, ability2, ability3 FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return render_template('account.html', user=user, username=session['username'])
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error fetching account details: {str(e)}', 'danger')
            return redirect(url_for('login'))
        finally:
            connection.close()
    else:
        return redirect(url_for('login'))



# Route for logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
