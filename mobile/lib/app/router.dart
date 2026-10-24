import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/storage.dart';
import '../features/history/history_screen.dart';
import '../features/home/home_screen.dart';
import '../features/listen/listen_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/result/result_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/task/task_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final onboarded = ref.read(settingsProvider).onboarded;
      if (!onboarded && state.matchedLocation != '/onboarding') return '/onboarding';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const HomeScreen()),
      GoRoute(path: '/onboarding', builder: (_, _) => const OnboardingScreen()),
      GoRoute(
        path: '/listen',
        builder: (_, s) => ListenScreen(
          startFlowId: s.uri.queryParameters['flow'],
          autoListen: s.uri.queryParameters['type'] != '1',
        ),
      ),
      GoRoute(path: '/task/:id', builder: (_, s) => TaskScreen(taskId: s.pathParameters['id']!)),
      GoRoute(path: '/result/:id', builder: (_, s) => ResultScreen(taskId: s.pathParameters['id']!)),
      GoRoute(path: '/history', builder: (_, _) => const HistoryScreen()),
      GoRoute(path: '/settings', builder: (_, _) => const SettingsScreen()),
    ],
  );
});
