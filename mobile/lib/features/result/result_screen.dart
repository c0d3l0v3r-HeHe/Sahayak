import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/models.dart';
import '../../core/storage.dart';
import '../../core/task_watcher.dart';
import '../../core/voice.dart';
import '../../l10n/app_localizations.dart';

class ResultScreen extends ConsumerWidget {
  const ResultScreen({super.key, required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final task = ref.watch(taskProvider(taskId));
    return task.when(
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (_, _) => ScreenFrame(child: Center(child: Text(l.networkError))),
      data: (t) => ResultView(task: t),
    );
  }
}

/// The answer in display-size text, read aloud once, with Hear again / Share / Done.
class ResultView extends ConsumerStatefulWidget {
  const ResultView({super.key, required this.task});

  final TaskDetail task;

  @override
  ConsumerState<ResultView> createState() => _ResultViewState();
}

class _ResultViewState extends ConsumerState<ResultView> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _speak());
  }

  String _text(String lang) =>
      widget.task.resultText?.of(lang) ?? widget.task.error?.of(lang) ?? AppLocalizations.of(context).taskFailedTitle;

  Future<void> _speak() async {
    final s = ref.read(settingsProvider);
    try {
      await ref.read(ttsProvider).speak(_text(s.language), lang: s.language, rate: s.speechRate.value);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final text = Theme.of(context).textTheme;
    final schemes = (widget.task.resultData['schemes'] as List?)?.cast<Map<String, dynamic>>();
    final answer = _text(lang);

    return ScreenFrame(
      title: widget.task.title?.of(lang),
      leading: const SizedBox.shrink(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l.resultTitle, style: text.bodySmall),
                  const SizedBox(height: Tokens.space),
                  if (schemes == null || schemes.isEmpty)
                    Semantics(liveRegion: true, child: SelectableText(answer, style: text.displaySmall))
                  else
                    for (final s in schemes) ...[
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(Tokens.space * 2),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('${s['name'] ?? ''}', style: text.titleLarge),
                              const SizedBox(height: Tokens.space),
                              Text('${s['benefit'] ?? ''}', style: text.bodyMedium),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: Tokens.space * 1.5),
                    ],
                ],
              ),
            ),
          ),
          const SizedBox(height: Tokens.space * 2),
          FilledButton.icon(
            onPressed: () {
              tapHaptic();
              _speak();
            },
            icon: const Icon(Icons.volume_up_rounded),
            label: Text(l.listenAgain),
          ),
          const SizedBox(height: Tokens.space * 1.5),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => SharePlus.instance.share(ShareParams(text: _shareText(lang, schemes))),
                  icon: const Icon(Icons.share_outlined),
                  label: Text(l.share),
                ),
              ),
              const SizedBox(width: Tokens.space * 1.5),
              Expanded(
                child: OutlinedButton(onPressed: () => context.go('/'), child: Text(l.done)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _shareText(String lang, List<Map<String, dynamic>>? schemes) {
    final buf = StringBuffer(_text(lang));
    for (final s in schemes ?? const <Map<String, dynamic>>[]) {
      if (s['link'] != null) buf.write('\n${s['name']}: ${s['link']}');
    }
    return buf.toString();
  }
}
