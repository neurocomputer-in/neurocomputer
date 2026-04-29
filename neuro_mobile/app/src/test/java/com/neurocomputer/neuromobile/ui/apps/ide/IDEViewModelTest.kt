package com.neurocomputer.neuromobile.ui.apps.ide

import org.junit.Assert.*
import org.junit.Test

class IdeNodeTest {

    @Test fun `node equality by id`() {
        val n1 = IdeNode("a", "Label", 0f, 0f)
        val n2 = IdeNode("a", "Label", 0f, 0f)
        assertEquals(n1, n2)
    }

    @Test fun `edge connects two nodes`() {
        val edge = IdeEdge("a", "b")
        assertEquals("a", edge.fromId)
        assertEquals("b", edge.toId)
    }

    @Test fun `IdeState default is empty`() {
        val s = IdeState()
        assertTrue(s.nodes.isEmpty())
        assertTrue(s.edges.isEmpty())
        assertNull(s.selectedNodeId)
    }
}
