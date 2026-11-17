import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class TitleTest(unittest.TestCase):
    def test_pair_rename_from_codex_only(self):
        script = Path(__file__).with_name('set_title.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claude_path = root / 'claude.jsonl'
            codex_path = root / 'sessions/rollout.jsonl'
            codex_path.parent.mkdir()
            codex_path.write_text(json.dumps({'payload': {'id': 'codex-id', 'cwd': directory}}) + '\n')
            terminals = [{'handle': 'term-' + agent, 'tabId': 'tab', 'leafId': agent, 'agentIdentity': agent, 'executionHostId': 'local', 'worktreePath': directory} for agent in ('claude', 'codex')]
            status = root / 'agent-hooks/last-status.json'
            status.parent.mkdir()
            status.write_text(json.dumps({'entries': {'tab:' + agent: {'providerSession': {'id': agent + '-id', 'transcriptPath': str(path)}} for agent, path in [('claude', claude_path), ('codex', codex_path)]}}))
            for caller in ('codex', 'claude'):
                with self.subTest(caller=caller):
                    claude_path.write_text('')
                    sent = []
                    def cli(args, **kwargs):
                        if args[1:3] == ['terminal', 'list']:
                            result = {'terminals': terminals}
                        else:
                            result = {}
                        if args[1:3] == ['terminal', 'send']:
                            sent.append(args)
                            claude_path.write_text(json.dumps({'type': 'custom-title', 'sessionId': 'claude-id', 'customTitle': '테스트 제목'}) + '\n')
                        return subprocess.CompletedProcess(args, 0, json.dumps({'ok': True, 'result': result}))
                    replies = [{'id': 1, 'result': {}}, {'id': 2, 'result': {'thread': {'name': 'before'}}}, {'id': 3, 'result': {}}, {'id': 4, 'result': {'thread': {'name': '테스트 제목'}}}]
                    class Server:
                        stdin = io.StringIO()
                        stdout = io.StringIO(''.join(json.dumps(r) + '\n' for r in replies))
                        def terminate(self):
                            pass
                        def wait(self, **kwargs):
                            return 0
                    server = Server()
                    env = {'ORCA_TERMINAL_HANDLE': 'term-' + caller, 'ORCA_USER_DATA_PATH': directory, 'ORCA_CLI_BIN_DIR': directory, 'CODEX_THREAD_ID': 'codex-id'}
                    with patch.dict(os.environ, env, clear=True), patch('sys.argv', [str(script), '테스트 제목']), patch('os.getppid', return_value=1), patch('subprocess.run', side_effect=cli), patch('subprocess.Popen', return_value=server) as popen, patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
                        if caller == 'claude':
                            with self.assertRaises(SystemExit):
                                runpy.run_path(str(script), run_name='__main__')
                            self.assertEqual(sent, [])
                            popen.assert_not_called()
                        else:
                            runpy.run_path(str(script), run_name='__main__')
                            self.assertEqual(len(sent), 1)
                            methods = [json.loads(line)['method'] for line in server.stdin.getvalue().splitlines()]
                            self.assertEqual(methods, ['initialize', 'initialized', 'thread/read', 'thread/name/set', 'thread/read'])


if __name__ == '__main__':
    unittest.main()
