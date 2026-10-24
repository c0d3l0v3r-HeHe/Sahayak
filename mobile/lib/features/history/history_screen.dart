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

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final history = ref.watch(historyProvider);
    final text = Theme.of(context).textTheme;
    return ScreenFrame(
      title: l.historyTitle,
      child: history.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => Center(child: Text(l.networkError, style: text.bodyMedium)),
        data: (tasks) => tasks.isEmpty
            ? Center(child: Text(l.historyEmpty, style: text.bodyMedium))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(historyProvider.future),
                child: ListView.separated(
                  itemCount: tasks.length,
                  separatorBuilder: (_, _) => const Divider(),
                  itemBuilder: (context, i) {
                    final t = tasks[i];
                    return InkWell(
                      onTap: () => context.push(t.status == TaskStatus.succeeded ? '/result/${t.id}' : '/task/${t.id}'),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: Tokens.minTarget + 16),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: Tokens.space * 1.5),
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(t.title?.of(lang) ?? t.flowId, style: text.bodyLarge),
                                    Text(DateFormat.yMMMd(lang).add_jm().format(t.createdAt), style: text.bodySmall),
                                  ],
                                ),
                              ),
                              Text(statusLabel(l, t.status), style: text.bodySmall),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
      ),
    );
  }
}
