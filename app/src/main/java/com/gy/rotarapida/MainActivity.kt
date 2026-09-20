package com.gy.rotarapida

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import com.google.android.material.textfield.TextInputEditText

class MainActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView

    private val refreshStatus = object : Runnable {
        override fun run() {
            status.text = Prefs.status(this@MainActivity)
            handler.postDelayed(this, 500)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val group = findViewById<TextInputEditText>(R.id.editGroupName)
        val save = findViewById<Button>(R.id.buttonSave)
        val enabled = findViewById<SwitchCompat>(R.id.switchEnabled)
        val accessibility = findViewById<Button>(R.id.buttonAccessibility)
        status = findViewById(R.id.textStatus)

        group.setText(Prefs.groupName(this))
        enabled.isChecked = Prefs.isEnabled(this)

        save.setOnClickListener {
            Prefs.setGroupName(this, group.text?.toString().orEmpty())
            Prefs.setStatus(
                this,
                if (Prefs.groupName(this).isBlank())
                    "Digite o nome exato do grupo antes de ativar."
                else
                    "Grupo salvo: ${Prefs.groupName(this)}"
            )
        }

        enabled.setOnCheckedChangeListener { _, checked ->
            Prefs.setEnabled(this, checked)
            Prefs.setStatus(
                this,
                when {
                    checked && Prefs.groupName(this).isBlank() ->
                        "Automação ligada, mas falta configurar o nome do grupo."
                    checked ->
                        "Automação ligada. Abra o grupo no WhatsApp."
                    else ->
                        "Automação desligada."
                }
            )
        }

        accessibility.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
    }

    override fun onResume() {
        super.onResume()
        handler.post(refreshStatus)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(refreshStatus)
    }
}
