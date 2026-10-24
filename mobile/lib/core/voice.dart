import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

/// On-device speech recognition (free). `hi-IN` also understands Hinglish reasonably well.
abstract class SpeechService {
  Future<bool> init();
  Future<void> listen({
    required String lang,
    required void Function(String partial) onPartial,
    required void Function(String finalText) onFinal,
  });
  Future<void> stop();
}

/// Text to speech in Hindi or English.
abstract class TtsService {
  Future<void> speak(String text, {required String lang, required double rate});
  Future<void> stop();
}

String localeFor(String lang) => lang == 'hi' ? 'hi-IN' : 'en-IN';

class DeviceSpeechService implements SpeechService {
  final _stt = SpeechToText();
  bool? _ready;
  void Function(String)? _onFinal;
  String _last = '';
  bool _delivered = false;

  @override
  Future<bool> init() async {
    _ready ??= await _stt.initialize(onStatus: (status) {
      // Some devices end without a final result; deliver what we heard.
      if ((status == 'done' || status == 'notListening') && !_delivered) {
        _delivered = true;
        _onFinal?.call(_last);
      }
    }, onError: (_) {
      if (!_delivered) {
        _delivered = true;
        _onFinal?.call(_last);
      }
    });
    return _ready!;
  }

  @override
  Future<void> listen({
    required String lang,
    required void Function(String partial) onPartial,
    required void Function(String finalText) onFinal,
  }) async {
    if (!await init()) {
      onFinal('');
      return;
    }
    _onFinal = onFinal;
    _last = '';
    _delivered = false;
    await _stt.listen(
      onResult: (SpeechRecognitionResult r) {
        _last = r.recognizedWords;
        onPartial(_last);
        if (r.finalResult && !_delivered) {
          _delivered = true;
          onFinal(_last);
        }
      },
      listenOptions: SpeechListenOptions(
        localeId: localeFor(lang),
        partialResults: true,
        listenMode: ListenMode.dictation,
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 3),
        cancelOnError: true,
      ),
    );
  }

  @override
  Future<void> stop() => _stt.stop();
}

class DeviceTtsService implements TtsService {
  final _tts = FlutterTts();
  bool _configured = false;

  @override
  Future<void> speak(String text, {required String lang, required double rate}) async {
    if (!_configured) {
      await _tts.awaitSpeakCompletion(true); // so we can listen right after a question
      _configured = true;
    }
    await _tts.stop();
    await _tts.setLanguage(localeFor(lang));
    await _tts.setSpeechRate(rate);
    await _tts.speak(text);
  }

  @override
  Future<void> stop() => _tts.stop();
}

final speechProvider = Provider<SpeechService>((ref) => DeviceSpeechService());
final ttsProvider = Provider<TtsService>((ref) => DeviceTtsService());
