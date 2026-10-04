from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v21 | TEXT v6 + READ MORE DESC WAIT TOKEN + STRICT PROOF + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v22 | TEXT v6 + SCHEDULE DIAG + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private var rmDescWaitGenerationV21=0L; private var rmDescWaitActiveGenerationV21=0L',
    'scheduleAnalyze(12L)',
    'private fun scheduleAnalyze(delayMs: Long)',
    'readMoreProof=$tdReadMoreProofV18',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('TEXT SCHEDULE DIAG v22 wrong base: '+m)

# Diagnostic-only state. No parser/send/read-more behavior is changed.
state_old='    private var rmDescWaitGenerationV21=0L; private var rmDescWaitActiveGenerationV21=0L\n'
state_new=state_old+'''    private var tdV22BatchActive=false
    private var tdV22BatchEvent=0L
    private var tdV22FirstScheduleAt=0L
    private var tdV22FirstHandlerAt=0L
    private var tdV22RequestedDelay=0L
    private var tdV22ScheduleCount=0
    private var tdV22HandlerCount=0
    private var tdV22EventsWhilePending=0
    private var tdV22FirstLate=-1L
    private var tdV22LastLate=-1L
    private var tdV22MaxLate=0L
'''
if state_old not in s:
    raise SystemExit('v22 state anchor not found')
s=s.replace(state_old,state_new,1)

# Instrument the exact point that already calls scheduleAnalyze(12L). This is more
# robust than matching the surrounding v21 Read-more guards and does not change
# their behavior. Events that reach this call while analyzeScheduled=true are counted.
event_call='        scheduleAnalyze(12L)\n'
event_instrument='''        val tdV22Now=SystemClock.elapsedRealtime()
        if(!tdV22BatchActive || tdV22BatchEvent<=0L || tdV22Now-tdV22BatchEvent>1500L){
            tdV22BatchActive=true
            tdV22BatchEvent=tdV22Now
            tdV22FirstScheduleAt=0L
            tdV22FirstHandlerAt=0L
            tdV22RequestedDelay=0L
            tdV22ScheduleCount=0
            tdV22HandlerCount=0
            tdV22EventsWhilePending=0
            tdV22FirstLate=-1L
            tdV22LastLate=-1L
            tdV22MaxLate=0L
        }else if(analyzeScheduled){
            tdV22EventsWhilePending++
        }
        scheduleAnalyze(12L)
'''
if event_call not in s:
    raise SystemExit('v22 schedule call anchor not found')
s=s.replace(event_call,event_instrument,1)

# Instrument the same Handler.postDelayed call. The callback timing is measured at
# the first instruction inside the existing Runnable, before analyzeCurrentWindow().
schedule_old='''    private fun scheduleAnalyze(delayMs: Long) {
        if (analyzeScheduled) return
        analyzeScheduled = true

        handler.postDelayed({
            analyzeScheduled = false
            analyzeCurrentWindow()
        }, delayMs)
    }
'''
schedule_new='''    private fun scheduleAnalyze(delayMs: Long) {
        if (analyzeScheduled) return
        analyzeScheduled = true

        val tdV22ScheduledAt=SystemClock.elapsedRealtime()
        if(tdV22BatchActive){
            tdV22ScheduleCount++
            if(tdV22FirstScheduleAt==0L){
                tdV22FirstScheduleAt=tdV22ScheduledAt
                tdV22RequestedDelay=delayMs
            }
        }
        handler.postDelayed({
            val tdV22RanAt=SystemClock.elapsedRealtime()
            if(tdV22BatchActive){
                tdV22HandlerCount++
                if(tdV22FirstHandlerAt==0L) tdV22FirstHandlerAt=tdV22RanAt
                val tdV22Late=(tdV22RanAt-tdV22ScheduledAt-delayMs).coerceAtLeast(0L)
                if(tdV22FirstLate<0L) tdV22FirstLate=tdV22Late
                tdV22LastLate=tdV22Late
                if(tdV22Late>tdV22MaxLate) tdV22MaxLate=tdV22Late
            }
            analyzeScheduled = false
            analyzeCurrentWindow()
        }, delayMs)
    }
'''
if schedule_old not in s:
    raise SystemExit('v22 scheduleAnalyze anchor not found')
s=s.replace(schedule_old,schedule_new,1)

# Add one line to the existing RAM-only diagnostic. This is emitted only after a
# confirmed send, like the rest of the text timing report.
report_anchor='''                if(tdReadMoreDescWaitMsV20>0L) appendLine("readMoreDescWait=${tdReadMoreDescWaitMsV20}ms | descWaitPolls=$tdReadMoreDescWaitPollsV20")
'''
report_insert=report_anchor+'''                val tdV22EventToSchedule=if(tdV22BatchEvent>0L && tdV22FirstScheduleAt>=tdV22BatchEvent) tdV22FirstScheduleAt-tdV22BatchEvent else -1L
                val tdV22EventToHandler=if(tdV22BatchEvent>0L && tdV22FirstHandlerAt>=tdV22BatchEvent) tdV22FirstHandlerAt-tdV22BatchEvent else -1L
                appendLine("scheduleV22=${tdV22RequestedDelay}ms | event->schedule=${tdV22EventToSchedule}ms | event->firstHandler=${tdV22EventToHandler}ms | handlerLate=${tdV22FirstLate}ms | lastLate=${tdV22LastLate}ms | maxLate=${tdV22MaxLate}ms | schedules=$tdV22ScheduleCount | callbacks=$tdV22HandlerCount | eventsWhilePending=$tdV22EventsWhilePending")
'''
if report_anchor not in s:
    raise SystemExit('v22 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

# Retire only diagnostic state after the report. This does not alter operational state.
report_end_old='Prefs.setSpeedDiagnosticReport(this,x); tdOn=false; tdCandidate=0'
report_end_new='''Prefs.setSpeedDiagnosticReport(this,x); tdOn=false; tdCandidate=0
        tdV22BatchActive=false; tdV22BatchEvent=0L; tdV22FirstScheduleAt=0L; tdV22FirstHandlerAt=0L
        tdV22RequestedDelay=0L; tdV22ScheduleCount=0; tdV22HandlerCount=0; tdV22EventsWhilePending=0
        tdV22FirstLate=-1L; tdV22LastLate=-1L; tdV22MaxLate=0L'''
if report_end_old not in s:
    raise SystemExit('v22 report reset anchor not found')
s=s.replace(report_end_old,report_end_new,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private var tdV22BatchActive=false',
    'tdV22EventsWhilePending++',
    'val tdV22Late=(tdV22RanAt-tdV22ScheduledAt-delayMs).coerceAtLeast(0L)',
    'scheduleV22=${tdV22RequestedDelay}ms',
    'eventsWhilePending=$tdV22EventsWhilePending',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('TEXT SCHEDULE DIAG v22 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('TEXT SCHEDULE DIAG v22 applied: diagnostic-only Handler lateness/event queue counters; v21 behavior/TEXT v6/IMAGE v9 preserved')
