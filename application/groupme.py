import requests, json
from rq import get_current_job

class Group:
  def __init__(self, name, image, id):
    self.name = name
    self.image = image if image else "https://i.groupme.com/300x300.png.e8ec5793a332457096bc9707ffc9ac37.avatar"
    self.id = id

class Member:
  def __init__(self, name, image, id):
    self.name = name
    self.image = image if image else "https://i.groupme.com/300x300.png.e8ec5793a332457096bc9707ffc9ac37.avatar"
    self.id = id

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

  def group_name(self, group_id):
    r = requests.get(self.base.format('/groups/{}'.format(group_id)), headers=self.headers)
    group_name = r.json().get('response').get('name')
    return group_name

  def members(self, group_id):
    r = requests.get(self.base.format('/groups/{}/members?filter=active'.format(group_id)), headers=self.headers)
    members = r.json().get('response').get('memberships')

    members_out = []

    for member in members:
      name = member.get('name')
      image = member.get('image_url')
      id = member.get('user_id')
      members_out.append(Member(name, image, id))

    return members_out

  def authorized(self, group_id):
    r = requests.get(self.base.format('/groups/{}'.format(group_id)), headers=self.headers)

    return r.status_code == 200


  def messages(self, group_id, job):
    r = requests.get(self.base.format('/groups/{}/messages'.format(group_id)), headers=self.headers)
    messages = r.json().get('response').get('messages')
    total_messages = r.json().get('response').get('count')
    before_id = messages[-1]['id']

    while r.status_code == 200:
      try:
        job.meta['progress'] = len(messages) / total_messages
        job.save_meta()
        r = requests.get(self.base.format('/groups/{}/messages?before_id={}'.format(group_id, before_id)), headers=self.headers)
        if r.status_code != 304:
          messages += r.json().get('response').get('messages')
          before_id = messages[-1]['id']
      except:
        pass
    
    return messages

  def analyze_group(self, group_id):
    job = get_current_job()
    messages = self.messages(group_id, job)
    members = self.members(group_id)
    group_name = self.group_name(group_id)
    members_dict = [dict(name=member.name, image=member.image, id = member.id) for member in members]

    analysis = dict(members=members_dict, num_messages=len(messages), name=group_name)

    likes = dict(total=0)
    words = dict(total=0)
    best_post = dict()
    best_image = dict()
    for member in members:
      likes[member.id] = {'total':0}
      words[member.id] = 0
      best_post[member.id] = dict(text=None, likes=-1)
      best_image[member.id] = dict(image=None, likes=-1, text=None)
      for member2 in members:
        likes[member.id][member2.id] = 0

    for message in messages:
      try:
        sender_id = message['sender_id']
        sender_type = message['sender_type']
        if sender_id == 'system' or sender_type == 'bot':
          continue
        else:
          num_fav = len(message['favorited_by'])
          if 'image' in map(lambda x: x['type'], message['attachments']):
            if (best_image[sender_id]['likes'] < num_fav):
              best_image[sender_id]['likes'] = num_fav
              best_image[sender_id]['image'] = list(filter(lambda x: x['type'] == 'image', message['attachments']))[0]['url']
              best_image[sender_id]['image'] = message['text']
          else:
            if best_post[sender_id]['likes'] < num_fav:
              best_post[sender_id]['likes'] = num_fav
              best_post[sender_id]['text'] = message['text']


          favorites = message.get('favorited_by')
          if favorites is None:
            favorites = []
          
          for favorite in favorites:
            try:
              likes[sender_id][favorite] += 1
              likes[sender_id]['total'] += 1
              likes['total'] += 1
            except Exception:
              pass

          text = message.get('text')
          if text is None:
            text = ""


          n_words = len(text.split())
          words[sender_id] += n_words
          words['total'] += n_words
      except Exception as e:
        print(e)
        pass


    analysis['likes'] = likes
    analysis['words'] = words
    analysis['best_posts'] = best_post
    analysis['best_images'] = best_image

    job.meta['progress'] = 1
    job.save_meta()
    return analysis

    
