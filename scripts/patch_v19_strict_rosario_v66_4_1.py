from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
s=p.read_text(encoding="utf-8")
# Only accept Rosário when its identifying stem is actually present.
# In particular, Feu Rosa must not be promoted to Rosário through fuzzy matching.
anchor='''            if (rule.requiredTokens.all { token -> containsTokenApprox(normalized, token) }) {'''
replacement='''            val rosarioRule = normalize(rule.name) == "rosario" || normalize(rule.name) == "rosario de fatima"
            if (rosarioRule && !Regex("""\\brosar[a-z]*\\b""").containsMatchIn(normalized)) return@forEachIndexed
            if (rule.requiredTokens.all { token -> containsTokenApprox(normalized, token) }) {'''
if anchor not in s: raise SystemExit("priorityFor anchor missing")
s=s.replace(anchor,replacement,1)
anchor2='''            if(rule.requiredTokens.all { normalized.contains(it) }){'''
replacement2='''            val rosarioRule = normalize(rule.name) == "rosario" || normalize(rule.name) == "rosario de fatima"
            if(rosarioRule && !Regex("""\\brosar[a-z]*\\b""").containsMatchIn(normalized)) return@forEachIndexed
            if(rule.requiredTokens.all { normalized.contains(it) }){'''
if anchor2 not in s: raise SystemExit("priorityForNormalized anchor missing")
s=s.replace(anchor2,replacement2,1)
p.write_text(s,encoding="utf-8")
print("v66.4.1 strict Rosário stem guard applied")
