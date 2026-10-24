import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/storage.dart';
import '../../l10n/app_localizations.dart';

/// Greeting, one big mic button, supported tasks as chips, and the last task. Nothing else.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final flows = ref.watch(flowsProvider);
    final history = ref.watch(historyProvider);
    final text = Theme.of(context).textTheme;

    return ScreenFrame(
      actions: [
        IconButton(
          tooltip: l.historyTitle,
          iconSize: 28,
          constraints: const BoxConstraints(minWidth: Tokens.minTarget, minHeight: Tokens.minTarget),
          onPressed: () => context.push('/history'),
          icon: const Icon(Icons.history_rounded),
        ),
        IconButton(
          tooltip: l.settingsTitle,
          iconSize: 28,
          constraints: const BoxConstraints(minWidth: Tokens.minTarget, minHeight: Tokens.minTarget),
          onPressed: () => context.push('/settings'),
          icon: const Icon(Icons.settings_outlined),
        ),
      ],
      child: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(l.greeting, style: text.headlineMedium),
                const SizedBox(height: Tokens.space * 6),
                Center(
                  child: MicButton(
                    listening: false,
                    semanticLabel: l.micSemantics,
                    onTap: () => context.push('/listen'),
                  ),
                ),
                const SizedBox(height: Tokens.space),
                Text(l.micTapToSpeak, textAlign: TextAlign.center, style: text.titleLarge),
                const SizedBox(height: Tokens.space * 6),
                Text(l.supportedTasks, style: text.bodySmall),
                const SizedBox(height: Tokens.space),
                flows.when(
                  data: (c) => Wrap(
                    spacing: Tokens.space,
                    runSpacing: Tokens.space,
                    children: [
                      for (final f in c.flows)
                        ActionChip(
                          label: Text(f.title.of(lang)),
                          onPressed: () => context.push('/listen?flow=${f.id}&type=1'),
                        ),
                    ],
                  ),
                  loading: () => const SizedBox(height: Tokens.minTarget),
                  error: (_, _) => Text(l.networkError, style: text.bodySmall),
                ),
                const SizedBox(height: Tokens.space * 4),
                history.maybeWhen(
                  data: (tasks) => tasks.isEmpty ? const SizedBox.shrink() : _RecentTask(task: tasks.first, lang: lang),
                  orElse: () => const SizedBox.shrink(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RecentTask extends StatelessWidget {
  const _RecentTask({required this.task, required this.lang});

  final TaskDetail task;
  final String lang;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(Tokens.radius),
      onTap: () => context.push(task.status == TaskStatus.succeeded ? '/result/${task.id}' : '/task/${task.id}'),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: Tokens.minTarget),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: Tokens.space),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.lastTask, style: text.bodySmall),
                    Text(task.title?.of(lang) ?? task.flowId, style: text.bodyMedium),
                  ],
                ),
              ),
              Text(
                '${statusLabel(l, task.status)} · ${DateFormat.MMMd(lang).format(task.createdAt)}',
                style: text.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
