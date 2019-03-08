import requests, json
from rq import get_current_job

class Group:
  def __init__(self, name, image, id):
    self.name = name
    self.image = image if image else "https://i.groupme.com/300x300.png.e8ec5793a332457096bc9707ffc9ac37.avatar"
    self.id = id
  
  def __repr__(self):
    return '<Group: {}>'.format(self.name)

class API:
  def __init__(self, token):
    self.token = token
    self.base = 'https://api.groupme.com/v3{}'
    self.headers = {'X-Access-Token' : self.token}    

  def groups(self):
    r = requests.get(self.base.format('/groups?per_page=100&omit=memberships'), headers=self.headers)
    groups = r.json().get('response')

    groups_out = []
    for group in groups:
      name = group.get('name')
      image = group.get('image_url')
      id = group.get('id')
      groups_out.append(Group(name,image,id))
    return groups_out

  def messages(self, group_id):
    job = get_current_job()

    r = requests.get(self.base.format('/groups/{}/messages'.format(group_id)), headers=self.headers)
    messages = r.json().get('response').get('messages')
    total_messages = r.json().get('response').get('count')
    before_id = messages[-1]['id']

    while r.status_code == 200:
      job.meta['progress'] = len(messages) / total_messages
      job.save_meta()
      r = requests.get(self.base.format('/groups/{}/messages?before_id={}'.format(group_id, before_id)), headers=self.headers)
      if r.status_code != 304:
        messages += r.json().get('response').get('messages')
        before_id = messages[-1]['id']
    
    return messages

  def analyze_group(self, group_id):
    messages = self.messages(group_id)

    return dict(messages=len(messages))

    
