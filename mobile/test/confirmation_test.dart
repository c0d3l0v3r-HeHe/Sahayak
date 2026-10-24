import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:sahayak/app/theme.dart';
import 'package:sahayak/core/models.dart';
import 'package:sahayak/features/listen/confirmation_card.dart';
import 'package:sahayak/features/listen/listen_screen.dart';
import 'package:sahayak/l10n/app_localizations.dart';

import 'helpers.dart';

const pnrConfirm = L10nText(
  'You want to check the status of PNR 4512345678?',
  'आप PNR 4512345678 की स्थिति जानना चाहते हैं?',
);

void main() {
  testWidgets('confirmation card shows the question and both actions', (tester) async {
    var yes = 0, change = 0;
    await tester.pumpWidget(wrap(
      ConfirmationCard(text: pnrConfirm.hi, onYes: () => yes++, onChange: () => change++),
      overrides: await testOverrides(lang: 'hi'),
      lang: 'hi',
    ));
    expect(find.text(pnrConfirm.hi), findsOneWidget);
    await tester.tap(find.text('हाँ'));
    await tester.tap(find.text('बदलें'));
    expect((yes, change), (1, 1));
    final yesSize = tester.getSize(find.widgetWithText(FilledButton, 'हाँ'));
    expect(yesSize.height, greaterThanOrEqualTo(56));
  });

  Widget routed(List<Override> overrides, String location) {
    final router = GoRouter(initialLocation: location, routes: [
      GoRoute(path: '/', builder: (_, _) => const Text('home')),
      GoRoute(
        path: '/listen',
        builder: (_, s) => ListenScreen(
          startFlowId: s.uri.queryParameters['flow'],
          autoListen: s.uri.queryParameters['type'] != '1',
        ),
      ),
      GoRoute(path: '/task/:id', builder: (_, s) => Text('task ${s.pathParameters['id']}')),
    ]);
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp.router(
        theme: buildTheme(Brightness.light, useGoogleFonts: false),
        locale: const Locale('en'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        routerConfig: router,
      ),
    );
  }

  testWidgets('speak -> confirm -> task is created', (tester) async {
    useTallPhone(tester);
    final api = FakeApi()
      ..onParse = (text, expecting) => const IntentResult(
            flowId: 'pnr_status',
            params: {'pnr': '4512345678'},
            missing: [],
            confirmation: pnrConfirm,
          );
    final tts = FakeTts();
    final overrides = await testOverrides(api: api, speech: FakeSpeech(['check my PNR 4512345678']), tts: tts);
    await tester.pumpWidget(routed(overrides, '/listen'));
    await tester.pumpAndSettle();

    expect(find.text(pnrConfirm.en), findsOneWidget);
    expect(tts.spoken, contains(pnrConfirm.en)); // confirmation is read aloud
    await tester.tap(find.text('Yes'));
    await tester.pumpAndSettle();
    expect(api.calls, ['parse:check my PNR 4512345678', 'create:pnr_status:4512345678']);
    expect(find.text('task task1'), findsOneWidget);
  });

  testWidgets('missing details are asked one at a time (keypad)', (tester) async {
    useTallPhone(tester);
    final api = FakeApi()
      ..onParse = (text, expecting) {
        expect(expecting, 'pnr');
        return const IntentResult(flowId: 'pnr_status', params: {'pnr': '4512345678'}, missing: [], confirmation: pnrConfirm);
      };
    await tester.pumpWidget(routed(await testOverrides(api: api), '/listen?flow=pnr_status&type=1'));
    await tester.pumpAndSettle();

    expect(find.text('Please tell me the 10-digit PNR number.'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '4512345678');
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();
    expect(find.text(pnrConfirm.en), findsOneWidget);
  });

  testWidgets('unsupported request lists what I can do', (tester) async {
    useTallPhone(tester);
    final api = FakeApi()
      ..onParse = (text, expecting) => const IntentResult(
            flowId: null,
            params: {},
            missing: [],
            confirmation: L10nText("Sorry, I can't do that yet.", 'माफ़ कीजिए'),
          );
    await tester.pumpWidget(routed(await testOverrides(api: api, speech: FakeSpeech(['order pizza'])), '/listen'));
    await tester.pumpAndSettle();
    expect(find.text("Sorry, I can't do that yet."), findsOneWidget);
    expect(find.widgetWithText(ActionChip, 'PNR status'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}
