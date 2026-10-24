import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'config.dart';

/// Overridden in main() with a real instance (and in tests with a mock one).
final sharedPrefsProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('sharedPrefsProvider must be overridden'),
);

enum SpeechRate { slow, normal, fast }

extension SpeechRateValue on SpeechRate {
  /// flutter_tts rate: 0.0–1.0 (0.5 is the platform's normal speed on Android).
  double get value => switch (this) {
        SpeechRate.slow => 0.35,
        SpeechRate.normal => 0.45,
        SpeechRate.fast => 0.6,
      };
}

class AppSettings {
  const AppSettings({
    required this.language,
    required this.onboarded,
    required this.speechRate,
    required this.textScale,
    required this.readAloud,
    required this.serverUrl,
    required this.deviceId,
    this.token,
  });

  final String language; // 'hi' | 'en'
  final bool onboarded;
  final SpeechRate speechRate;
  final double textScale; // user multiplier on top of the system scale
  final bool readAloud;
  final String serverUrl;
  final String deviceId;
  final String? token;

  AppSettings copyWith({
    String? language,
    bool? onboarded,
    SpeechRate? speechRate,
    double? textScale,
    bool? readAloud,
    String? serverUrl,
    String? token,
    bool clearToken = false,
  }) =>
      AppSettings(
        language: language ?? this.language,
        onboarded: onboarded ?? this.onboarded,
        speechRate: speechRate ?? this.speechRate,
        textScale: textScale ?? this.textScale,
        readAloud: readAloud ?? this.readAloud,
        serverUrl: serverUrl ?? this.serverUrl,
        deviceId: deviceId,
        token: clearToken ? null : (token ?? this.token),
      );
}

class SettingsNotifier extends Notifier<AppSettings> {
  SharedPreferences get _prefs => ref.read(sharedPrefsProvider);

  @override
  AppSettings build() {
    final p = _prefs;
    var deviceId = p.getString('device_id');
    if (deviceId == null) {
      deviceId = 'android-${const Uuid().v4()}';
      p.setString('device_id', deviceId);
    }
    return AppSettings(
      language: p.getString('language') ?? 'hi',
      onboarded: p.getBool('onboarded') ?? false,
      speechRate: SpeechRate.values[p.getInt('speech_rate') ?? 1],
      textScale: p.getDouble('text_scale') ?? 1.0,
      readAloud: p.getBool('read_aloud') ?? true,
      serverUrl: p.getString('server_url') ?? defaultApiBaseUrl,
      deviceId: deviceId,
      token: p.getString('token'),
    );
  }

  void setLanguage(String lang) {
    _prefs.setString('language', lang);
    state = state.copyWith(language: lang);
  }

  void completeOnboarding() {
    _prefs.setBool('onboarded', true);
    state = state.copyWith(onboarded: true);
  }

  void setSpeechRate(SpeechRate rate) {
    _prefs.setInt('speech_rate', rate.index);
    state = state.copyWith(speechRate: rate);
  }

  void setTextScale(double scale) {
    _prefs.setDouble('text_scale', scale);
    state = state.copyWith(textScale: scale);
  }

  void setReadAloud(bool value) {
    _prefs.setBool('read_aloud', value);
    state = state.copyWith(readAloud: value);
  }

  void setServerUrl(String url) {
    _prefs.setString('server_url', url);
    _prefs.remove('token');
    state = state.copyWith(serverUrl: url, clearToken: true);
  }

  void setToken(String? token) {
    if (token == null) {
      _prefs.remove('token');
    } else {
      _prefs.setString('token', token);
    }
    state = state.copyWith(token: token, clearToken: token == null);
  }
}

final settingsProvider = NotifierProvider<SettingsNotifier, AppSettings>(SettingsNotifier.new);
