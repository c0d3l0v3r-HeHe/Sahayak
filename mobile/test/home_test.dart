import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahayak/core/models.dart';
import 'package:sahayak/features/home/home_screen.dart';

import 'helpers.dart';

void main() {
  testWidgets('home shows greeting, mic, task chips and the last task', (tester) async {
    useTallPhone(tester);
    final api = FakeApi()
      ..historyItems = [
        TaskDetail(
          id: 't1',
          flowId: 'pnr_status',
          title: const L10nText('PNR status', 'PNR स्थिति'),
          status: TaskStatus.succeeded,
          events: const [],
          createdAt: DateTime(2026, 10, 24),
        ),
      ];
    await tester.pumpWidget(wrap(const HomeScreen(), overrides: await testOverrides(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Namaste! How can I help?'), findsOneWidget);
    expect(find.text('Tap and speak'), findsOneWidget);
    expect(find.bySemanticsLabel('Microphone. Tap and say what you need.'), findsOneWidget);
    expect(find.widgetWithText(ActionChip, 'PNR status'), findsOneWidget);
    expect(find.widgetWithText(ActionChip, 'Where is my train?'), findsOneWidget);
    expect(find.text('Last task'), findsOneWidget);
  });

  testWidgets('home is in Hindi when Hindi is chosen', (tester) async {
    useTallPhone(tester);
    await tester.pumpWidget(wrap(const HomeScreen(), overrides: await testOverrides(lang: 'hi'), lang: 'hi'));
    await tester.pumpAndSettle();
    expect(find.text('नमस्ते! मैं कैसे मदद करूँ?'), findsOneWidget);
    expect(find.text('दबाकर बोलिए'), findsOneWidget);
    expect(find.widgetWithText(ActionChip, 'PNR स्थिति'), findsOneWidget);
  });

  testWidgets('home survives 200% text without overflow', (tester) async {
    useTallPhone(tester);
    await tester.pumpWidget(wrap(const HomeScreen(), overrides: await testOverrides(), textScale: 2.0));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('mic button is at least 120dp', (tester) async {
    useTallPhone(tester);
    await tester.pumpWidget(wrap(const HomeScreen(), overrides: await testOverrides()));
    await tester.pumpAndSettle();
    final size = tester.getSize(find.byIcon(Icons.mic_rounded).first.hitTestable());
    expect(size.width, greaterThanOrEqualTo(40)); // the icon
    final button = tester.getSize(find.ancestor(of: find.byIcon(Icons.mic_rounded), matching: find.byType(InkWell)).first);
    expect(button.width, greaterThanOrEqualTo(120));
  });
}
