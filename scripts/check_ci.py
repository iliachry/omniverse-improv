import urllib.request
import json
import time
import sys

def check_latest_run():
    url = 'https://api.github.com/repos/iliachry/omniverse-improv/actions/runs?per_page=3'
    req = urllib.request.Request(url, headers={'User-Agent': 'Antigravity'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            runs = data.get('workflow_runs', [])
            if not runs:
                print("No runs found.")
                return None
            for r in runs:
                commit_msg = r.get('head_commit', {}).get('message', '').splitlines()[0] if r.get('head_commit') else ''
                print(f"Run ID: {r['id']} | Status: {r['status']} | Conclusion: {r['conclusion']} | SHA: {r['head_sha'][:7]} | Message: {commit_msg}")
            return runs[0]
    except Exception as e:
        print("Error querying GitHub API:", e)
        return None

def monitor_run(run_id):
    url = f'https://api.github.com/repos/iliachry/omniverse-improv/actions/runs/{run_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Antigravity'})
    for _ in range(60):
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                status = data.get('status')
                conclusion = data.get('conclusion')
                print(f"Run {run_id} ({data.get('name')}): {status} | conclusion: {conclusion}")
                if status == 'completed':
                    return conclusion
        except Exception as e:
            print("Error:", e)
        time.sleep(10)
    return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        monitor_run(sys.argv[1])
    else:
        check_latest_run()
