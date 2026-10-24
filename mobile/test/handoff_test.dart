import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahayak/core/models.dart';
import 'package:sahayak/features/handoff/handoff_sheet.dart';

import 'helpers.dart';

Handoff handoff(String kind) => Handoff(
      id: 'h1',
      kind: kind,
      prompt: const L10nText('Please read what is written in the picture.', 'कृपया तस्वीर में जो लिखा है, वह पढ़कर बताइए।'),
      imageId: kind == 'captcha' ? 'img1' : null,
    );

void main() {
  testWidgets('captcha: big image, letters typed and sent', (tester) async {
    useTallPhone(tester);
    final sent = <String>[];
    await tester.pumpWidget(wrap(
      Scaffold(
        body: HandoffSheet(
          handoff: handoff('captcha'),
          lang: 'en',
          image: const ColoredBox(color: Colors.grey, child: SizedBox(height: 120)),
          onSubmit: (v) async {
            sent.add(v);
            return null;
          },
        ),
      ),
      overrides: await testOverrides(),
    ));
    expect(find.text('Please read these letters'), findsOneWidget);
    expect(find.bySemanticsLabel('Picture with letters to read'), findsOneWidget);
    await tester.enterText(find.byKey(const ValueKey('handoff-field')), ' K7PQR ');
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();
    expect(sent, ['K7PQR']);
  });

  testWidgets('captcha: server rejection shows a friendly message', (tester) async {
    useTallPhone(tester);
    await tester.pumpWidget(wrap(
      Scaffold(
        body: HandoffSheet(
          handoff: handoff('captcha'),
          lang: 'en',
          onSubmit: (v) async => 'That does not look right. Please check and try again.',
        ),
      ),
      overrides: await testOverrides(),
    ));
    await tester.enterText(find.byKey(const ValueKey('handoff-field')), '!!');
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();
    expect(find.text('That does not look right. Please check and try again.'), findsOneWidget);
  });

  testWidgets('captcha can be answered by voice', (tester) async {
    useTallPhone(tester);
    final sent = <String>[];
    await tester.pumpWidget(wrap(
      Scaffold(
        body: HandoffSheet(
          handoff: handoff('captcha'),
          lang: 'en',
          onSubmit: (v) async {
            sent.add(v);
            return null;
          },
        ),
      ),
      overrides: await testOverrides(speech: FakeSpeech(['k 7 p q r'])),
    ));
    await tester.tap(find.text('Speak'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();
    expect(sent, ['K7PQR']);
  });

  testWidgets('otp: numeric field only accepts digits', (tester) async {
    useTallPhone(tester);
    await tester.pumpWidget(wrap(
      Scaffold(body: HandoffSheet(handoff: handoff('otp'), lang: 'en', onSubmit: (v) async => null)),
      overrides: await testOverrides(),
    ));
    expect(find.text("You will get an SMS. Tell me the 6-digit code."), findsOneWidget);
    await tester.enterText(find.byKey(const ValueKey('handoff-field')), '48a29b13');
    expect(find.text('482913'), findsOneWidget);
  });

  testWidgets('confirm: Yes / No in Hindi', (tester) async {
    useTallPhone(tester);
    final sent = <String>[];
    await tester.pumpWidget(wrap(
      Scaffold(
        body: HandoffSheet(
          handoff: handoff('confirm'),
          lang: 'hi',
          onSubmit: (v) async {
            sent.add(v);
            return null;
          },
        ),
      ),
      overrides: await testOverrides(lang: 'hi'),
      lang: 'hi',
    ));
    expect(find.text('क्या मैं इसे जमा कर दूँ?'), findsOneWidget);
    await tester.tap(find.text('नहीं'));
    await tester.pumpAndSettle();
    expect(sent, ['no']);
  });
}
