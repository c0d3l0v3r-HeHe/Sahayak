import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahayak/app/theme.dart';
import 'package:sahayak/core/api_client.dart';
import 'package:sahayak/core/models.dart';
import 'package:sahayak/core/storage.dart';
import 'package:sahayak/core/voice.dart';
import 'package:sahayak/l10n/app_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

const pnrFlow = FlowInfo(
  id: 'pnr_status',
  title: L10nText('PNR status', 'PNR स्थिति'),
  description: L10nText('Check your ticket', 'टिकट देखें'),
  params: [
    FlowParam(
      name: 'pnr',
      type: 'string',
      regex: r'^\d{10}$',
      prompt: L10nText('Please tell me the 10-digit PNR number.', 'कृपया 10 अंकों का PNR नंबर बताइए।'),
    ),
  ],
);

const trainFlow = FlowInfo(
  id: 'train_running_status',
  title: L10nText('Where is my train?', 'मेरी ट्रेन कहाँ है?'),
  description: L10nText('Live status', 'लाइव स्थिति'),
  params: [],
);

class FakeApi extends SahayakApi {
  final calls = <String>[];
  IntentResult Function(String text, String? expecting)? onParse;
  List<TaskDetail> historyItems = [];

  @override
  String get baseUrl => 'http://test';

  @override
  Future<Map<String, String>> authHeaders() async => {'Authorization': 'Bearer t'};

  @override
  Future<FlowCatalog> flows() async => const FlowCatalog(flows: [pnrFlow, trainFlow], demoMode: true);

  @override
  Future<IntentResult> parse(String text, String lang,
      {String? flowId, Map<String, String>? params, String? expecting}) async {
    calls.add('parse:$text');
    return onParse!(text, expecting);
  }

  @override
  Future<String> createTask(String flowId, Map<String, String> params, String lang) async {
    calls.add('create:$flowId:${params.values.join(',')}');
    return 'task1';
  }

  @override
  Future<TaskDetail> task(String id) async => throw UnimplementedError();

  @override
  Future<List<TaskDetail>> history({int limit = 30}) async => historyItems;

  @override
  Future<void> answer(String taskId, String handoffId, String value) async {}

  @override
  Future<void> cancel(String taskId) async {}

  @override
  Future<void> deleteMyData() async {}

  @override
  Uri eventsUri(String taskId, String token) => Uri.parse('ws://test');
}

class FakeSpeech implements SpeechService {
  FakeSpeech(this.utterances);
  final List<String> utterances;

  @override
  Future<bool> init() async => true;

  @override
  Future<void> listen({
    required String lang,
    required void Function(String partial) onPartial,
    required void Function(String finalText) onFinal,
  }) async {
    final text = utterances.isEmpty ? '' : utterances.removeAt(0);
    onPartial(text);
    onFinal(text);
  }

  @override
  Future<void> stop() async {}
}

class FakeTts implements TtsService {
  final spoken = <String>[];

  @override
  Future<void> speak(String text, {required String lang, required double rate}) async => spoken.add(text);

  @override
  Future<void> stop() async {}
}

Future<List<Override>> testOverrides({
  FakeApi? api,
  FakeSpeech? speech,
  FakeTts? tts,
  String lang = 'en',
}) async {
  SharedPreferences.setMockInitialValues({'onboarded': true, 'language': lang, 'device_id': 'test-device-1'});
  final prefs = await SharedPreferences.getInstance();
  return [
    sharedPrefsProvider.overrideWithValue(prefs),
    apiProvider.overrideWithValue(api ?? FakeApi()),
    speechProvider.overrideWithValue(speech ?? FakeSpeech([])),
    ttsProvider.overrideWithValue(tts ?? FakeTts()),
  ];
}

/// Wraps a widget in a localized, themed app.
Widget wrap(Widget child, {required List<Override> overrides, String lang = 'en', double textScale = 1.0}) {
  return ProviderScope(
    overrides: overrides,
    child: MaterialApp(
      theme: buildTheme(Brightness.light, useGoogleFonts: false),
      locale: Locale(lang),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, c) =>
          MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)), child: c!),
      home: child,
    ),
  );
}

void useTallPhone(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 2.625;
  addTearDown(tester.view.reset);
}
