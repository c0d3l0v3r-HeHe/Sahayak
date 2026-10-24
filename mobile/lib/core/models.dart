/// Plain data classes mirroring the backend's JSON.
class L10nText {
  const L10nText(this.en, this.hi);
  final String en;
  final String hi;

  String of(String lang) => lang == 'hi' ? hi : en;

  static L10nText? fromJson(Object? json) {
    if (json is! Map) return null;
    return L10nText('${json['en'] ?? ''}', '${json['hi'] ?? ''}');
  }
}

class ParamOption {
  const ParamOption(this.value, this.label);
  final String value;
  final L10nText label;
}

class FlowParam {
  const FlowParam({
    required this.name,
    required this.type,
    required this.prompt,
    this.regex,
    this.options = const [],
    this.required = true,
  });

  final String name;
  final String type; // string | int | date | enum
  final L10nText prompt;
  final String? regex;
  final List<ParamOption> options;
  final bool required;

  bool get numeric => type == 'int' || (regex?.contains(r'\d') ?? false);

  factory FlowParam.fromJson(Map<String, dynamic> j) => FlowParam(
        name: j['name'] as String,
        type: j['type'] as String? ?? 'string',
        prompt: L10nText.fromJson(j['prompt'])!,
        regex: j['regex'] as String?,
        required: j['required'] as bool? ?? true,
        options: [
          for (final o in (j['options'] as List? ?? const []))
            ParamOption(o['value'] as String, L10nText.fromJson(o['label'])!),
        ],
      );
}

class FlowInfo {
  const FlowInfo({required this.id, required this.title, required this.description, required this.params});
  final String id;
  final L10nText title;
  final L10nText description;
  final List<FlowParam> params;

  FlowParam? param(String name) {
    for (final p in params) {
      if (p.name == name) return p;
    }
    return null;
  }

  factory FlowInfo.fromJson(Map<String, dynamic> j) => FlowInfo(
        id: j['id'] as String,
        title: L10nText.fromJson(j['title'])!,
        description: L10nText.fromJson(j['description'])!,
        params: [for (final p in j['params'] as List) FlowParam.fromJson(p as Map<String, dynamic>)],
      );
}

class FlowCatalog {
  const FlowCatalog({required this.flows, required this.demoMode});
  final List<FlowInfo> flows;
  final bool demoMode;

  FlowInfo? byId(String id) {
    for (final f in flows) {
      if (f.id == id) return f;
    }
    return null;
  }
}

class IntentResult {
  const IntentResult({
    required this.flowId,
    required this.params,
    required this.missing,
    this.confirmation,
    this.nextPrompt,
    this.title,
  });

  final String? flowId;
  final Map<String, String> params;
  final List<String> missing;
  final L10nText? confirmation; // also the "can't do that yet" message when flowId is null
  final L10nText? nextPrompt;
  final L10nText? title;

  bool get matched => flowId != null;
  bool get complete => matched && missing.isEmpty;

  factory IntentResult.fromJson(Map<String, dynamic> j) => IntentResult(
        flowId: j['flow_id'] as String?,
        params: {for (final e in (j['params'] as Map? ?? {}).entries) '${e.key}': '${e.value}'},
        missing: [for (final m in (j['missing_params'] as List? ?? const [])) '$m'],
        confirmation: L10nText.fromJson(j['confirmation']),
        nextPrompt: L10nText.fromJson(j['next_prompt']),
        title: L10nText.fromJson(j['title']),
      );
}

enum TaskStatus { queued, running, awaitingUser, succeeded, failed, cancelled, expired }

TaskStatus parseStatus(String s) => switch (s) {
      'queued' => TaskStatus.queued,
      'running' => TaskStatus.running,
      'awaiting_user' => TaskStatus.awaitingUser,
      'succeeded' => TaskStatus.succeeded,
      'failed' => TaskStatus.failed,
      'cancelled' => TaskStatus.cancelled,
      _ => TaskStatus.expired,
    };

extension TaskStatusX on TaskStatus {
  bool get terminal =>
      this == TaskStatus.succeeded ||
      this == TaskStatus.failed ||
      this == TaskStatus.cancelled ||
      this == TaskStatus.expired;
}

class TaskEvent {
  const TaskEvent({required this.seq, required this.type, this.message, this.screenshotId});
  final int seq;
  final String type;
  final L10nText? message;
  final String? screenshotId;

  factory TaskEvent.fromJson(Map<String, dynamic> j) => TaskEvent(
        seq: j['seq'] as int,
        type: j['type'] as String,
        message: L10nText.fromJson(j['message']),
        screenshotId: j['screenshot_id'] as String?,
      );
}

class Handoff {
  const Handoff({required this.id, required this.kind, required this.prompt, this.imageId, this.param});
  final String id;
  final String kind; // captcha | otp | confirm | param
  final L10nText prompt;
  final String? imageId;
  final String? param;

  static Handoff? fromJson(Object? j) {
    if (j is! Map) return null;
    return Handoff(
      id: j['id'] as String,
      kind: j['kind'] as String,
      prompt: L10nText.fromJson(j['prompt'])!,
      imageId: j['image_id'] as String?,
      param: j['param'] as String?,
    );
  }
}

class TaskDetail {
  const TaskDetail({
    required this.id,
    required this.flowId,
    required this.title,
    required this.status,
    required this.events,
    required this.createdAt,
    this.resultText,
    this.resultData = const {},
    this.error,
    this.handoff,
  });

  final String id;
  final String flowId;
  final L10nText? title;
  final TaskStatus status;
  final List<TaskEvent> events;
  final DateTime createdAt;
  final L10nText? resultText;
  final Map<String, dynamic> resultData;
  final L10nText? error;
  final Handoff? handoff;

  List<TaskEvent> get steps => [for (final e in events) if (e.type == 'step' && e.message != null) e];

  String? get latestScreenshot {
    for (final e in events.reversed) {
      if (e.screenshotId != null && e.type == 'screenshot') return e.screenshotId;
    }
    return null;
  }

  factory TaskDetail.fromJson(Map<String, dynamic> j) {
    final result = j['result'] as Map<String, dynamic>?;
    return TaskDetail(
      id: j['id'] as String,
      flowId: j['flow_id'] as String,
      title: L10nText.fromJson(j['title']),
      status: parseStatus(j['status'] as String),
      events: [for (final e in (j['events'] as List? ?? const [])) TaskEvent.fromJson(e as Map<String, dynamic>)],
      createdAt: DateTime.tryParse('${j['created_at']}')?.toLocal() ?? DateTime.now(),
      resultText: L10nText.fromJson(result?['text']),
      resultData: (result?['data'] as Map<String, dynamic>?) ?? const {},
      error: L10nText.fromJson(j['error']),
      handoff: Handoff.fromJson(j['handoff']),
    );
  }
}

/// Thrown for answers the server rejects (422) or hand-offs that expired (410).
class ApiException implements Exception {
  const ApiException(this.statusCode, [this.message = '']);
  final int statusCode;
  final String message;

  bool get invalidAnswer => statusCode == 422;
  bool get expired => statusCode == 410;
  bool get network => statusCode == 0;

  @override
  String toString() => 'ApiException($statusCode, $message)';
}
