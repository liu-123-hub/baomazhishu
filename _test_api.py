import requests, json, sys

base = 'http://127.0.0.1:8765/api'
errors = []

def test(name, method, path, **kwargs):
    try:
        r = getattr(requests, method)(base + path, timeout=15, **kwargs)
        try:
            j = r.json()
            code = j.get('code', 'no-code')
        except:
            code = 'non-json'
            j = None
        ok = r.status_code == 200 and code in (200, 409)
        status = "PASS" if ok else "FAIL"
        print(f'  [{status}] {name}: HTTP {r.status_code}, code={code}')
        if not ok:
            errors.append((name, r.status_code, code))
        return j
    except Exception as e:
        print(f'  [FAIL] {name}: ERROR {e}')
        errors.append((name, 'ERR', str(e)[:80]))
        return None

print('=== API Endpoint Verification ===')
test('Overview', 'get', '/dashboard/overview')
test('Sector Detail (bank)', 'get', '/dashboard/sector-detail', params={'code':'bank'})
test('Line Chart 7d', 'get', '/dashboard/line-chart', params={'sectors':'bank,gold,semi','days':7})
test('Line Chart 30d', 'get', '/dashboard/line-chart', params={'sectors':'bank','days':30})
test('Market Data', 'get', '/dashboard/market-data')
test('Capital Flow', 'get', '/dashboard/capital-flow')
test('ETF Correlation', 'get', '/dashboard/etf-correlation', params={'sector':'bank','days':30})
test('Health', 'get', '/system/health')
test('Status', 'get', '/system/status')
test('Cache Stats', 'get', '/cache/stats')
test('Audit Logs', 'get', '/system/audit-logs', params={'limit':5})
test('Collect Trigger (409 expected)', 'post', '/system/collect/trigger')

print()
j = test('Overview Data Integrity', 'get', '/dashboard/overview')
if j and j.get('data'):
    d = j['data']
    print(f'  avg_index: {d.get("avg_index")}')
    print(f'  sector_count: {d.get("sector_count")}')
    print(f'  valid_sector_count: {d.get("valid_sector_count")}')
    print(f'  is_real_data: {d.get("is_real_data")}')
    sectors = d.get('sectors', {})
    degraded = [k for k,v in sectors.items() if v.get('is_degraded')]
    print(f'  degraded: {len(degraded)}/{len(sectors)}')
    dq = d.get('data_quality', {})
    print(f'  data_quality: {json.dumps(dq, ensure_ascii=False)[:300]}')

print()
if errors:
    print(f'=== {len(errors)} FAILURES ===')
    for e in errors:
        print(f'  - {e[0]}: HTTP {e[1]}, code={e[2]}')
    sys.exit(1)
else:
    print('=== ALL API TESTS PASSED ===')
