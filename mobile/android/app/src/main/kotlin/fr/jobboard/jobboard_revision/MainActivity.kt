package fr.jobboard.jobboard_revision

import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

// Lecture à voix haute des questions de l'entretien oral, par le moteur vocal
// d'Android : « speak » répond true une fois la phrase dite, false si elle ne
// peut pas l'être ou si elle est interrompue.
class MainActivity : FlutterActivity() {
    private var speech: TextToSpeech? = null
    private var ready = false
    private var pending: Pair<String, MethodChannel.Result>? = null
    private var waiting: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "fr.jobboard/speech")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "speak" -> speak(call.argument<String>("text").orEmpty(), result)
                    "stop" -> {
                        stopSpeech()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun speak(text: String, result: MethodChannel.Result) {
        stopSpeech()

        if (speech != null) {
            say(text, result)
            return
        }

        // Le moteur s'initialise à part : la phrase attend qu'il soit prêt.
        pending?.second?.success(false)
        pending = text to result
        speech = TextToSpeech(this) { status ->
            ready = status == TextToSpeech.SUCCESS
            pending?.let { (waitingText, waitingResult) ->
                pending = null
                say(waitingText, waitingResult)
            }
        }
    }

    private fun say(text: String, result: MethodChannel.Result) {
        val engine = speech

        if (!ready || engine == null) {
            result.success(false)
            return
        }

        engine.language = Locale.FRANCE
        waiting = result
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}

            override fun onDone(utteranceId: String?) = finish(true)

            @Deprecated("Remplacé par onError(String, Int), appelé aussi")
            override fun onError(utteranceId: String?) = finish(false)
        })
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "question")
    }

    private fun finish(done: Boolean) {
        runOnUiThread {
            waiting?.success(done)
            waiting = null
        }
    }

    private fun stopSpeech() {
        speech?.stop()
        waiting?.success(false)
        waiting = null
    }

    override fun onDestroy() {
        speech?.shutdown()
        super.onDestroy()
    }
}
