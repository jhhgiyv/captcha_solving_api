from curl_cffi import requests

from captcha_solving_api.model import CaptchaSolving, GetTaskResultResponse, Task
from config import settings


class FunCaptchaServer(CaptchaSolving):

    def __init__(self, task):
        headers = {
            'Content-Type': 'application/json',
        }

        json_data = {
            'clientKey': 'your_key',
            'task': {
                'type': 'FunCaptchaClassification',
                'image': task.image,
                'question': task.question,
            },
        }
        self.data = None

        response = requests.post(f'{settings.funcaptcha_server}/createTask', headers=headers, json=json_data)
        response_data = response.json()
        if response_data.get('status') == 'ready':
            self.data = response.text
        if response_data.get('errorId', 1) == 0:
            self.taskId = response.json().get('taskId')
            return
        raise Exception(f'funcaptcha server 错误 {response.text}')

    @classmethod
    async def create_task(cls, task: Task) -> 'CaptchaSolving':
        return cls(task)

    async def get_task_result(self) -> GetTaskResultResponse:
        headers = {
            'Content-Type': 'application/json',
        }

        json_data = {
            'clientKey': 'your_key',
            'taskId': self.taskId
        }
        if self.data:
            return GetTaskResultResponse.model_validate_json(self.data)

        response = requests.post(f'{settings.funcaptcha_server}/createTask', headers=headers, json=json_data)
        return GetTaskResultResponse.model_validate_json(response.text)

    async def finalize(self):
        pass

    async def init(self):
        pass
