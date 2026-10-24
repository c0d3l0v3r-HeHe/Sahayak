import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/storage.dart';
import '../../core/voice.dart';
import '../../l10n/app_localizations.dart';

/// Two steps: pick a language, then a short explanation + microphone permission.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  int _step = 0;

  Future<void> _finish({required bool askMic}) async {
    if (askMic) await ref.read(speechProvider).init(); // triggers the system permission prompt
    ref.read(settingsProvider.notifier).completeOnboarding();
    if (mounted) context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final text = Theme.of(context).textTheme;
    return ScreenFrame(
      child: AnimatedSwitcher(
        duration: Tokens.fade,
        child: _step == 0
            ? Column(
                key: const ValueKey('lang'),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: Tokens.space * 4),
                  Text(l.languageTitle, style: text.headlineMedium),
                  const SizedBox(height: Tokens.space * 4),
                  _LanguageCard(label: 'हिन्दी', selected: lang == 'hi', onTap: () => _pick('hi')),
                  const SizedBox(height: Tokens.space * 2),
                  _LanguageCard(label: 'English', selected: lang == 'en', onTap: () => _pick('en')),
                  const Spacer(),
                  FilledButton(onPressed: () => setState(() => _step = 1), child: Text(l.continueButton)),
                ],
              )
            : Column(
                key: const ValueKey('intro'),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: Tokens.space * 4),
                  Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(l.onboardingTitle, style: text.headlineMedium),
                          const SizedBox(height: Tokens.space * 3),
                          Text(l.onboardingBody, style: text.bodyLarge),
                          const SizedBox(height: Tokens.space * 3),
                          Text(l.onboardingMicNote, style: text.bodySmall),
                        ],
                      ),
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: () => _finish(askMic: true),
                    icon: const Icon(Icons.mic_rounded),
                    label: Text(l.onboardingMicButton),
                  ),
                  const SizedBox(height: Tokens.space),
                  TextButton(onPressed: () => _finish(askMic: false), child: Text(l.notNow)),
                ],
              ),
      ),
    );
  }

  void _pick(String lang) {
    tapHaptic();
    ref.read(settingsProvider.notifier).setLanguage(lang);
  }
}

class _LanguageCard extends StatelessWidget {
  const _LanguageCard({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      selected: selected,
      button: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(Tokens.radius),
        child: AnimatedContainer(
          duration: Tokens.fade,
          constraints: const BoxConstraints(minHeight: 96),
          padding: const EdgeInsets.all(Tokens.space * 3),
          decoration: BoxDecoration(
            color: scheme.surface,
            borderRadius: BorderRadius.circular(Tokens.radius),
            border: Border.all(color: selected ? scheme.primary : scheme.outline, width: selected ? 2 : 1),
          ),
          child: Row(
            children: [
              Expanded(child: Text(label, style: Theme.of(context).textTheme.headlineMedium)),
              if (selected) Icon(Icons.check_circle_rounded, color: scheme.primary, size: 32),
            ],
          ),
        ),
      ),
    );
  }
}
