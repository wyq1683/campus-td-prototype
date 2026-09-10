import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute

CODE = r'''
import bpy, json
names=[o.name for o in bpy.data.objects]
# show counts by prefix
import collections
pref=collections.Counter()
for n in names:
    key=n.split('_')[0] if '_' in n else n
    pref[key]+=1
print('TOTAL',len(names))
print('PRE:',dict(pref))
# show anything with Pitch/Wall/M38/M11
hits=[n for n in names if any(k in n for k in ('Pitch','Wall','M38','M11_','Gym','Field','Track'))]
print('HITS', json.dumps(hits[:60]))
'''
res = send_execute(CODE, strict_json=False, timeout=120)
print(res)
