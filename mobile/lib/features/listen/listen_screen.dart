import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/storage.dart';
import '../../core/voice.dart';
import '../../l10n/app_localizations.dart';
import 'confirmation_card.dart';

enum ListenPhase { listening, thinking, asking, confirming, noMatch, error }

/// Listens, understands, asks for missing details one at a time, then confirms.
class ListenScreen extends ConsumerStatefulWidget {
  const ListenScreen({super.key, this.startFlowId, this.autoListen = true});

  /// Started from a task chip: skip the first question and ask for that task's details.
  final String? startFlowId;

  /// false = the user prefers the keypad (started without voice).
  final bool autoListen;

  @override
  ConsumerState<ListenScreen> createState() => _ListenScreenState();
}

class _ListenScreenState extends ConsumerState<ListenScreen> {
  ListenPhase _phase = ListenPhase.thinking;
  String _transcript = '';
  String? _flowId;
  Map<String, String> _params = {};
  String? _expecting;
  L10nText? _message; // question, confirmation or "can't do that yet"
  bool _typing = false;
  bool _busy = false;
  String? _error;
  final _input = TextEditingController();

  SahayakApi get _api => ref.read(apiProvider);
  String get _lang => ref.read(settingsProvider).language;

  late final SpeechService _speech;
  late final TtsService _tts;

  @override
  void initState() {
    super.initState();
    _speech = ref.read(speechProvider); // captured now: ref can't be used in dispose()
    _tts = ref.read(ttsProvider);
    _typing = !widget.autoListen;
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  @override
  void dispose() {
    _speech.stop();
    _tts.stop();
    _input.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final flowId = widget.startFlowId;
    if (flowId == null) {
      _listen();
      return;
    }
    try {
      final flow = (await ref.read(flowsProvider.future)).byId(flowId);
      final first = flow?.params.where((p) => p.required).firstOrNull;
      if (flow == null || first == null) {
        await _listen();
        return;
      }
      _flowId = flow.id;
      _ask(first.name, first.prompt);
    } catch (_) {
      _fail(null);
    }
  }

  Future<void> _say(L10nText text) async {
    final s = ref.read(settingsProvider);
    try {
      await _tts.speak(text.of(s.language), lang: s.language, rate: s.speechRate.value);
    } catch (_) {
      // speech output is a convenience; the text is always on screen
    }
  }

  Future<void> _listen() async {
    if (!mounted) return;
    setState(() {
      _phase = _expecting == null ? ListenPhase.listening : ListenPhase.asking;
      _transcript = '';
      _error = null;
      _typing = false;
    });
    final speech = _speech;
    if (!await speech.init()) {
      if (!mounted) return;
      final l = AppLocalizations.of(context);
      setState(() {
        _typing = true;
        _error = l.micUnavailable;
      });
      return;
    }
    if (!mounted) return;
    setState(() => _listeningNow = true);
    await speech.listen(
      lang: _lang,
      onPartial: (t) {
        if (mounted) setState(() => _transcript = t);
      },
      onFinal: (t) {
        if (!mounted) return;
        setState(() => _listeningNow = false);
        _handle(t);
      },
    );
  }

  bool _listeningNow = false;

  Future<void> _handle(String text) async {
    final l = AppLocalizations.of(context);
    if (text.trim().isEmpty) {
      setState(() {
        _error = l.noSpeech;
        _phase = _expecting == null ? ListenPhase.error : ListenPhase.asking;
      });
      return;
    }
    setState(() {
      _transcript = text;
      _phase = ListenPhase.thinking;
      _error = null;
    });
    try {
      final r = await _api.parse(text, _lang, flowId: _flowId, params: _params, expecting: _expecting);
      if (!mounted) return;
      _apply(r);
    } catch (e) {
      _fail(e);
    }
  }

  void _apply(IntentResult r) {
    if (!r.matched) {
      setState(() {
        _phase = ListenPhase.noMatch;
        _message = r.confirmation;
        _flowId = null;
        _params = {};
        _expecting = null;
      });
      if (r.confirmation != null) _say(r.confirmation!);
      return;
    }
    final stillMissing = r.missing.isNotEmpty && r.missing.first == _expecting;
    _flowId = r.flowId;
    _params = r.params;
    if (r.missing.isNotEmpty) {
      final l = AppLocalizations.of(context);
      _ask(r.missing.first, r.nextPrompt!, error: stillMissing ? l.answerInvalid : null);
    } else {
      setState(() {
        _expecting = null;
        _phase = ListenPhase.confirming;
        _message = r.confirmation;
      });
      if (r.confirmation != null) _say(r.confirmation!);
    }
  }

  Future<void> _ask(String param, L10nText prompt, {String? error}) async {
    setState(() {
      _expecting = param;
      _message = prompt;
      _phase = ListenPhase.asking;
      _error = error;
      _input.clear();
    });
    await _say(prompt);
    if (mounted && !_typing && widget.autoListen) _listen();
  }

  void _fail(Object? e) {
    if (!mounted) return;
    final l = AppLocalizations.of(context);
    setState(() {
      _phase = ListenPhase.error;
      _error = l.networkError;
    });
  }

  Future<void> _confirm() async {
    setState(() => _busy = true);
    try {
      final id = await _api.createTask(_flowId!, _params, _lang);
      if (mounted) context.pushReplacement('/task/$id');
    } catch (e) {
      setState(() => _busy = false);
      _fail(e);
    }
  }

  void _restart() {
    ref.read(ttsProvider).stop();
    setState(() {
      _flowId = null;
      _params = {};
      _expecting = null;
      _message = null;
    });
    _listen();
  }

  FlowParam? _currentParam(FlowCatalog? catalog) =>
      (_flowId == null || _expecting == null) ? null : catalog?.byId(_flowId!)?.param(_expecting!);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = ref.watch(settingsProvider).language;
    final text = Theme.of(context).textTheme;
    final catalog = ref.watch(flowsProvider).value;
    final param = _currentParam(catalog);

    Widget body;
    switch (_phase) {
      case ListenPhase.confirming:
        body = ConfirmationCard(text: _message?.of(lang) ?? '', busy: _busy, onYes: _confirm, onChange: _restart);
      case ListenPhase.noMatch:
        body = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_message?.of(lang) ?? '', style: text.titleLarge),
            const SizedBox(height: Tokens.space * 3),
            if (catalog != null)
              Wrap(spacing: Tokens.space, runSpacing: Tokens.space, children: [
                for (final f in catalog.flows)
                  ActionChip(
                    label: Text(f.title.of(lang)),
                    onPressed: () => context.pushReplacement('/listen?flow=${f.id}&type=1'),
                  ),
              ]),
            const SizedBox(height: Tokens.space * 3),
            FilledButton(onPressed: _restart, child: Text(l.tryAgain)),
          ],
        );
      default:
        body = _ListeningView(
          phase: _phase,
          transcript: _transcript,
          question: _message?.of(lang),
          listening: _listeningNow,
          error: _error,
          typing: _typing,
          param: param,
          lang: lang,
          input: _input,
          onMic: () {
            if (_listeningNow) {
              ref.read(speechProvider).stop();
            } else {
              _listen();
            }
          },
          onToggleTyping: () => setState(() => _typing = !_typing),
          onSubmitText: (v) => _handle(v),
          onOption: (o) => _handle(o.value),
        );
    }

    return ScreenFrame(
      leading: IconButton(
        tooltip: l.cancel,
        icon: const Icon(Icons.close_rounded),
        onPressed: () => context.canPop() ? context.pop() : context.go('/'),
      ),
      child: AnimatedSwitcher(duration: Tokens.fade, child: SingleChildScrollView(key: ValueKey(_phase), child: body)),
    );
  }
}

