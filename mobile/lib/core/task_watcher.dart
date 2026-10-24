import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'api_client.dart';
import 'models.dart';

/// Keeps a task up to date: WebSocket events while connected, polling as a fallback.
class TaskWatcher extends AsyncNotifier<TaskDetail> {
  TaskWatcher(this.taskId);
  final String taskId;

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _sub;
  Timer? _poll;
  bool _disposed = false;

  SahayakApi get _api => ref.read(apiProvider);

  @override
  Future<TaskDetail> build() async {
    ref.onDispose(_close);
    final task = await _api.task(taskId);
    if (!task.status.terminal) unawaited(_connect());
    return task;
  }

  Future<void> _connect() async {
    try {
      final headers = await _api.authHeaders();
      final token = headers['Authorization']!.substring(7);
      final channel = WebSocketChannel.connect(_api.eventsUri(taskId, token));
      _channel = channel;
      await channel.ready;
      _sub = channel.stream.listen(
        _onMessage,
        onError: (_) => _startPolling(),
        onDone: () {
          if (!(state.value?.status.terminal ?? false)) _startPolling();
        },
      );
    } catch (_) {
      _startPolling();
    }
  }

  void _onMessage(dynamic raw) {
    final type = (jsonDecode(raw as String) as Map<String, dynamic>)['type'] as String?;
    // Events carry deltas; refreshing from the API keeps a single source of truth.
    if (type != null) unawaited(refresh());
  }

  void _startPolling() {
    if (_disposed || _poll != null) return;
    _poll = Timer.periodic(const Duration(milliseconds: 1500), (_) => refresh());
  }

  Future<void> refresh() async {
    if (_disposed) return;
    try {
      final task = await _api.task(taskId);
      if (_disposed) return;
      state = AsyncData(task);
      if (task.status.terminal) _close();
    } catch (_) {
      // keep the last known state; polling will retry
    }
  }

  void _close() {
    _disposed = true;
    _poll?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
  }
}

final taskProvider = AsyncNotifierProvider.autoDispose.family<TaskWatcher, TaskDetail, String>(TaskWatcher.new);
