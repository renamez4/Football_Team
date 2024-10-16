from flask import Flask, request, render_template, redirect, url_for, flash, session
import mysql.connector
import os
from dotenv import load_dotenv
import bcrypt
import json
import random
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
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['phone'] = user['phone']
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

            positions = [
                {
                    'position': request.form.get(f'position{i}'),
                    'player_name': request.form.get(f'player_name{i}')
                } 
                for i in range(1, 12)
            ]
            substitutes = [
                {
                    'position': request.form.get(f'sub{i}'),
                    'player_name': request.form.get(f'sub_player_name{i}')
                } 
                for i in range(1, 6)
            ]

            description = request.form.get('description')

            # Prepare data for the team
            team_data = {
                'positions': positions,
                'substitutes': substitutes
            }

            # Database interaction
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
        return redirect(url_for('login'))

@app.route('/join', methods=['GET', 'POST'])
def join():
    if 'loggedin' in session:
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Fetch all team names
            cursor.execute("SELECT team_name FROM create_team")
            teams = cursor.fetchall()  # Fetch all teams for the sidebar
            
            # Fetch user's abilities from the `users` table
            cursor.execute("""
                SELECT ability1, ability2, ability3 
                FROM users 
                WHERE username = %s
            """, (session['username'],))
            user_abilities = cursor.fetchone()

            if not user_abilities or all(ability is None for ability in user_abilities):
                flash('User abilities not found or empty.', 'danger')
                return redirect(url_for('join'))

            position_map = {
                'GK': 'Goalkeeper',
                'RB': 'Right Back',
                'RWB': 'Right Wing Back',
                'CB': 'Center Back',
                'LB': 'Left Back',
                'LWB': 'Left Wing Back',
                'RAM': 'Right Attacking Midfielder',
                'RM': 'Right Midfielder',
                'CM': 'Central Midfielder',
                'CDM': 'Defensive Midfielder',
                'LM': 'Left Midfielder',
                'LAM': 'Left Attacking Midfielder',
                'CAM': 'Attacking Midfielder',
                'ST': 'Striker',
                'CF': 'Center Forward',
                'RW': 'Right Winger',
                'LW': 'Left Winger',
            }

            # Randomly select one ability, ensuring there are valid options
            valid_abilities = [ability for ability in user_abilities if ability]
            selected_ability = random.choice(valid_abilities) if valid_abilities else None

            # Map selected ability to its full name
            selected_position = position_map.get(selected_ability, selected_ability)

            # Handle form submission if a team is selected
            if request.method == 'POST':
                selected_team = request.form.get('team_name')
                position = request.form.get('position')  # This will be the selected random ability

                # Update team with the user's position
                cursor.execute("""
                    UPDATE create_team
                    SET teamdata = JSON_SET(teamdata, '$.positions[0].player_name', %s)
                    WHERE team_name = %s
                """, (session['username'], selected_team))

                connection.commit()
                flash('Position assigned and saved successfully!', 'success')
                return redirect(url_for('join'))

            # If a specific team is selected, fetch its data
            selected_team = request.args.get('team_name', None)
            if selected_team:
                cursor.execute("""
                    SELECT owner, team_name, teamdata, description 
                    FROM create_team 
                    WHERE team_name = %s
                """, (selected_team,))
                team = cursor.fetchone()

                if team:
                    teamdata = json.loads(team[2])
                    return render_template('join.html', 
                                           username=session['username'],
                                           phone=session['phone'],
                                           teams=teams,
                                           team_name=team[1],
                                           teamdata=teamdata,
                                           description=team[3],
                                           selected_ability=selected_ability,
                                           selected_position=selected_position)  # Pass the full position name
                else:
                    flash('Selected team not found.', 'danger')
                    return redirect(url_for('join'))
            else:
                return render_template('join.html', 
                                       username=session['username'], 
                                       teams=teams,
                                       selected_ability=selected_ability,
                                       selected_position=selected_position)  # Pass the full position name

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
