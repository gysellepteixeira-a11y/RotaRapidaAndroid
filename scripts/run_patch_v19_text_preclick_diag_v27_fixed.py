from pathlib import Path

P=Path('scripts/patch_v19_text_preclick_diag_v27.py')
code=P.read_text(encoding='utf-8')

# v21 changed the waiter signature by adding a generation token.
old_sig="'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int){'"
new_sig="'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){'"
if old_sig not in code:
    raise SystemExit('v27 fixed runner: old required waiter signature not found')
code=code.replace(old_sig,new_sig,1)

# The retry success block is no longer byte-identical to the immediate success
# block because v21 retires the generation before updating rmUsed/rmPending.
old_block='''# The remaining identical success block belongs to DESC_RETRY. Capture click end.
if immediate_ok_old not in s:
    raise SystemExit('v27 retry click anchor not found')
retry_ok_new=''' + "'''            if(ok){\n                rmV27ClickDoneAt=done\n                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done\n'''" + '''
s=s.replace(immediate_ok_old,retry_ok_new,1)
'''
new_block='''# v21 inserts generation retirement inside DESC_RETRY, so capture click end at
# that token-specific success anchor.
retry_ok_old=''' + "'''                rmDescWaitActiveGenerationV21=0L\n                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done\n'''" + '''
retry_ok_new=''' + "'''                rmDescWaitActiveGenerationV21=0L\n                rmV27ClickDoneAt=done\n                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done\n'''" + '''
if retry_ok_old not in s:
    raise SystemExit('v27 retry click token anchor not found')
s=s.replace(retry_ok_old,retry_ok_new,1)
'''
if old_block not in code:
    raise SystemExit('v27 fixed runner: retry source block not found')
code=code.replace(old_block,new_block,1)

exec(compile(code,str(P),'exec'),{'__name__':'__main__'})
