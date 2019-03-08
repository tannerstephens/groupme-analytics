from flask import current_app, Blueprint, render_template, session, redirect, flash, request, url_for, jsonify
from application.groupme import API
from application.database import db, Group

views = Blueprint('views', __name__)

@views.route('/')
def index():
  return render_template('views/index.html')

@views.route('/callback')
def callback():
  access_token = request.args.get('access_token')

  if access_token is None:
    flash('Authentication Failed')
    redirect('/')
  else:
    session['access_token'] = access_token
    print(access_token)
    return redirect(url_for('views.loggedin'))

@views.route('/analyze')
def loggedin():
  at = session.get('access_token')

  if at is None:
    return redirect('/')
  
  gapi = API(at)
  groups = gapi.groups()  
  
  return render_template('views/logged-in.html', groups=groups)

@views.route('/analyze/<int:group_id>')
def analyze(group_id):
  at = session.get('access_token')

  if at is None:
    return redirect('/')

  group = Group.query.filter_by(group_id=group_id).first()

  if group is None:
    group = Group(group_id = group_id)
    gapi = API(at)
    job = current_app.task_queue.enqueue(gapi.analyze_group, group_id, result_ttl=-1, timeout=3600)
    group.message_job_id = job.get_id()
    db.session.add(group)
    db.session.commit()
  else:
    job = group.get_rq_job()

  if job.is_finished:
    info = job.return_value
    return jsonify(info)
  else:
    return render_template('views/analysis_loading.html')

@views.route('/analyze/<group_id>/status')
def analysis_status(group_id):

  group = Group.query.filter_by(group_id=group_id).first()

  if group is None:
    return '', 404

  job = group.get_rq_job()

  return jsonify(dict(is_finished=job.is_finished, percent=job.meta.get('progress', 0)))
