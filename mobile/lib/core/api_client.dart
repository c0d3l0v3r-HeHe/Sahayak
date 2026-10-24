import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'models.dart';
import 'storage.dart';

/// Everything the app needs from the backend. Tests replace it with a fake.
abstract class SahayakApi {
  String get baseUrl;
  Future<Map<String, String>> authHeaders();
  Future<FlowCatalog> flows();
  Future<IntentResult> parse(String text, String lang,
      {String? flowId, Map<String, String>? params, String? expecting});
  Future<String> createTask(String flowId, Map<String, String> params, String lang);
  Future<TaskDetail> task(String id);
  Future<List<TaskDetail>> history({int limit = 30});
  Future<void> answer(String taskId, String handoffId, String value);
  Future<void> cancel(String taskId);
  Future<void> deleteMyData();
  String screenUrl(String taskId, String screenshotId) => '$baseUrl/v1/tasks/$taskId/screens/$screenshotId';
  Uri eventsUri(String taskId, String token);
}

class DioSahayakApi extends SahayakApi {
  DioSahayakApi(this.ref, this._settings)
      : _dio = Dio(BaseOptions(
          baseUrl: _settings.serverUrl,
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 20),
        ));

  final Ref ref;
  final AppSettings _settings;
  final Dio _dio;
  String? _token;

  @override
  String get baseUrl => _settings.serverUrl;

  Future<String> _ensureToken({bool refresh = false}) async {
    _token ??= _settings.token;
    if (_token != null && !refresh) return _token!;
    final resp = await _dio.post('/v1/auth/anonymous',
        data: {'device_id': _settings.deviceId, 'language': _settings.language});
    _token = resp.data['token'] as String;
    ref.read(settingsProvider.notifier).setToken(_token);
    return _token!;
  }

  @override
  Future<Map<String, String>> authHeaders() async => {'Authorization': 'Bearer ${await _ensureToken()}'};

  Future<Response<dynamic>> _call(String method, String path, {Object? data, Map<String, dynamic>? query}) async {
    Future<Response<dynamic>> send() async => _dio.request(path,
        data: data,
        queryParameters: query,
        options: Options(method: method, headers: await authHeaders()));
    try {
      try {
        return await send();
      } on DioException catch (e) {
        if (e.response?.statusCode == 401) {
          await _ensureToken(refresh: true); // token expired or data deleted: log in again
          return await send();
        }
        rethrow;
      }
    } on DioException catch (e) {
      throw ApiException(e.response?.statusCode ?? 0, '${e.response?.data ?? e.message}');
    }
  }

  @override
  Future<FlowCatalog> flows() async {
    final r = await _call('GET', '/v1/flows');
    return FlowCatalog(
      demoMode: r.data['demo_mode'] as bool? ?? false,
      flows: [for (final f in r.data['flows'] as List) FlowInfo.fromJson(f as Map<String, dynamic>)],
    );
  }

  @override
  Future<IntentResult> parse(String text, String lang,
      {String? flowId, Map<String, String>? params, String? expecting}) async {
    final r = await _call('POST', '/v1/intent/parse', data: {
      'text': text,
      'lang': lang,
      'flow_id': ?flowId,
      'params': ?params,
      'expecting': ?expecting,
    });
    return IntentResult.fromJson(r.data as Map<String, dynamic>);
  }

  @override
  Future<String> createTask(String flowId, Map<String, String> params, String lang) async {
    final r = await _call('POST', '/v1/tasks', data: {'flow_id': flowId, 'params': params, 'lang': lang});
    return r.data['task_id'] as String;
  }

  @override
  Future<TaskDetail> task(String id) async =>
      TaskDetail.fromJson((await _call('GET', '/v1/tasks/$id')).data as Map<String, dynamic>);

  @override
  Future<List<TaskDetail>> history({int limit = 30}) async {
    final r = await _call('GET', '/v1/tasks', query: {'limit': limit});
    return [for (final t in r.data['tasks'] as List) TaskDetail.fromJson(t as Map<String, dynamic>)];
  }

  @override
  Future<void> answer(String taskId, String handoffId, String value) async {
    await _call('POST', '/v1/tasks/$taskId/input', data: {'handoff_id': handoffId, 'value': value});
  }

  @override
  Future<void> cancel(String taskId) async {
    await _call('POST', '/v1/tasks/$taskId/cancel');
  }

  @override
  Future<void> deleteMyData() async {
    await _call('DELETE', '/v1/me');
    _token = null;
    ref.read(settingsProvider.notifier).setToken(null);
  }

  @override
  Uri eventsUri(String taskId, String token) {
    final base = Uri.parse(baseUrl);
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '${base.path}/v1/tasks/$taskId/events'.replaceAll('//', '/'),
      queryParameters: {'token': token},
    );
  }
}

final apiProvider = Provider<SahayakApi>((ref) {
  // Rebuilt when the server URL changes (debug setting); token updates don't rebuild it.
  final url = ref.watch(settingsProvider.select((s) => s.serverUrl));
  final settings = ref.read(settingsProvider);
  return DioSahayakApi(ref, settings.copyWith(serverUrl: url));
});

final flowsProvider = FutureProvider<FlowCatalog>((ref) => ref.watch(apiProvider).flows());

final historyProvider = FutureProvider.autoDispose<List<TaskDetail>>((ref) => ref.watch(apiProvider).history());
