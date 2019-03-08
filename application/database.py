from flask_sqlalchemy import SQLAlchemy
from flask import current_app
import redis
import rq

db = SQLAlchemy(current_app)

class Group(db.Model):
  __tablename__ = "groups"

  id = db.Column(db.Integer, primary_key=True)
  group_id = db.Column(db.Integer, unique=True)
  message_job_id = db.Column(db.String(36))

  def get_rq_job(self):
    try:
        rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
    except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
        return None
    return rq_job
