# app.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import base64
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Store player info in memory
players = {}
current_buzzer = None

# Ensure uploads directory exists
if not os.path.exists('static/uploads'):
    os.makedirs('static/uploads')


@app.route('/')
def index():
    return render_template('player.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    player_name = data['name']
    image_data = data['image'].split(',')[1]  # Remove data URL prefix

    # Save image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"player_{timestamp}.png"
    filepath = os.path.join('static/uploads', filename)

    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(image_data))

    # Store player info
    players[request.remote_addr] = {
        'name': player_name,
        'image': f'/static/uploads/{filename}'
    }

    return jsonify({'status': 'success'})


@socketio.on('buzz')
def handle_buzz():
    global current_buzzer
    if current_buzzer is None and request.remote_addr in players:
        current_buzzer = request.remote_addr
        player = players[current_buzzer]
        emit('buzz_received', {
            'name': player['name'],
            'image': player['image']
        }, broadcast=True)


@socketio.on('reset_buzzer')
def reset_buzzer():
    global current_buzzer
    current_buzzer = None
    emit('buzzer_reset', broadcast=True)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)