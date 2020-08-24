from django.http import HttpResponse
import json
import vk_api
import threading
from random import randint, choice
from api.models import EducationMessage, Trigger, Picture
import mc
from urllib.request import urlopen
import requests


token = "3e0ae4055ea88392353d46bad3a1bb1a0646d467e63f9e3b45b58ac7470ed2f2fad50f8d4de1c4a3c3892"
vk = vk_api.VkApi(token=token)


class Message:
    def __init__(self, data):
        self.text = data["object"]["text"]
        self.from_id = data["object"]["from_id"]
        self.peer_id = data["object"]["peer_id"]
        if "fwd_messages" in data["objects"].keys():
            self.fwd_messages = data["objects"]["fwd_messages"]
        else:
            self.fwd_messages = None
        if "reply_message" in data["objects"].keys():
            self.reply_message = data["objects"]["reply_message"]
        else:
            self.reply_message = None
        if "attachments" in data["objects"].keys():
            self.attachments = data["objects"]["attachments"]
        else:
            self.attachments = None
        self.is_command = self.text.startswith("g")
        self.is_trigger = self.text in [trigger.trigger for trigger in Trigger.objects.all()]
        if randint(1, 2) == 1:
            EducationMessage(peer_id=self.peer_id, message=self.text).save()

    def reply(self, text='', attachment=None, peer_id=None):
        if not peer_id:
            peer_id = self.peer_id
        vk.method("messages.send", {
            "peer_id": peer_id,
            "text": text,
            "attachment": attachment,
            "random_id": randint(1, 1000000000)
        })

    def generate(self, picture=False):
        if randint(0, 100) <= 10 or picture:
            attachment = choice([picture.vk_code for picture in Picture.objects.all()])
            return {"attachment": attachment}
        else:
            text = mc.StringGenerator(
                samples=[message.message for message in EducationMessage.objects.filter(
                    peer_id=self.peer_id)]).generate_string()
            return {"text": text}


def add_picture(message):
    if message.fwd_messages:
        for _message in message.fwd_messages:
            _message = Message(_message)
            _message.from_id, _message.peer_id = message.from_id, message.peer_id
            add_picture(_message)
            del _message
    if message.reply_message:
        _message = Message(message.reply_message)
        _message.from_id, _message.peer_id = message.from_id, message.peer_id
        add_picture(_message)
    for attachment in message.attachments:
        if attachment["type"] == "photo":
            k = urlopen(attachment['photo']['sizes'][-1]['url']).read()
            a = open(str(attachment['photo']['id']) + '.jpg', 'wb')
            a.write(k)
            a.close()
            server = json.loads(requests.request('POST', vk.method(
                'photos.getMessagesUploadServer')['upload_url'],
                files={'photo': open(str(attachment['photo']['id']) + '.jpg', 'rb')}).text)
            res = vk.method('photos.saveMessagesPhoto', {'server': server['server'],
                                                         'hash': server['hash'],
                                                         'photo': server['photo']})
            vk_code = 'photo' + str(res[0]['owner_id']) + '_' + str(res[0]['id'])
            if message.from_id == 589102943:
                Picture(vk_code=vk_code, url=attachment['photo']['sizes'][-1]['url']).save()
            else:
                message.reply(text='чел тут картинку в пул добавить хотят', attachment=vk_code, peer_id=589102943)


def message_handler(data):
    message = Message(data)
    if message.is_command:
        if message.text == "g s":
            message.reply(**message.generate())
        if message.text == "g st":
            message.reply(
                text="\n|".join([f"{trigger.trigger} - {trigger.answer}" for trigger in Trigger.objects.all()]))
        if message.text == "g i":
            message.reply(text=f"сохранено {len(EducationMessage.objects.all())} сообщений из беседы")
        if message.text == "g sp":
            message.reply(**message.generate(picture=True))
        if message.text == "g ap":
            add_picture(message)
    elif message.is_trigger:
        message.reply(text=Trigger.objects.filter(trigger=message.text)[0].answer)

    elif randint(0, 100) <= 5:
        message.reply(**message.generate())

    del message


def api(request):
    data = json.loads(request.body)
    if data["type"] == "message_new":
        threading.Thread(target=message_handler, args=(data,)).start()
        return HttpResponse("ok")
