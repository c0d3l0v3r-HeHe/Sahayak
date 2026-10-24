import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahayak/app/theme.dart';
import 'package:sahayak/core/models.dart';
import 'package:sahayak/features/result/result_screen.dart';

import 'helpers.dart';

TaskDetail done({Map<String, dynamic> data = const {}}) => TaskDetail(
      id: 't1',
      flowId: 'train_running_status',
      title: const L10nText('Where is my train?', 'मेरी ट्रेन कहाँ है?'),
      status: TaskStatus.succeeded,
      events: const [],
      createdAt: DateTime(2026, 10, 24),
      resultText: const L10nText(
        '12301 RAJDHANI EXPRES: Arrived at NEW DELHI(NDLS) at 11:08 24-Oct (Delay: 01:03).',
        'ट्रेन 12301 RAJDHANI EXPRES: Arrived at NEW DELHI(NDLS) at 11:08 24-Oct (Delay: 01:03)।',
      ),
      resultData: data,
    );

void main() {
  testWidgets('result in display size, read aloud, with actions', (tester) async {
    useTallPhone(tester);
    final tts = FakeTts();
    await tester.pumpWidget(wrap(ResultView(task: done()), overrides: await testOverrides(tts: tts)));
    await tester.pumpAndSettle();

    final answer = find.byType(SelectableText);
    expect(answer, findsOneWidget);
    expect(find.textContaining('Arrived at NEW DELHI'), findsOneWidget);
    final style = tester.widget<SelectableText>(answer).style!;
    expect(style.fontSize, Tokens.display);
    expect(tts.spoken.length, 1);

    await tester.tap(find.text('Hear again'));
    await tester.pumpAndSettle();
    expect(tts.spoken.length, 2);
    expect(find.text('Share'), findsOneWidget);
    expect(find.text('Done'), findsOneWidget);
  });

  testWidgets('scheme results are shown as cards', (tester) async {
    useTallPhone(tester);
    final task = done(data: {
      'schemes': [
        {'name': 'Delhi Old Age Pension', 'benefit': '₹2,500 a month', 'link': 'https://example.org'},
        {'name': 'Ayushman Vay Vandana', 'benefit': 'Free health cover', 'link': 'https://example.org/2'},
      ],
    });
    await tester.pumpWidget(wrap(ResultView(task: task), overrides: await testOverrides()));
    await tester.pumpAndSettle();
    expect(find.text('Delhi Old Age Pension'), findsOneWidget);
    expect(find.byType(Card), findsNWidgets(2));
  });

  testWidgets('result reads in Hindi', (tester) async {
    useTallPhone(tester);
    final tts = FakeTts();
    await tester.pumpWidget(wrap(ResultView(task: done()), overrides: await testOverrides(tts: tts, lang: 'hi'), lang: 'hi'));
    await tester.pumpAndSettle();
    expect(tts.spoken.single, startsWith('ट्रेन 12301'));
    expect(find.text('फिर से सुनें'), findsOneWidget);
  });
}
