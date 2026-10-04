from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v30 | TEXT v6 + TRUNC BEFORE ROOT + LAZY ADMIN + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v31 | TEXT v6 + SKIP OBSOLETE BAND + TRUNC BEFORE ROOT + LAZY ADMIN + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'val before=freshReadMoreBandStatsV12(descTarget.rect)',
    'private fun waitForReadMoreExpansionV12(',
    'val proof=freshReadMoreProofV18(target)',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'truncBeforeRootV30=enabled',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for m in required:
    if m not in s:
        raise SystemExit('SKIP OBSOLETE BAND v31 wrong base: '+m)

# Safety proof: since v18, the old broad-band "before" snapshot is no longer
# consulted by the expansion verifier. Expansion is accepted only by
# freshReadMoreProofV18(), which reacquires the same message by anchor, requires
# material text growth, and requires truncation to be gone.
a=s.find('    private fun waitForReadMoreExpansionV12(')
b=s.find('    private fun waitForTextDirectSendReadyV5(',a)
if a<0 or b<0:
    raise SystemExit('v31 wait region not found')
wait_region=s[a:b]
if 'val proof=freshReadMoreProofV18(target)' not in wait_region:
    raise SystemExit('v31 strict proof missing from wait region')
if 'before.' in wait_region:
    raise SystemExit('v31 unsafe: wait region still reads before.*')

# Immediate DESC_NEWITEM/DESC_ROOT path: preserve rememberReadMoreChainV16(),
# ACTION_CLICK and strict-proof polling, but skip the obsolete full fresh-tree
# band snapshot. Keep the value only to satisfy the historical function signature.
immediate_old='''                val v27BandStart=SystemClock.elapsedRealtime()
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                rmV27BandMs=SystemClock.elapsedRealtime()-v27BandStart
                val t=SystemClock.elapsedRealtime()
'''
immediate_new='''                val before=ReadMoreBandStatsV12(0,0,false,false)
                rmV27BandMs=0L
                val t=SystemClock.elapsedRealtime()
'''
if immediate_old not in s:
    raise SystemExit('v31 immediate band block not found')
s=s.replace(immediate_old,immediate_new,1)

# Rare DESC_RETRY path: same reasoning. rememberReadMoreChainV16() immediately
# above still builds the strict same-message anchor before ACTION_CLICK.
retry_old='''            val v27RetryBandStart=SystemClock.elapsedRealtime()
            val before=freshReadMoreBandStatsV12(descTarget.rect)
            rmV27RetryBandMs=SystemClock.elapsedRealtime()-v27RetryBandStart
            val t=SystemClock.elapsedRealtime()
'''
retry_new='''            val before=ReadMoreBandStatsV12(0,0,false,false)
            rmV27RetryBandMs=0L
            val t=SystemClock.elapsedRealtime()
'''
if retry_old not in s:
    raise SystemExit('v31 retry band block not found')
s=s.replace(retry_old,retry_new,1)

report_anchor='''                    appendLine("truncBeforeRootV30=enabled | currentDescRoot=${tdV27DescRootMs}ms | currentTargetScan=${tdV27TargetScanMs}ms | strictProof=preserved")
'''
report_insert=report_anchor+'''                    appendLine("obsoleteBandV31=skipped=true | immediateBand=${tdV27BandMs}ms | retryBand=${tdV27RetryBandMs}ms | strictSameMessageProof=preserved")
'''
if report_anchor not in s:
    raise SystemExit('v31 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'val before=ReadMoreBandStatsV12(0,0,false,false)',
    'rmV27BandMs=0L',
    'rmV27RetryBandMs=0L',
    'obsoleteBandV31=skipped=true',
    'val proof=freshReadMoreProofV18(target)',
    'directProofV26=used=$tdV26DirectUsed',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('SKIP OBSOLETE BAND v31 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('SKIP OBSOLETE BAND v31 applied: removed legacy fresh-tree band snapshot before Read-more click; v18 strict same-message proof preserved')
