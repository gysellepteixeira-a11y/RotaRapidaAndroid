from pathlib import Path

root=Path("app/src/main/java/com/gy/rotarapida")
p=root/"TextOfferGuardV85.kt"
s=p.read_text(encoding="utf-8")
def once(old,new):
    global s
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new,1)

# Preserve the V85 six-field layout. Add only the seven-field layout
# actually observed in the second admin table, including space-only rendering.
once('    private val quoted = Regex(',r'''    private val flatSeven = Regex(
        "^([A-Z]-?\\d{2}) +((?:AT)\\d{8}[A-Z0-9]{3,24}) +(.+?) +(\\d{1,6}) +(\\d{1,6}) +(" +
            towns + "(?: *; *" + towns + ")*) +(.+)$",
        RegexOption.IGNORE_CASE
    )
    private val quoted = Regex(''')
once(r'''                if (parts.size == 6) parts else flat.matchEntire(line)?.groupValues?.drop(1) ?: continue
            }
            if (fields.size != 6) continue
            val (c, id, count, status, municipality) = fields
            val bairro = fields[5]
            if (!cage.matches(c) || !code.matches(id) || !qty.matches(count)) continue
            if (status.isBlank() || !town.matches(municipality) || bairro.none { it.isLetter() }) continue''',
r'''                if (parts.size in 6..7) parts else (
                    flatSeven.matchEntire(line)?.groupValues?.drop(1)
                        ?: flat.matchEntire(line)?.groupValues?.drop(1)
                        ?: continue
                )
            }
            if (fields.size !in 6..7) continue
            val c=fields[0]
            val id=fields[1]
            val count=if(fields.size==6) fields[2] else fields[3]
            val status=if(fields.size==6) fields[3] else fields[2]
            val municipality=fields[fields.size-2]
            val bairro=fields.last()
            if (!cage.matches(c) || !code.matches(id) || !qty.matches(count)) continue
            if(fields.size==7 && !qty.matches(fields[4])) continue
            if (status.isBlank() || status.none { it.isLetter() } ||
                !town.matches(municipality) || bairro.none { it.isLetter() }) continue''')
p.write_text(s,encoding="utf-8")

# Only identify the revised text guard in its diagnostic; image report untouched.
service=root/"WhatsRouteAccessibilityService.kt"
k=service.read_text(encoding="utf-8")
assert k.count('V85 TEXT GUARD |')==1
service.write_text(k.replace('V85 TEXT GUARD |','V85.1 TEXT GUARD |',1),encoding="utf-8")

test=Path("app/src/test/java/com/gy/rotarapida/TextOfferGuardV851Test.kt")
test.write_text(r'''package com.gy.rotarapida

import org.junit.Assert.*
import org.junit.Test

class TextOfferGuardV851Test {
    @Test fun fullNewAdminTable() {
        val raw = """
B-14	AT20261128DPOO3	Ausente	126	0	Serra	Jardim Carapina
B-22	AT20261128DPNZM	Ausente	133	0	Serra	Novo Horizonte
B-23	AT20261128DPNZL	Ausente	133	0	Serra	Novo Horizonte
C-02	AT20261128DPNXH	Ausente	136	0	Serra	das Laranjeiras
C-12	AT20261128DPMZ3	Ausente	141	0	Serra	Parque Jacaraípe
C-17	AT20261128DPMME	Ausente	127	0	Serra	Central Carapina
C-18	AT20261128DPJPY	Ausente	126	0	Serra	Central Carapina
C-20	AT20261128DPJM6	Ausente	129	0	Serra	Feu Rosa
C-22	AT20261128DPMIN	Ausente	130	0	Serra	Vila Nova de Colares
C-28	AT20261128DPM8N	Ausente	130	0	Serra	Feu Rosa
C-29	AT20261128DPMAU	Ausente	143	0	Serra	Jardim Limoeiro
C-35	AT20261128DPLJP	Ausente	134	0	Serra	Morada de Laranjeiras
""".trim()
        val rows=TextOfferGuardV85.rows(raw)
        assertEquals(12,rows.size)
        assertEquals("C35",rows.last().cage)
        assertEquals("Morada de Laranjeiras",rows.last().neighborhood)
        assertEquals(12,TextOfferGuardV85.rows(raw.replace('\t',' ')).size)
    }

    @Test fun bothFormatsAndStatusVariants() {
        for(raw in listOf(
            "C-35\tAT20261128DPLJP\tOutro nome\t134\t3\tSerra\tMorada de Laranjeiras",
            "C-35 AT20261128DPLJP Outro nome 134 3 Serra Morada de Laranjeiras",
            "C-35  AT20261128DPLJP  Outro nome  134  3  Serra  Morada de Laranjeiras",
            "C-35\tAT20261128DPLJP\t134\t\tOutro nome\tSerra\tMorada de Laranjeiras"
        )) {
            val row=TextOfferGuardV85.rows(raw).single()
            assertEquals("C35",row.cage)
            assertEquals("Morada de Laranjeiras",row.neighborhood)
        }
    }

    @Test fun malformedNewLayoutStillBlocked() {
        for(raw in listOf(
            "Nome: Entregador\nID: 123456\nModal: Passeio\nGaiola: C-35",
            "Rosario A09",
            "C-35\tAT20261128DPLJP\tAusente\t134\tX\tSerra\tRosario",
            "C-35\tAT20261128DPLJP\tAusente\tX\t0\tSerra\tRosario",
            "C-35\tAT20261128DPLJP\tAusente\t134\t0\tSerra\nRosario",
            "mensagem citada\nC-35\tAT20261128DPLJP\tAusente\t134\t0\tSerra\tRosario"
        )) assertTrue(raw,TextOfferGuardV85.rows(raw).isEmpty())
    }
}
''',encoding="utf-8")
print("V85.1: both observed text schemas, full 12-row regression fixture, original guard and OCR preserved.")
