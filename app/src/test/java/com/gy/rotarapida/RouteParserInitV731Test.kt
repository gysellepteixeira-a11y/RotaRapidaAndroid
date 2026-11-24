package com.gy.rotarapida

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Guard against V73's service startup crash:
 * RouteParser initializes dynamic priorities at object construction time,
 * and this invokes normalize(). Regex cache must exist before priorities.
 */
class RouteParserInitV731Test {
    @Test
    fun initializePrioritiesAndNormalizeWithoutCrash() {
        RouteParser.configurePriorities(listOf("Rosario de Fatima", "Mata da Praia", "Republica"))
        assertEquals("rosario de fatima", RouteParser.normalize("Rosário de Fátima"))
        assertEquals("feu rosa", RouteParser.normalize("Feu Rosa"))
        assertTrue(RouteParser.isFeuRosaRowV684("Feu Rosa"))
        assertNotNull(RouteParser.matchPriority("Rosário de Fátima"))
        assertEquals("Rosario de Fatima", RouteParser.matchPriority("Rosário de Fátima")?.second)
    }
}
