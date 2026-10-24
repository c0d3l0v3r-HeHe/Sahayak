/// Build-time configuration. Pass with:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
/// The default reaches the host machine from the Android emulator.
const String defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
