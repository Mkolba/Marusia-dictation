# -*- coding: utf-8 -*-
from aiohttp import web
from utils import json_serial, BetterDict, prepare_text, prepare_tts, incline, is_stop_word
from random import choice
import json


with open('./pictures.json', 'r', encoding='utf-8') as f:
    pictures = json.load(f)


class Handler(web.View):
    async def post(self):

        data = BetterDict.loads(await self.request.text())
        self.session = data.session
        state = data.state.session
        print(data.request.command)

        if self.session.new:
            text = 'Привет! Готов порисовать? Подготовь карандаш и листочек в клеточку и скажи: «^Начать^».'
            return self.response(text, text, buttons=[{"title": "Начать"}], state={"stage": "start"})

        elif is_stop_word(data.request.command) or 'on_interrupt' in data.request.command:
            text = 'Поняла. До скорых встреч!'
            return self.response(text, text, end=True)

        elif state.stage == 'start':
            if 'нет' in data.request.command or 'не хочу' in data.request.command:
                text = 'Поняла. До скорых встреч!'
                return self.response(text, text, end=True)
            if data.state.user.picture:
                picture = str(int(data.state.user.picture) + 1)
            elif state.picture:
                picture = str(int(state.picture) + 1)
            else:
                picture = '1'

            if picture not in pictures:
                picture = '1'

            start = pictures[picture]['start']
            text = f'Отлично, начинаем! Отступи {start[0]} {incline(start[0])} вниз и {start[1]} {incline(start[1])} вправо, а потом скажи: «Начать».'
            return self.response(text, text, state={"stage": "drawing", "step": 0, "picture": picture},
                                 buttons=[{'title': 'Готов'}])

        elif state.stage == 'drawing':
            picture = pictures[state.picture]['moves']

            if state.step == 0:
                text = f'Хорошо. Нарисуй {picture[state.step]} и скажи: «Дальше».'

            elif 'повтор' in data.request.command:
                text = f'Повторяю - нарисуй {picture[state.step - 1]}.'
                return self.response(text, text, state={"stage": "drawing", "step": state.step, "picture": state.picture},
                                     buttons=[{'title': 'Дальше'}, {'title': 'Повтори'}])
            else:
                if state.step < len(picture):
                    text = choice([f'Теперь нарисуй {picture[state.step]}.', f'Нарисуй {picture[state.step]}.'])
                else:
                    if 'screen' in data.meta.interfaces:
                        text = f'Поздравляю! Рисунок «{pictures[state.picture]["name"]}» завершён. Вот что должно было получиться. Нарисуем что-нибудь ещё?'
                        tts = f'<speaker audio=\"marusia-sounds/game-win-2\"> Поздравляю! Рисунок «{pictures[state.picture]["name"]}» завершён. Вот что должно было получиться. Нарисуем что-нибудь ещё?'
                    else:
                        text = f'Поздравляю! Рисунок «{pictures[state.picture]["name"]}» завершён. Нарисуем что-нибудь ещё?'
                        tts = f'<speaker audio=\"marusia-sounds/game-win-2\"> Поздравляю! Рисунок «{pictures[state.picture]["name"]}» завершён. Нарисуем что-нибудь ещё?'
                    return self.response(text, tts,
                                         state={"stage": "start", "picture": state.picture}, perm_state={"picture": state.picture},
                                         buttons=[{'title': 'Давай!'}], image=pictures[state.picture]["photo"])

            return self.response(text, text, state={"stage": "drawing", "step": state.step + 1, "picture": state.picture},
                                 buttons=[{'title': 'Дальше'}, {'title': 'Повтори'}])

        else:
            text = 'Привет! Готов порисовать? Подготовь карандаш и листочек в клеточку и скажи: «^Начать^».'
            return self.response(text, text, buttons=[{"title": "Начать"}], state={"stage": "start"})

    def response(self, text, tts="", end=False, state=None, buttons=None, jsonify=True, perm_state=None, image=None):
        data = {
            "response": {
                "end_session": end,
                "text": prepare_text(text),
                "tts": prepare_tts(tts)
            },
            "session": {
                "session_id": self.session.session_id,
                "user_id": self.session.application.application_id,
                "message_id": self.session.message_id
            },
            "version": "1.0"
        }

        if state:
            data.update({"session_state": state})

        if perm_state:
            data.update({"user_state_update": perm_state})

        if buttons:
            data["response"].update({'buttons': buttons})

        if image:
            data["response"].update({'card': {"type": "BigImage", "image_id": image}})
        resp = web.Response(body=(json.dumps(data, default=json_serial)) if jsonify else data)
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = 'application/json'
        return resp
