package com.gy.rotarapida

import org.json.JSONObject
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.Locale

/**
 * v68: comunicacao LOCAL via adb reverse tcp:8765 tcp:8765.
 * Nao utiliza servico externo nem altera a UI do WhatsApp.
 * Chamadas somente no executor de fundo do AccessibilityService.
 */
internal object RyzenOcrBridgeV68 {
    internal data class Result(val bairro: String, val priority: Int, val gaiolas: List<String>, val pcMs: Double)
    private val nomes = listOf(
        "Valparaíso", "Colina de Laranjeiras", "Praia da Baleia",
        "Mata da Praia", "Morada de Laranjeiras", "Eurico", "Rosário", "Manoel Plaza"
    )
    private val codigo = Regex("^[A-Z]-[0-9]{2}$")

    fun reconhecer(jpg: ByteArray): Result? {
        if (jpg.isEmpty() || jpg.size > 4_000_000) return null
        return try {
            Socket().use { socket ->
                socket.tcpNoDelay = true
                socket.connect(InetSocketAddress("127.0.0.1", 8765), 250)
                socket.soTimeout = 2500
                val output = DataOutputStream(socket.getOutputStream())
                val input = DataInputStream(socket.getInputStream())
                output.writeInt(jpg.size)
                output.write(jpg)
                output.flush()
                val n = input.readInt()
                if (n !in 1..65536) return null
                val body = ByteArray(n)
                input.readFully(body)
                val root = JSONObject(String(body, Charsets.UTF_8))
                if (root.optString("estado") != "OK") return null
                val result = root.optJSONObject("resultado") ?: return null
                if (result.optString("estado") != "OK") return null
                val bairro = RouteParser.normalize(result.optString("bairro"))
                val index = nomes.indexOfFirst { RouteParser.normalize(it) == bairro }
                if (index < 0) return null
                val arr = result.optJSONArray("gaiolas") ?: return null
                val gaiolas = ArrayList<String>()
                for (i in 0 until arr.length()) {
                    val c = arr.optString(i).trim().uppercase(Locale.ROOT)
                    if (codigo.matches(c) && c !in gaiolas) gaiolas.add(c)
                }
                if (gaiolas.isEmpty()) return null
                Result(nomes[index], index, gaiolas, root.optDouble("tempo_pc_ms", -1.0))
            }
        } catch (_: Exception) {
            null // OCR do telefone faz reserva; NUNCA envie resultado parcial
        }
    }
}
