import os
import json
import random
import string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# MongoDB connection
client = MongoClient(os.environ.get('MONGO_URI', ''))
db = client['orion']

# Collections
users_col = db['users']
quizzes_col = db['quizzes']
questions_col = db['questions']
options_col = db['options']
sessions_col = db['sessions']
participants_col = db['participants']
responses_col = db['responses']

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def index(request):
    return render(request, 'index.html')

def host_page(request):
    return render(request, 'host.html')

def join_page(request):
    return render(request, 'join.html')

def play_page(request):
    return render(request, 'play.html')

def leaderboard_page(request):
    return render(request, 'leaderboard.html')

def health(request):
    return JsonResponse({'message': '🚀 Orion Django API is running!'})

@csrf_exempt
@require_http_methods(['POST'])
def create_quiz(request):
    try:
        data = json.loads(request.body)
        quiz = {
            'title': data['title'],
            'description': data.get('description', ''),
            'host_id': data.get('host_id', 'host'),
            'created_at': datetime.utcnow()
        }
        result = quizzes_col.insert_one(quiz)
        return JsonResponse({
            'quiz_id': str(result.inserted_id),
            'title': quiz['title']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def bulk_questions(request):
    try:
        data = json.loads(request.body)
        quiz_id = data['quiz_id']
        questions = data['questions']

        for i, q in enumerate(questions):
            question = {
                'quiz_id': quiz_id,
                'question_text': q['question_text'],
                'question_type': q['question_type'],
                'time_limit_seconds': q.get('time_limit_seconds', 30),
                'points': q.get('points', 10),
                'order_num': i + 1,
                'options': []
            }

            if q['question_type'] != 'open_ended' and 'options' in q:
                for opt in q['options']:
                    if opt['text'].strip():
                        question['options'].append({
                            'option_id': str(ObjectId()),
                            'option_text': opt['text'],
                            'is_correct': opt.get('is_correct', False)
                        })

            questions_col.insert_one(question)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def create_session(request):
    try:
        data = json.loads(request.body)
        session = {
            'quiz_id': data['quiz_id'],
            'join_code': data['join_code'],
            'status': 'waiting',
            'started_at': None,
            'ended_at': None,
            'created_at': datetime.utcnow()
        }
        result = sessions_col.insert_one(session)
        return JsonResponse({
            'session_id': str(result.inserted_id),
            'join_code': session['join_code']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_session(request, join_code):
    try:
        session = sessions_col.find_one({'join_code': join_code.upper()})
        if not session:
            return JsonResponse({'error': 'Session not found'}, status=404)
        return JsonResponse({
            'session_id': str(session['_id']),
            'join_code': session['join_code'],
            'status': session['status'],
            'quiz_id': session['quiz_id']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def session_status(request, join_code):
    try:
        session = sessions_col.find_one({'join_code': join_code.upper()})
        if not session:
            return JsonResponse({'error': 'Session not found'}, status=404)
        count = participants_col.count_documents({'session_id': str(session['_id'])})
        return JsonResponse({
            'status': session['status'],
            'participant_count': count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def start_session(request, join_code):
    try:
        sessions_col.update_one(
            {'join_code': join_code.upper()},
            {'$set': {'status': 'active', 'started_at': datetime.utcnow()}}
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_questions(request, join_code):
    try:
        session = sessions_col.find_one({'join_code': join_code.upper()})
        if not session:
            return JsonResponse({'error': 'Session not found'}, status=404)

        questions = list(questions_col.find(
            {'quiz_id': session['quiz_id']},
            sort=[('order_num', 1)]
        ))

        questions_data = []
        for q in questions:
            questions_data.append({
                'question_id': str(q['_id']),
                'question_text': q['question_text'],
                'question_type': q['question_type'],
                'time_limit_seconds': q['time_limit_seconds'],
                'points': q['points'],
                'options': q.get('options', [])
            })

        return JsonResponse({
            'session': {
                'session_id': str(session['_id']),
                'join_code': session['join_code'],
                'status': session['status']
            },
            'questions': questions_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def join_session(request):
    try:
        data = json.loads(request.body)
        username = data['username']
        join_code = data['join_code'].upper()

        session = sessions_col.find_one({'join_code': join_code})
        if not session:
            return JsonResponse({'error': 'Quiz code not found!'}, status=404)

        user = {
            'username': username,
            'email': f"{username.lower()}_{int(datetime.utcnow().timestamp())}@guest.orion",
            'role': 'participant',
            'created_at': datetime.utcnow()
        }
        user_result = users_col.insert_one(user)

        participant = {
            'session_id': str(session['_id']),
            'user_id': str(user_result.inserted_id),
            'username': username,
            'total_score': 0,
            'joined_at': datetime.utcnow()
        }
        participants_col.insert_one(participant)

        return JsonResponse({
            'success': True,
            'user_id': str(user_result.inserted_id),
            'username': username,
            'session_id': str(session['_id']),
            'join_code': join_code
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def submit_response(request):
    try:
        data = json.loads(request.body)
        session_id = data['session_id']
        question_id = data['question_id']
        user_id = data['user_id']
        option_id = data.get('option_id')
        open_answer = data.get('open_answer')

        question = questions_col.find_one({'_id': ObjectId(question_id)})
        if not question:
            return JsonResponse({'error': 'Question not found'}, status=404)

        is_correct = None
        score_awarded = 0

        if question['question_type'] == 'mcq' and option_id:
            for opt in question.get('options', []):
                if opt['option_id'] == option_id:
                    is_correct = opt.get('is_correct', False)
                    score_awarded = question['points'] if is_correct else 0
                    break

        response = {
            'session_id': session_id,
            'question_id': question_id,
            'user_id': user_id,
            'option_id': option_id,
            'open_answer': open_answer,
            'is_correct': is_correct,
            'score_awarded': score_awarded,
            'submitted_at': datetime.utcnow()
        }
        responses_col.insert_one(response)

        if score_awarded > 0:
            participants_col.update_one(
                {'session_id': session_id, 'user_id': user_id},
                {'$inc': {'total_score': score_awarded}}
            )

        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'score_awarded': score_awarded
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def leaderboard(request, join_code):
    try:
        session = sessions_col.find_one({'join_code': join_code.upper()})
        if not session:
            return JsonResponse({'error': 'Session not found'}, status=404)

        participants = list(participants_col.find(
            {'session_id': str(session['_id'])},
            sort=[('total_score', -1)]
        ))

        leaderboard_data = [{
            'username': p['username'],
            'total_score': p['total_score']
        } for p in participants]

        return JsonResponse(leaderboard_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
