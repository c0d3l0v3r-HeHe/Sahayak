import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design tokens. One accent colour, no gradients, no shadows — 1px borders instead.
class Tokens {
  static const bgLight = Color(0xFFFAFAF7);
  static const bgDark = Color(0xFF111111);
  static const surfaceLight = Color(0xFFFFFFFF);
  static const surfaceDark = Color(0xFF1A1A1A);
  static const textLight = Color(0xFF111111);
  static const textDark = Color(0xFFF2F2F2);
  static const text2Light = Color(0xFF5F5F5F);
  static const text2Dark = Color(0xFFA0A0A0);
  static const accentLight = Color(0xFF0F7B5F);
  static const accentDark = Color(0xFF3DBE93);
  static const error = Color(0xFFB3261E);
  static const borderLight = Color(0xFFE6E6E1);
  static const borderDark = Color(0xFF2C2C2A);

  static const radius = 16.0;
  static const space = 8.0; // 8-point grid
  static const screenPadding = 24.0;
  static const minTarget = 56.0;
  static const micSize = 120.0;

  static const body = 20.0;
  static const bodyLarge = 24.0;
  static const title = 32.0;
  static const display = 40.0;
  static const lineHeight = 1.4;

  static const fade = Duration(milliseconds: 180);
}

ThemeData buildTheme(Brightness brightness, {bool useGoogleFonts = true}) {
  final dark = brightness == Brightness.dark;
  final accent = dark ? Tokens.accentDark : Tokens.accentLight;
  final text = dark ? Tokens.textDark : Tokens.textLight;
  final text2 = dark ? Tokens.text2Dark : Tokens.text2Light;
  final surface = dark ? Tokens.surfaceDark : Tokens.surfaceLight;
  final border = dark ? Tokens.borderDark : Tokens.borderLight;

  final scheme = ColorScheme(
    brightness: brightness,
    primary: accent,
    onPrimary: dark ? Tokens.bgDark : Colors.white,
    secondary: accent,
    onSecondary: dark ? Tokens.bgDark : Colors.white,
    error: Tokens.error,
    onError: Colors.white,
    surface: surface,
    onSurface: text,
    onSurfaceVariant: text2,
    outline: border,
    outlineVariant: border,
  );

  TextStyle s(double size, {FontWeight weight = FontWeight.w400, Color? color}) =>
      TextStyle(fontSize: size, height: Tokens.lineHeight, fontWeight: weight, color: color ?? text);

  var textTheme = TextTheme(
    displaySmall: s(Tokens.display, weight: FontWeight.w600),
    headlineMedium: s(Tokens.title, weight: FontWeight.w600),
    titleLarge: s(Tokens.bodyLarge, weight: FontWeight.w600),
    bodyLarge: s(Tokens.bodyLarge),
    bodyMedium: s(Tokens.body),
    bodySmall: s(16, color: text2),
    labelLarge: s(Tokens.body, weight: FontWeight.w600),
    labelMedium: s(16, color: text2),
  );
  if (useGoogleFonts) {
    // Inter for Latin, Noto Sans Devanagari for Hindi.
    final inter = GoogleFonts.inter().fontFamily;
    final devanagari = GoogleFonts.notoSansDevanagari().fontFamily!;
    textTheme = textTheme.apply(fontFamily: inter, fontFamilyFallback: [devanagari]);
  }

  final shape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(Tokens.radius),
  );
  const minSize = Size(Tokens.minTarget, Tokens.minTarget);

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: dark ? Tokens.bgDark : Tokens.bgLight,
    textTheme: textTheme,
    splashFactory: NoSplash.splashFactory,
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? Tokens.bgDark : Tokens.bgLight,
      foregroundColor: text,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: textTheme.titleLarge,
    ),
    cardTheme: CardThemeData(
      color: surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Tokens.radius),
        side: BorderSide(color: border),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: minSize,
        shape: shape,
        textStyle: textTheme.labelLarge,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: minSize,
        shape: shape,
        foregroundColor: text,
        side: BorderSide(color: border),
        textStyle: textTheme.labelLarge,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: minSize, textStyle: textTheme.labelLarge),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Tokens.radius),
        borderSide: BorderSide(color: border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Tokens.radius),
        borderSide: BorderSide(color: border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Tokens.radius),
        borderSide: BorderSide(color: accent, width: 2),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: surface,
      side: BorderSide(color: border),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Tokens.radius)),
      labelStyle: textTheme.labelMedium?.copyWith(color: text),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: surface,
      elevation: 0,
      modalElevation: 0,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(Tokens.radius)),
      ),
    ),
    dividerTheme: DividerThemeData(color: border, thickness: 1, space: 1),
    dialogTheme: DialogThemeData(
      backgroundColor: surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Tokens.radius),
        side: BorderSide(color: border),
      ),
    ),
  );
}