class _ListeningView extends StatelessWidget {
  const _ListeningView({
    required this.phase,
    required this.transcript,
    required this.question,
    required this.listening,
    required this.error,
    required this.typing,
    required this.param,
    required this.lang,
    required this.input,
    required this.onMic,
    required this.onToggleTyping,
    required this.onSubmitText,
    required this.onOption,
  });

  final ListenPhase phase;
  final String transcript;
  final String? question;
  final bool listening;
  final String? error;
  final bool typing;
  final FlowParam? param;
  final String lang;
  final TextEditingController input;
  final VoidCallback onMic;
  final VoidCallback onToggleTyping;
  final ValueChanged<String> onSubmitText;
  final ValueChanged<ParamOption> onOption;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final thinking = phase == ListenPhase.thinking;
    final options = param?.options ?? const <ParamOption>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (question != null && phase != ListenPhase.listening) ...[
          Semantics(liveRegion: true, child: Text(question!, style: text.headlineMedium)),
          const SizedBox(height: Tokens.space * 3),
        ],
        ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 96),
          child: Semantics(
            liveRegion: true,
            child: Text(
              thinking
                  ? l.thinking
                  : transcript.isNotEmpty
                      ? transcript
                      : (listening ? l.micListening : ''),
              style: text.displaySmall?.copyWith(
                color: transcript.isEmpty || thinking ? scheme.onSurfaceVariant : null,
                fontSize: Tokens.title,
              ),
            ),
          ),
        ),
        if (error != null) ...[
          const SizedBox(height: Tokens.space),
          Text(error!, style: text.bodyMedium?.copyWith(color: scheme.error)),
        ],
        const SizedBox(height: Tokens.space * 3),
        if (options.isNotEmpty) ...[
          Text(l.chooseOne, style: text.bodySmall),
          const SizedBox(height: Tokens.space),
          Wrap(spacing: Tokens.space, runSpacing: Tokens.space, children: [
            for (final o in options.take(40)) ActionChip(label: Text(o.label.of(lang)), onPressed: () => onOption(o)),
          ]),
          const SizedBox(height: Tokens.space * 3),
        ],
        if (typing && options.isEmpty) ...[
          TextField(
            controller: input,
            autofocus: true,
            style: text.bodyLarge,
            keyboardType: (param?.numeric ?? false) ? TextInputType.number : TextInputType.text,
            inputFormatters: (param?.numeric ?? false) ? [FilteringTextInputFormatter.digitsOnly] : null,
            decoration: InputDecoration(hintText: l.answerHint),
            onSubmitted: onSubmitText,
          ),
          const SizedBox(height: Tokens.space * 2),
          FilledButton(onPressed: () => onSubmitText(input.text), child: Text(l.send)),
          const SizedBox(height: Tokens.space * 2),
        ],
        if (!thinking && !typing)
          Center(child: MicButton(listening: listening, onTap: onMic, semanticLabel: l.micSemantics)),
        if (!thinking)
          TextButton(
            onPressed: onToggleTyping,
            child: Text(typing ? l.speakInstead : l.typeInstead),
          ),
      ],
    );
  }
}
