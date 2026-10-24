import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/storage.dart';
import '../l10n/app_localizations.dart';
import 'router.dart';
import 'theme.dart';

class SahayakApp extends ConsumerWidget {
  const SahayakApp({super.key, this.useGoogleFonts = true});

  final bool useGoogleFonts;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    return MaterialApp.router(
      onGenerateTitle: (c) => AppLocalizations.of(c).appTitle,
      debugShowCheckedModeBanner: false,
      theme: buildTheme(Brightness.light, useGoogleFonts: useGoogleFonts),
      darkTheme: buildTheme(Brightness.dark, useGoogleFonts: useGoogleFonts),
      locale: Locale(settings.language),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: ref.watch(routerProvider),
      builder: (context, child) => applyTextScale(context, settings.textScale, child!),
    );
  }
}

/// System text scale x the user's in-app choice, capped at 200%.
Widget applyTextScale(BuildContext context, double userScale, Widget child) {
  final mq = MediaQuery.of(context);
  final system = mq.textScaler.scale(1);
  final total = (system * userScale).clamp(1.0, 2.0);
  return MediaQuery(data: mq.copyWith(textScaler: TextScaler.linear(total)), child: child);
}
