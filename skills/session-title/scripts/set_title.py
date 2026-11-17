import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time

if len(sys.argv) != 2:
    raise SystemExit('사용법: set_title.py \"업무 제목\"')
pid = os.getppid()
env = dict(os.environ)
while pid > 1:
    row = subprocess.check_output(['ps', '-p', str(pid), '-o', 'ppid='], text=True).strip()
    raw = subprocess.check_output(['ps', 'eww', '-p', str(pid), '-o', 'command='], text=True).strip()
    values = dict(re.findall(r'(?:^| )([A-Za-z_][A-Za-z_0-9]*)=(.*?)(?= [A-Za-z_][A-Za-z_0-9]*=|$)', raw))
    if values.get('ORCA_TERMINAL_HANDLE'):
        for key, value in values.items():
            if key.startswith('ORCA_') or key in ('CODEX_HOME', 'CODEX_THREAD_ID', 'CLAUDE_CONFIG_DIR'):
                env.setdefault(key, value)
        break
    pid = int(row)
os.environ.update(env)
if not env.get('ORCA_TERMINAL_HANDLE'):
    raise SystemExit('현재 Orca 연결을 확인하지 못했습니다. 대화가 실행 중인 터미널에서 실행하세요')
orca = str(Path(env['ORCA_CLI_BIN_DIR']) / 'orca') if env.get('ORCA_CLI_BIN_DIR') else 'orca'
title = sys.argv[1]
if not title.strip() or any(ord(c) < 32 for c in title):
    raise SystemExit('제목은 비어 있지 않은 한 줄이어야 합니다')

def cli(*args):
    result = subprocess.run([orca, *args, '--json'], capture_output=True, text=True, timeout=20)
    data = json.loads(result.stdout)
    if result.returncode or not data.get('ok'):
        raise RuntimeError(data)
    return data['result']

def listed():
    data = cli('terminal', 'list')
    if data.get('truncated'):
        raise RuntimeError('터미널 목록이 잘렸습니다')
    return data

def entries():
    return json.loads(status_path.read_text())['entries']

def session(terminal):
    entry = entries().get(terminal['tabId'] + ':' + terminal['leafId'], {})
    value = entry.get('providerSession') or {}
    presence = entry.get('agentPresence') or {}
    if not value and presence.get('agent') == 'claude' and presence.get('sessionOwner'):
        session_id = presence.get('session')
        config = os.environ.get('ORCA_CLAUDE_CONFIG_DIR') or os.environ.get('CLAUDE_CONFIG_DIR')
        if session_id and config:
            paths = list((Path(config) / 'projects').glob('*/' + session_id + '.jsonl'))
            if len(paths) == 1:
                value = {'id': session_id, 'transcriptPath': str(paths[0])}
    if not value and terminal.get('agentIdentity') == 'codex':
        home = Path(os.environ.get('CODEX_HOME') or os.environ.get('ORCA_CODEX_HOME') or str(Path.home() / '.codex'))
        brief = '개발자 Claude 창 handle은 ' + claude['handle'] + ' 이다.'
        matches = []
        for path in (home / 'sessions').glob('**/rollout-*.jsonl'):
            with path.open() as stream:
                first = stream.readline()
                if not first:
                    continue
                meta = json.loads(first).get('payload', {})
                if meta.get('cwd') != terminal['worktreePath']:
                    continue
                for line in stream:
                    item = json.loads(line)
                    payload = item.get('payload', {})
                    if item.get('type') == 'response_item' and payload.get('role') == 'user':
                        text = ''.join(c.get('text', '') for c in payload.get('content', []))
                        if text.startswith(('너는 PM이다.', '너는 이 worktree의 PM이다.')):
                            if brief in text:
                                matches.append({'id': meta['id'], 'transcriptPath': str(path)})
                            break
        if len(matches) == 1:
            value = matches[0]
    if not value.get('id') or not value.get('transcriptPath'):
        raise RuntimeError('대화 연결 기록이 없거나 후보가 여럿입니다: ' + terminal['handle'])
    return value

def claude_name():
    path = Path(claude_session['transcriptPath'])
    name = None
    if path.exists():
        for line in path.read_text().splitlines():
            item = json.loads(line)
            if item.get('type') == 'custom-title' and item.get('sessionId') == claude_session['id']:
                name = item.get('customTitle')
    return name

def request(server, number, method, params):
    server.stdin.write(json.dumps({'id': number, 'method': method, 'params': params}) + '\n')
    server.stdin.flush()
    for line in server.stdout:
        response = json.loads(line)
        if response.get('id') == number:
            if 'error' in response:
                raise RuntimeError(response['error'])
            return response['result']
    raise RuntimeError('Codex 서버 연결이 끊겼습니다')

def timeout(signum, frame):
    raise TimeoutError('이름 변경 확인 시간이 초과됐습니다')

