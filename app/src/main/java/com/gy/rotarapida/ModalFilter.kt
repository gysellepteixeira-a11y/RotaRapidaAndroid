package com.gy.rotarapida

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import kotlin.math.abs

/**
 * Filtra modalidades SEM OCR adicional. Amostra a cor da coluna Modal (direita).
 * FAKE VOLUMOSO (rosa) e VOLUMOSO (vermelho) bloqueados no modo padrao; MOTO (preto) sempre.
 * Azul e cores desconhecidas sao aceitos.
 *
 * Filtrar antes do OCR faz o parser ignorar bairro/gaiola de linhas bloqueadas.
 * Em imagens densas, topOffset e o deslocamento vertical do recorte.
 */
internal object ModalFilter {
    private enum class Mode { BLUE, VOLUMOSO, BLACK, OTHER }
    private data class Span(val start: Int, val end: Int)

    private fun classify(pixel: Int): Mode {
        val r = Color.red(pixel)
        val g = Color.green(pixel)
        val b = Color.blue(pixel)
        return when {
            b >= 105 && b >= r + 25 && b >= g + 13 && r <= 125 && g in 28..170 -> Mode.BLUE
            r >= 130 && r >= g + 24 && r >= b + 17 && g <= 230 -> Mode.VOLUMOSO
            r <= 105 && g <= 105 && b <= 105 &&
                abs(r - g) <= 38 && abs(g - b) <= 38 -> Mode.BLACK
            else -> Mode.OTHER
        }
    }

    private fun excludedAtY(source: Bitmap, y: Int, includeFake: Boolean): Mode? {
        val fractions = floatArrayOf(.89f, .905f, .92f, .935f, .95f, .965f, .98f)
        var volumoso = 0
        var black = 0
        for (fraction in fractions) {
            val x = (source.width * fraction).toInt().coerceIn(0, source.width - 1)
            when (classify(source.getPixel(x, y))) {
                Mode.VOLUMOSO -> volumoso++
                Mode.BLACK -> black++
                else -> Unit
            }
        }
        return when {
            black >= 4 -> Mode.BLACK
            !includeFake && volumoso >= 4 -> Mode.VOLUMOSO
            else -> null
        }
    }

    fun filter(
        source: Bitmap,
        target: Bitmap,
        topOffset: Int,
        includeFake: Boolean
    ): Bitmap {
        if (source.width < 100 || source.height < 10 || target.isRecycled) return target
        val spans = ArrayList<Span>()
        var first = -1
        var last = -1
        var kind: Mode? = null

        fun flush() {
            if (first >= 0 && last - first + 1 >= 6) {
                spans += Span((first - 1).coerceAtLeast(0), (last + 2).coerceAtMost(source.height))
            }
            first = -1
            last = -1
            kind = null
        }

        for (y in 0 until source.height) {
            val current = excludedAtY(source, y, includeFake)
            if (current == null) {
                if (first >= 0 && y - last > 3) flush()
                continue
            }
            if (first < 0) {
                first = y
                last = y
                kind = current
            } else if (kind == current || y - last <= 2) {
                last = y
            } else {
                flush()
                first = y
                last = y
                kind = current
            }
        }
        flush()
        if (spans.isEmpty()) return target

        val editable = target.copy(Bitmap.Config.ARGB_8888, true) ?: return target
        val canvas = Canvas(editable)
        val paint = Paint().apply { color = Color.WHITE; style = Paint.Style.FILL }
        for (span in spans) {
            val y1 = (span.start - topOffset).coerceIn(0, target.height)
            val y2 = (span.end - topOffset).coerceIn(0, target.height)
            if (y2 > y1) canvas.drawRect(0f, y1.toFloat(), target.width.toFloat(), y2.toFloat(), paint)
        }
        if (target !== source) {
            try { target.recycle() } catch (_: Throwable) {}
        } else {
            try { source.recycle() } catch (_: Throwable) {}
        }
        return editable
    }
}
