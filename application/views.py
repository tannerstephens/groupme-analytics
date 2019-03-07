from flask import current_app, Blueprint, render_template

views = Blueprint('views', __name__)

@views.route('/')
def index():
  return render_template('views/index.html')
