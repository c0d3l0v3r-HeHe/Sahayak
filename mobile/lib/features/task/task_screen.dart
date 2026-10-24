import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/auth_image.dart';
import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/storage.dart';
import '../../core/task_watcher.dart';
import '../../core/voice.dart';
import '../../l10n/app_localizations.dart';
import '../handoff/handoff_sheet.dart';

/// Plain-language step list, a live screenshot, spoken narration and the hand-off sheet.
class TaskScreen extends ConsumerStatefulWidget {
  const TaskScreen({super.key, required this.taskId});

  final String taskId;

  @override
  ConsumerState<TaskScreen> createState() => _TaskScreenState();
}

class _TaskScreenState extends ConsumerState<TaskScreen> {
  int _spokenSteps = 0;
  String? _sheetFor; // hand-off id currently shown

  late final TtsService _tts;

  @override
  void initState() {
    super.initState();
    _tts = ref.read(ttsProvider); // captured now: ref can't be used in dispose()
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  void _onUpdate(TaskDetail? prev, TaskDetail task) {
    final settings = ref.read(settingsProvider);
    final steps = task.steps;
    if (settings.readAloud && steps.length > _spokenSteps && task.handoff == null) {
      final msg = steps.last.message!.of(settings.language);
      ref.read(ttsProvider).speak(msg, lang: settings.language, rate: settings.speechRate.value).catchError((_) {});
    }
    _spokenSteps = steps.length;

    if (task.status == TaskStatus.succeeded) {
      context.pushReplacement('/result/${task.id}');
      return;
    }
    final h = task.handoff;
    if (task.status == TaskStatus.awaitingUser && h != null && h.id != _sheetFor) {
      _sheetFor = h.id;
      _showHandoff(task, h);
    }
  }

  Future<void> _showHandoff(TaskDetail task, Handoff h) async {
    final settings = ref.read(settingsProvider);
    final l = AppLocalizations.of(context);
    tapHaptic();
    if (settings.readAloud) {
      ref
          .read(ttsProvider)
          .speak(h.prompt.of(settings.language), lang: settings.language, rate: settings.speechRate.value)
          .catchError((_) {});
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      builder: (_) => HandoffSheet(
        handoff: h,
        lang: settings.language,
        image: h.imageId == null ? null : AuthImage(taskId: task.id, screenshotId: h.imageId!),
        onSubmit: (value) async {
          try {
            await ref.read(apiProvider).answer(task.id, h.id, value);
            ref.read(taskProvider(task.id).notifier).refresh();
            return null;
          } on ApiException catch (e) {
            if (e.invalidAnswer) return l.answerInvalid;
            if (e.expired) return l.handoffExpired;
            return l.networkError;
          }
        },
      ),
    );
  }

  Future<void> _cancel() async {
    try {
      await ref.read(apiProvider).cancel(widget.taskId);
    } catch (_) {}
    if (mounted) context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final async = ref.watch(taskProvider(widget.taskId));
    ref.listen(taskProvider(widget.taskId), (prev, next) {
      final task = next.value;
      if (task != null) _onUpdate(prev?.value, task);
    });
    final text = Theme.of(context).textTheme;

    return ScreenFrame(
      title: async.value?.title?.of(lang),
      leading: const SizedBox.shrink(),
      child: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => _Problem(message: l.networkError, onDone: () => context.go('/')),
        data: (task) {
          if (task.status.terminal && task.status != TaskStatus.succeeded) {
            return _Problem(
              message: task.status == TaskStatus.cancelled ? l.taskCancelled : (task.error?.of(lang) ?? l.taskFailedTitle),
              onDone: () => context.go('/'),
              onRetry: task.status == TaskStatus.cancelled ? null : () => context.pushReplacement('/listen'),
            );
          }
          final shot = task.latestScreenshot;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                switch (task.status) {
                  TaskStatus.queued => l.taskQueued,
                  TaskStatus.awaitingUser => l.taskNeedsYou,
                  _ => l.taskWorking,
                },
                style: text.bodySmall,
              ),
              const SizedBox(height: Tokens.space * 2),
              Expanded(child: StepList(steps: task.steps, lang: lang, running: !task.status.terminal)),
              if (shot != null) ...[
                const SizedBox(height: Tokens.space * 2),
                _Thumbnail(taskId: task.id, screenshotId: shot),
              ],
              const SizedBox(height: Tokens.space),
              TextButton(onPressed: _cancel, child: Text(l.cancel)),
            ],
          );
        },
      ),
    );
  }
}

/// ✓ done, ● current.
class StepList extends StatelessWidget {
  const StepList({super.key, required this.steps, required this.lang, required this.running});

  final List<TaskEvent> steps;
  final String lang;
  final bool running;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return ListView.separated(
      itemCount: steps.length,
      separatorBuilder: (_, _) => const SizedBox(height: Tokens.space * 2),
      itemBuilder: (context, i) {
        final current = running && i == steps.length - 1;
        return Semantics(
          label: '${current ? l.stepCurrent : l.stepDone}: ${steps[i].message!.of(lang)}',
          excludeSemantics: true,
          child: AnimatedOpacity(
            opacity: 1,
            duration: Tokens.fade,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: current
                      ? Icon(Icons.circle, size: 16, color: scheme.primary)
                      : Icon(Icons.check_rounded, size: 22, color: scheme.primary),
                ),
                const SizedBox(width: Tokens.space * 2),
                Expanded(
                  child: Text(
                    steps[i].message!.of(lang),
                    style: current ? text.bodyLarge : text.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Thumbnail extends StatelessWidget {
  const _Thumbnail({required this.taskId, required this.screenshotId});

  final String taskId;
  final String screenshotId;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: l.liveView,
      excludeSemantics: true,
      child: GestureDetector(
        onTap: () => showDialog<void>(
          context: context,
          builder: (_) => Dialog.fullscreen(
            child: Stack(children: [
              Positioned.fill(
                child: InteractiveViewer(
                  maxScale: 4,
                  child: AuthImage(taskId: taskId, screenshotId: screenshotId),
                ),
              ),
              Positioned(
                top: 8,
                right: 8,
                child: SafeArea(
                  child: IconButton.filledTonal(
                    tooltip: l.back,
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
              ),
            ]),
          ),
        ),
        child: Container(
          height: 140,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(Tokens.radius),
            border: Border.all(color: scheme.outline),
          ),
          clipBehavior: Clip.antiAlias,
          child: AuthImage(taskId: taskId, screenshotId: screenshotId, fit: BoxFit.cover),
        ),
      ),
    );
  }
}

class _Problem extends StatelessWidget {
  const _Problem({required this.message, required this.onDone, this.onRetry});

  final String message;
  final VoidCallback onDone;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l.taskFailedTitle, style: text.bodySmall),
        const SizedBox(height: Tokens.space),
        Semantics(liveRegion: true, child: Text(message, style: text.titleLarge)),
        const Spacer(),
        if (onRetry != null) ...[
          FilledButton(onPressed: onRetry, child: Text(l.tryAgain)),
          const SizedBox(height: Tokens.space * 1.5),
        ],
        OutlinedButton(onPressed: onDone, child: Text(l.done)),
      ],
    );
  }
}
