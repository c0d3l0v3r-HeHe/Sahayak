import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../l10n/app_localizations.dart';

/// "आप PNR 1234567890 की स्थिति जानना चाहते हैं?" with two large buttons.
class ConfirmationCard extends StatelessWidget {
  const ConfirmationCard({super.key, required this.text, required this.onYes, required this.onChange, this.busy = false});

  final String text;
  final VoidCallback onYes;
  final VoidCallback onChange;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Tokens.space * 3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l.confirmTitle, style: theme.bodySmall),
            const SizedBox(height: Tokens.space),
            Semantics(liveRegion: true, child: Text(text, style: theme.titleLarge)),
            const SizedBox(height: Tokens.space * 3),
            FilledButton(
              onPressed: busy
                  ? null
                  : () {
                      tapHaptic();
                      onYes();
                    },
              child: busy
                  ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2.5))
                  : Text(l.yes),
            ),
            const SizedBox(height: Tokens.space * 1.5),
            OutlinedButton(onPressed: busy ? null : onChange, child: Text(l.change)),
          ],
        ),
      ),
    );
  }
}
