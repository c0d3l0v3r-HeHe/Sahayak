import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahayak/l10n/app_localizations.dart';

Map<String, dynamic> arb(String lang) =>
    jsonDecode(File('lib/l10n/app_$lang.arb').readAsStringSync()) as Map<String, dynamic>;

Set<String> keys(Map<String, dynamic> m) => m.keys.where((k) => !k.startsWith('@')).toSet();

void main() {
  test('English and Hindi have exactly the same keys', () {
    final en = keys(arb('en')), hi = keys(arb('hi'));
    expect(en.difference(hi), isEmpty, reason: 'missing in Hindi');
    expect(hi.difference(en), isEmpty, reason: 'missing in English');
  });

  test('no empty translations', () {
    for (final lang in ['en', 'hi']) {
      final m = arb(lang);
      for (final k in keys(m)) {
        expect((m[k] as String).trim(), isNotEmpty, reason: '$lang.$k is empty');
      }
    }
  });

  test('Hindi strings are actually Hindi', () {
    final hi = arb('hi');
    final devanagari = RegExp(r'[ऀ-ॿ]');
    final translated = keys(hi).where((k) => devanagari.hasMatch(hi[k] as String)).length;
    // A few strings (e.g. "English", "Sahayak" in brand contexts) stay Latin on purpose.
    expect(translated / keys(hi).length, greaterThan(0.9));
  });

  testWidgets('both locales load', (tester) async {
    for (final locale in AppLocalizations.supportedLocales) {
      final l = await AppLocalizations.delegate.load(locale);
      expect(l.appTitle, isNotEmpty);
      expect(l.greeting, isNotEmpty);
    }
    expect(AppLocalizations.supportedLocales.map((l) => l.languageCode), containsAll(['en', 'hi']));
    expect(AppLocalizations.delegate.isSupported(const Locale('hi')), isTrue);
  });
}