try:
    data = listed()
    current = [t for t in data['terminals'] if t['handle'] == os.environ['ORCA_TERMINAL_HANDLE']]
    if len(current) != 1 or current[0].get('orphaned'):
        raise RuntimeError('현재 터미널을 확인하지 못했습니다')
    current = current[0]
    if os.environ.get('ORCA_TAB_ID', current['tabId']) != current['tabId']:
        raise RuntimeError('현재 탭 식별자가 맞지 않습니다')
    if current.get('executionHostId') != 'local':
        raise RuntimeError('대화가 실행 중인 머신에서 실행하세요')
    root = os.environ.get('ORCA_USER_DATA_PATH')
    if not root:
        raise RuntimeError('Orca 기록 경로를 확인하지 못했습니다')
    status_path = Path(root) / 'agent-hooks/last-status.json'
    peers = [t for t in data['terminals'] if t['tabId'] == current['tabId']]
    for terminal in peers:
        if terminal.get('agentIdentity'):
            continue
        presence = entries().get(terminal['tabId'] + ':' + terminal['leafId'], {}).get('agentPresence') or {}
        process = presence.get('process') or {}
        if presence.get('sessionOwner') and presence.get('agent') == 'claude' and process.get('pid'):
            raw = subprocess.check_output(['ps', 'eww', '-p', str(process['pid']), '-o', 'command='], text=True).strip()
            values = dict(re.findall(r'(?:^| )([A-Za-z_][A-Za-z_0-9]*)=(.*?)(?= [A-Za-z_][A-Za-z_0-9]*=|$)', raw))
            command = subprocess.check_output(['ps', '-p', str(process['pid']), '-o', 'comm='], text=True).strip()
            if Path(command).name == 'claude' and values.get('ORCA_TERMINAL_HANDLE') == terminal['handle']:
                terminal['agentIdentity'] = 'claude'
    if len(peers) != 2 or sorted(t.get('agentIdentity', '') for t in peers) != ['claude', 'codex']:
        raise RuntimeError('현재 탭에 Claude와 Codex가 하나씩 있어야 합니다')
    claude = next(t for t in peers if t['agentIdentity'] == 'claude')
    codex = next(t for t in peers if t['agentIdentity'] == 'codex')
    if current['handle'] != codex['handle']:
        raise RuntimeError('Claude의 실행 중인 턴에서는 이름 저장을 확인할 수 없습니다. 연결된 Codex에서 실행하세요')
    claude_session, codex_session = session(claude), session(codex)
    thread_id = codex_session['id']
    if os.environ.get('CODEX_THREAD_ID', thread_id) != thread_id:
        raise RuntimeError('현재 Codex 대화와 탭의 대화가 다릅니다')
    transcript = Path(codex_session['transcriptPath'])
    meta = json.loads(transcript.open().readline())['payload']
    if meta.get('id') != thread_id or meta.get('cwd') != codex['worktreePath']:
        raise RuntimeError('Codex 대화 기록과 연결 정보가 다릅니다')
    homes = [p.parent for p in transcript.parents if p.name == 'sessions']
    if len(homes) != 1:
        raise RuntimeError('Codex 저장 경로를 확인하지 못했습니다')
    env = {**os.environ, 'CODEX_HOME': str(homes[0])}
    signal.signal(signal.SIGALRM, timeout)
    server = subprocess.Popen(['codex', 'app-server', '--stdio'], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        signal.alarm(50)
        request(server, 1, 'initialize', {'clientInfo': {'name': 'session-title', 'version': '1'}})
        server.stdin.write(json.dumps({'method': 'initialized'}) + '\n')
        server.stdin.flush()
        before = request(server, 2, 'thread/read', {'threadId': thread_id, 'includeTurns': False})['thread']
        print(json.dumps({'before': {'claude': claude_name(), 'codex': before.get('name')}, 'tabId': current['tabId'], 'claudeSessionId': claude_session['id'], 'codexThreadId': thread_id}, ensure_ascii=False), flush=True)
        cli('terminal', 'read', '--terminal', claude['handle'], '--screen')
        if claude_name() != title:
            cli('terminal', 'send', '--terminal', claude['handle'], '--text', '/rename ' + title, '--enter')
            deadline = time.monotonic() + 12
            while claude_name() != title:
                if session(claude)['id'] != claude_session['id']:
                    raise RuntimeError('Claude 대화가 바뀌었습니다')
                if time.monotonic() > deadline:
                    raise RuntimeError('Claude 이름 저장 미확인; 입력을 다시 보내지 않았습니다')
                time.sleep(0.25)
        print('Claude 대화: 저장 확인 ' + claude_session['id'], flush=True)
        request(server, 3, 'thread/name/set', {'threadId': thread_id, 'name': title})
        after = request(server, 4, 'thread/read', {'threadId': thread_id, 'includeTurns': False})['thread']
        if after.get('name') != title:
            raise RuntimeError('Codex 이름 저장 미확인')
        print('Codex 대화: 저장 확인 ' + thread_id, flush=True)
        if session(claude)['id'] != claude_session['id'] or session(codex)['id'] != thread_id:
            raise RuntimeError('이름 변경 중 대화 연결이 바뀌었습니다')
    finally:
        signal.alarm(0)
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
except Exception as error:
    print('제목 변경 실패 (일부 이름이 바뀌었을 수 있음): ' + str(error), file=sys.stderr)
    sys.exit(1)
