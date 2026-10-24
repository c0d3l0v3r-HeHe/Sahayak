import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/models.dart';
import '../../core/voice.dart';
import '../../l10n/app_localizations.dart';

/// Returns null on success, or an error message to show.
typedef SubmitAnswer = Future<String?> Function(String value);

/// The moment a human must act: CAPTCHA, OTP, final confirmation, or a missing detail.
/// Answers go straight to the server and are never stored on the phone.
class HandoffSheet extends ConsumerStatefulWidget {
  const HandoffSheet({super.key, required this.handoff, required this.lang, required this.onSubmit, this.image});

  final Handoff handoff;
  final String lang;
  final SubmitAnswer onSubmit;
  final Widget? image;

  @override
  ConsumerState<HandoffSheet> createState() => _HandoffSheetState();
}

class _HandoffSheetState extends ConsumerState<HandoffSheet> {
  final _field = TextEditingController();
  bool _busy = false;
  bool _listening = false;
  String? _error;

  bool get _isOtp => widget.handoff.kind == 'otp';
  bool get _isCaptcha => widget.handoff.kind == 'captcha';

  @override
  void dispose() {
    _field.dispose();
    super.dispose();
  }

  Future<void> _submit(String value) async {
    if (value.trim().isEmpty) return;
    tapHaptic();
    setState(() {
      _busy = true;
      _error = null;
    });
    final error = await widget.onSubmit(value.trim());
    if (!mounted) return;
    if (error == null) {
      final closed = await Navigator.of(context).maybePop();
      if (!closed && mounted) setState(() => _busy = false);
    } else {
      setState(() {
        _busy = false;
        _error = error;
      });
    }
  }

  Future<void> _speak() async {
    final speech = ref.read(speechProvider);
    if (!await speech.init()) return;
    setState(() => _listening = true);
    await speech.listen(
      lang: widget.lang,
      onPartial: (t) => _field.text = _clean(t),
      onFinal: (t) {
        if (!mounted) return;
        setState(() {
          _listening = false;
          _field.text = _clean(t);
        });
      },
    );
  }

  /// "K 7 P Q R" -> "K7PQR"; spoken digits for OTPs.
  String _clean(String t) => (_isCaptcha || _isOtp) ? t.replaceAll(RegExp(r'\s+'), '').toUpperCase() : t;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final h = widget.handoff;

    final title = switch (h.kind) {
      'captcha' => l.captchaTitle,
      'otp' => l.otpTitle,
      'confirm' => l.confirmSubmitTitle,
      _ => h.prompt.of(widget.lang),
    };

    return Padding(
      padding: EdgeInsets.only(
        left: Tokens.screenPadding,
        right: Tokens.screenPadding,
        top: Tokens.space * 3,
        bottom: MediaQuery.of(context).viewInsets.bottom + Tokens.screenPadding,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(header: true, liveRegion: true, child: Text(title, style: text.headlineMedium)),
            if (h.kind != 'param' && h.prompt.of(widget.lang) != title) ...[
              const SizedBox(height: Tokens.space),
              Text(h.prompt.of(widget.lang), style: text.bodyMedium),
            ],
            const SizedBox(height: Tokens.space * 3),
            if (widget.image != null)
              Semantics(
                image: true,
                label: l.captchaImage,
                child: Container(
                  constraints: const BoxConstraints(minHeight: 120, maxHeight: 220),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(Tokens.radius),
                    border: Border.all(color: scheme.outline),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: widget.image,
                ),
              ),
            if (widget.image != null) const SizedBox(height: Tokens.space * 3),
            if (h.kind == 'confirm') ...[
              FilledButton(onPressed: _busy ? null : () => _submit('yes'), child: Text(l.yes)),
              const SizedBox(height: Tokens.space * 1.5),
              OutlinedButton(onPressed: _busy ? null : () => _submit('no'), child: Text(l.no)),
            ] else ...[
              TextField(
                key: const ValueKey('handoff-field'),
                controller: _field,
                autofocus: true,
                enabled: !_busy,
                textAlign: TextAlign.center,
                style: text.displaySmall?.copyWith(letterSpacing: _isOtp || _isCaptcha ? 6 : 0),
                keyboardType: _isOtp ? TextInputType.number : TextInputType.visiblePassword,
                textCapitalization: _isCaptcha ? TextCapitalization.characters : TextCapitalization.none,
                autocorrect: false,
                enableSuggestions: false,
                maxLength: _isOtp ? 8 : (_isCaptcha ? 12 : 200),
                inputFormatters: _isOtp ? [FilteringTextInputFormatter.digitsOnly] : null,
                decoration: InputDecoration(
                  hintText: _isOtp ? l.otpHint : (_isCaptcha ? l.captchaHint : l.answerHint),
                  counterText: '',
                ),
                onSubmitted: _submit,
              ),
              const SizedBox(height: Tokens.space * 2),
              FilledButton(
                onPressed: _busy ? null : () => _submit(_field.text),
                child: _busy
                    ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2.5))
                    : Text(l.send),
              ),
              const SizedBox(height: Tokens.space),
              OutlinedButton.icon(
                onPressed: _busy || _listening ? null : _speak,
                icon: Icon(_listening ? Icons.graphic_eq_rounded : Icons.mic_rounded),
                label: Text(_listening ? l.micListening : l.speak),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: Tokens.space * 2),
              Semantics(liveRegion: true, child: Text(_error!, style: text.bodyMedium?.copyWith(color: scheme.error))),
            ],
          ],
        ),
      ),
    );
  }
}
