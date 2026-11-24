package com.gy.rotarapida

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RouteParserV74PrioritiesTest {
    @Test fun sixDefaultPrioritiesAndCustomization() {
        val expected=listOf(
            "Eurico", "Rosario", "Manoel Plaza", "Mata da Praia",
            "Praia da Baleia", "Morada de Laranjeiras"
        )
        assertEquals(expected,Prefs.defaultNeighborhoods())
        RouteParser.configurePriorities(expected)
        expected.forEachIndexed { i,name ->
            assertEquals("priority mismatch for "+name,i,RouteParser.matchPriority(name)?.first)
        }
        assertEquals(1,RouteParser.matchPriority("Rosário de Fátima")?.first)
        assertTrue(RouteParser.isFeuRosaRowV684("Feu Rosa"))
        assertNull(RouteParser.matchPriority("Feu Rosa"))
        // User changes must still override the built-in six.
        RouteParser.configurePriorities(listOf("Mata da Praia", "Eurico"))
        assertEquals(0,RouteParser.matchPriority("Mata da Praia")?.first)
        assertEquals(1,RouteParser.matchPriority("Eurico")?.first)
    }
}
