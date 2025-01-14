# app.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import base64
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Store player info and scores in memory
players = {}
scores = {}
score_limit = 0
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

    # Store player info and initialize score
    players[request.remote_addr] = {
        'name': player_name,
        'image': f'/static/uploads/{filename}'
    }
    scores[player_name] = 0

    # Broadcast updated scores to all clients
    emit('update_scores', scores, broadcast=True, namespace='/')
    return jsonify({'status': 'success'})


@socketio.on('set_score_limit')
def handle_score_limit(data):
    global score_limit
    score_limit = int(data['limit'])
    emit('score_limit_set', {'limit': score_limit}, broadcast=True)


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


@socketio.on('answer_result')
def handle_answer(data):
    global current_buzzer
    if current_buzzer and data['correct']:
        player_name = players[current_buzzer]['name']
        scores[player_name] += 1

        # Check for winner
        if score_limit > 0 and scores[player_name] >= score_limit:
            emit('game_won', {
                'name': player_name,
                'image': players[current_buzzer]['image'],
                'score': scores[player_name]
            }, broadcast=True)
        else:
            emit('update_scores', scores, broadcast=True)

    current_buzzer = None
    emit('buzzer_reset', broadcast=True)


@socketio.on('update_manual_score')
def handle_manual_score(data):
    player_name = data['player']
    new_score = int(data['score'])
    if player_name in scores:
        scores[player_name] = new_score

        # Check for winner
        if score_limit > 0 and scores[player_name] >= score_limit:
            winner_addr = next(addr for addr, p in players.items() if p['name'] == player_name)
            emit('game_won', {
                'name': player_name,
                'image': players[winner_addr]['image'],
                'score': scores[player_name]
            }, broadcast=True)
        else:
            emit('update_scores', scores, broadcast=True)


@socketio.on('reset_buzzer')
def reset_buzzer():
    global current_buzzer
    current_buzzer = None
    emit('buzzer_reset', broadcast=True)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)