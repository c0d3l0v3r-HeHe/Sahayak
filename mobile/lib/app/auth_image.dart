import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';

/// A screenshot from the API (requires the auth header).
class AuthImage extends ConsumerWidget {
  const AuthImage({super.key, required this.taskId, required this.screenshotId, this.fit = BoxFit.contain});

  final String taskId;
  final String screenshotId;
  final BoxFit fit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    return FutureBuilder<Map<String, String>>(
      future: api.authHeaders(),
      builder: (context, snap) {
        if (!snap.hasData) return const SizedBox.shrink();
        return Image.network(
          api.screenUrl(taskId, screenshotId),
          headers: snap.data,
          fit: fit,
          gaplessPlayback: true, // no flicker when the next screenshot arrives
          errorBuilder: (_, _, _) => const SizedBox.shrink(),
        );
      },
    );
  }
}
