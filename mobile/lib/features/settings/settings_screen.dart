import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/api_client.dart';
import '../../core/storage.dart';
import '../../app/widgets.dart';
import '../../l10n/app_localizations.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final _server = TextEditingController(text: ref.read(settingsProvider).serverUrl);

  @override
  void dispose() {
    _server.dispose();
    super.dispose();
  }

  Future<void> _delete() async {
    final l = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        content: Text(l.deleteConfirm, style: Theme.of(c).textTheme.bodyMedium),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(l.no)),
          TextButton(onPressed: () => Navigator.pop(c, true), child: Text(l.yes)),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(apiProvider).deleteMyData();
      ref.invalidate(historyProvider);
      messenger.showSnackBar(SnackBar(content: Text(l.deleteDone)));
    } catch (_) {
      messenger.showSnackBar(SnackBar(content: Text(l.networkError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = ref.watch(settingsProvider);
    final n = ref.read(settingsProvider.notifier);
    final text = Theme.of(context).textTheme;
    final demo = ref.watch(flowsProvider).value?.demoMode ?? false;
    const gap = SizedBox(height: Tokens.space * 4);

    return ScreenFrame(
      title: l.settingsTitle,
      child: ListView(
        children: [
          Text(l.settingsLanguage, style: text.titleLarge),
          const SizedBox(height: Tokens.space),
          SegmentedButton<String>(
            segments: [
              ButtonSegment(value: 'hi', label: Text(l.languageHindi)),
              ButtonSegment(value: 'en', label: Text(l.languageEnglish)),
            ],
            selected: {s.language},
            onSelectionChanged: (v) => n.setLanguage(v.first),
          ),
          gap,
          Text(l.settingsSpeechRate, style: text.titleLarge),
          const SizedBox(height: Tokens.space),
          SegmentedButton<SpeechRate>(
            segments: [
              ButtonSegment(value: SpeechRate.slow, label: Text(l.rateSlow)),
              ButtonSegment(value: SpeechRate.normal, label: Text(l.rateNormal)),
              ButtonSegment(value: SpeechRate.fast, label: Text(l.rateFast)),
            ],
            selected: {s.speechRate},
            onSelectionChanged: (v) => n.setSpeechRate(v.first),
          ),
          const SizedBox(height: Tokens.space),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l.settingsReadAloud, style: text.bodyMedium),
            value: s.readAloud,
            onChanged: n.setReadAloud,
          ),
          gap,
          Text(l.settingsTextSize, style: text.titleLarge),
          Slider(
            value: s.textScale,
            min: 1.0,
            max: 2.0,
            divisions: 4,
            label: '${(s.textScale * 100).round()}%',
            onChanged: n.setTextScale,
          ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(Tokens.space * 2),
              child: Text(l.textSizePreview, style: text.bodyMedium),
            ),
          ),
          gap,
          if (kDebugMode) ...[
            Text(l.settingsServer, style: text.titleLarge),
            const SizedBox(height: Tokens.space),
            TextField(controller: _server, keyboardType: TextInputType.url, style: text.bodyMedium),
            const SizedBox(height: Tokens.space),
            OutlinedButton(
              onPressed: () {
                n.setServerUrl(_server.text.trim());
                ref.invalidate(flowsProvider);
              },
              child: Text(l.save),
            ),
            if (demo) ...[
              const SizedBox(height: Tokens.space),
              Text(l.demoBanner, style: text.bodySmall),
            ],
            gap,
          ],
          OutlinedButton(
            style: OutlinedButton.styleFrom(foregroundColor: Tokens.error),
            onPressed: () {
              tapHaptic();
              _delete();
            },
            child: Text(l.deleteData),
          ),
          gap,
          Text(l.privacyTitle, style: text.titleLarge),
          const SizedBox(height: Tokens.space),
          Text(l.privacyNote, style: text.bodyMedium),
          gap,
        ],
      ),
    );
  }
}
