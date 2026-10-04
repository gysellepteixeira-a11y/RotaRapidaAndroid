from pathlib import Path

p=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=p.read_text(encoding='utf-8')

bad='''    private var rmV27RetryBandMs=0L; rmV33AnchorDepth=-1; rmV33LocalCalls=0; rmV33LocalTotalMs=0L; rmV33LocalMaxMs=0L; rmV33LocalWins=0; rmV33BfsFallbacks=0; rmV33LocalRefreshOk=false; rmV33LocalChars=0; rmV33LocalTruncated=true\n'''
good='''    private var rmV27RetryBandMs=0L\n'''
if bad not in s:
    raise SystemExit('v33 bad class-scope reset line not found')
s=s.replace(bad,good,1)

reset='''rmV27RetrySearchCalls=0; rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'''
reset2=reset+'''; rmV33AnchorDepth=-1; rmV33LocalCalls=0; rmV33LocalTotalMs=0L; rmV33LocalMaxMs=0L; rmV33LocalWins=0; rmV33BfsFallbacks=0; rmV33LocalRefreshOk=false; rmV33LocalChars=0; rmV33LocalTruncated=true'''
if reset not in s:
    raise SystemExit('v33 real reset sequence not found')
s=s.replace(reset,reset2,1)

p.write_text(s,encoding='utf-8')
print('v33 reset placement fixed: class declaration restored and temporary local-proof state reset at tdBegin')
