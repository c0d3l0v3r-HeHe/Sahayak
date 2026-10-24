import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/models.dart';
import '../l10n/app_localizations.dart';
import 'theme.dart';

/// Standard screen frame: generous padding, quiet app bar.
class ScreenFrame extends StatelessWidget {
  const ScreenFrame({super.key, required this.child, this.title, this.actions, this.leading});

  final Widget child;
  final String? title;
  final List<Widget>? actions;
  final Widget? leading;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: (title != null || actions != null || leading != null)
          ? AppBar(title: title == null ? null : Text(title!), actions: actions, leading: leading)
          : null,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Tokens.screenPadding, vertical: Tokens.space * 2),
          child: child,
        ),
      ),
    );
  }
}

bool reduceMotion(BuildContext context) => MediaQuery.of(context).disableAnimations;

void tapHaptic() => HapticFeedback.mediumImpact();

String statusLabel(AppLocalizations l, TaskStatus s) => switch (s) {
      TaskStatus.queued => l.statusQueued,
      TaskStatus.running => l.statusRunning,
      TaskStatus.awaitingUser => l.statusAwaitingUser,
      TaskStatus.succeeded => l.statusSucceeded,
      TaskStatus.failed => l.statusFailed,
      TaskStatus.cancelled => l.statusCancelled,
      TaskStatus.expired => l.statusExpired,
    };

/// The big microphone button with a slow pulsing ring while listening.
class MicButton extends StatefulWidget {
  const MicButton({super.key, required this.listening, required this.onTap, required this.semanticLabel});

  final bool listening;
  final VoidCallback onTap;
  final String semanticLabel;

  @override
  State<MicButton> createState() => _MicButtonState();
}

class _MicButtonState extends State<MicButton> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1600));

  @override
  void didUpdateWidget(covariant MicButton old) {
    super.didUpdateWidget(old);
    _sync();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  void _sync() {
    if (widget.listening && !reduceMotion(context)) {
      if (!_pulse.isAnimating) _pulse.repeat();
    } else {
      _pulse.stop();
      _pulse.value = 0;
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    final onAccent = Theme.of(context).colorScheme.onPrimary;
    return Semantics(
      button: true,
      label: widget.semanticLabel,
      excludeSemantics: true,
      child: SizedBox(
        width: Tokens.micSize * 1.5,
        height: Tokens.micSize * 1.5,
        child: Stack(
          alignment: Alignment.center,
          children: [
            AnimatedBuilder(
              animation: _pulse,
              builder: (_, _) {
                final t = _pulse.value;
                return Opacity(
                  opacity: widget.listening ? (1 - t) * 0.5 : 0,
                  child: Container(
                    width: Tokens.micSize * (1 + 0.45 * t),
                    height: Tokens.micSize * (1 + 0.45 * t),
                    decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: accent, width: 2)),
                  ),
                );
              },
            ),
            Material(
              color: accent,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: () {
                  tapHaptic();
                  widget.onTap();
                },
                child: SizedBox(
                  width: Tokens.micSize,
                  height: Tokens.micSize,
                  child: Icon(widget.listening ? Icons.stop_rounded : Icons.mic_rounded, size: 52, color: onAccent),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
