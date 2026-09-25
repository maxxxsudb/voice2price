"""Client for the asynchronous, unauthenticated GigaAM microservice."""
import os
import time
from pathlib import Path

import requests


def base_url():
    return os.environ.get('GIGAAM_URL', 'http://gigaam:5001').rstrip('/')


def model_name():
    return os.environ.get('GIGAAM_MODEL', 'v3_rnnt')


def submit(source):
    path = Path(source)
    with path.open('rb') as stream:
        response = requests.post(f'{base_url()}/v1/transcriptions',
                                 files={'file': (path.name, stream, 'application/octet-stream')},
                                 timeout=int(os.environ.get('GIGAAM_UPLOAD_TIMEOUT_SEC', '300')))
    response.raise_for_status()
    return response.json()['id']


def get_operation(operation_id):
    response = requests.get(f'{base_url()}/v1/operations/{operation_id}', timeout=30)
    response.raise_for_status()
    return response.json()


def wait(operation_id, timeout=None, poll_interval=None):
    timeout = timeout or float(os.environ.get('GIGAAM_WAIT_TIMEOUT_SEC', '3600'))
    poll_interval = poll_interval or float(os.environ.get('GIGAAM_POLL_INTERVAL_SEC', '0.5'))
    deadline = time.monotonic() + timeout
    while True:
        operation = get_operation(operation_id)
        if operation.get('done'):
            if operation.get('error'):
                raise RuntimeError(operation['error'].get('message') or 'GigaAM operation failed')
            return operation['response']
        if time.monotonic() >= deadline:
            raise TimeoutError(f'GigaAM operation {operation_id} exceeded {timeout:g} seconds')
        time.sleep(poll_interval)


def transcribe(source):
    response = wait(submit(source))
    return response.get('text', ''), response.get('segments', [])
