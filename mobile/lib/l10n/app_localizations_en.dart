// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Sahayak';

  @override
  String get languageTitle => 'Choose your language';

  @override
  String get languageHindi => 'हिन्दी';

  @override
  String get languageEnglish => 'English';

  @override
  String get continueButton => 'Continue';

  @override
  String get onboardingTitle => 'I can use government websites for you';

  @override
  String get onboardingBody =>
      'Tell me what you need. I fill in the website and read the answer to you. I always ask you before anything important.';

  @override
  String get onboardingMicButton => 'Allow microphone';

  @override
  String get onboardingMicNote => 'I need the microphone to hear you.';

  @override
  String get notNow => 'Not now';

  @override
  String get greeting => 'Namaste! How can I help?';

  @override
  String get micTapToSpeak => 'Tap and speak';

  @override
  String get micListening => 'Listening…';

  @override
  String get micSemantics => 'Microphone. Tap and say what you need.';

  @override
  String get supportedTasks => 'I can help with';

  @override
  String get lastTask => 'Last task';

  @override
  String get historyTitle => 'History';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get cancel => 'Cancel';

  @override
  String get yes => 'Yes';

  @override
  String get no => 'No';

  @override
  String get change => 'Change';

  @override
  String get back => 'Back';

  @override
  String get confirmTitle => 'Is this right?';

  @override
  String get thinking => 'Understanding…';

  @override
  String get noSpeech => 'I did not hear anything. Please try again.';

  @override
  String get typeInstead => 'Type instead';

  @override
  String get speakInstead => 'Speak instead';

  @override
  String get answerHint => 'Your answer';

  @override
  String get send => 'Send';

  @override
  String get micUnavailable =>
      'The microphone is not available. You can type instead.';

  @override
  String get networkError =>
      'I cannot reach the server. Please check your internet.';

  @override
  String get tryAgain => 'Try again';

  @override
  String get taskWorking => 'Working on it';

  @override
  String get taskQueued => 'Getting ready…';

  @override
  String get taskNeedsYou => 'I need your help';

  @override
  String get liveView => 'Live view of the website. Tap to enlarge.';

  @override
  String get stepDone => 'Done';

  @override
  String get stepCurrent => 'In progress';

  @override
  String get captchaTitle => 'Please read these letters';

  @override
  String get captchaImage => 'Picture with letters to read';

  @override
  String get captchaHint => 'Letters in the picture';

  @override
  String get otpTitle => 'You will get an SMS. Tell me the 6-digit code.';

  @override
  String get otpHint => '6-digit code';

  @override
  String get confirmSubmitTitle => 'Shall I submit this?';

  @override
  String get speak => 'Speak';

  @override
  String get answerInvalid =>
      'That does not look right. Please check and try again.';

  @override
  String get handoffExpired => 'This step took too long. Please start again.';

  @override
  String get resultTitle => 'Here is your answer';

  @override
  String get listenAgain => 'Hear again';

  @override
  String get share => 'Share';

  @override
  String get done => 'Done';

  @override
  String get taskFailedTitle => 'I could not finish this';

  @override
  String get taskCancelled => 'Task cancelled';

  @override
  String get statusQueued => 'Waiting';

  @override
  String get statusRunning => 'In progress';

  @override
  String get statusAwaitingUser => 'Needs you';

  @override
  String get statusSucceeded => 'Done';

  @override
  String get statusFailed => 'Failed';

  @override
  String get statusCancelled => 'Cancelled';

  @override
  String get statusExpired => 'Timed out';

  @override
  String get historyEmpty => 'No tasks yet.';

  @override
  String get settingsLanguage => 'Language';

  @override
  String get settingsSpeechRate => 'Speaking speed';

  @override
  String get rateSlow => 'Slow';

  @override
  String get rateNormal => 'Normal';

  @override
  String get rateFast => 'Fast';

  @override
  String get settingsTextSize => 'Text size';

  @override
  String get textSizePreview => 'This is how text will look.';

  @override
  String get settingsReadAloud => 'Read each step aloud';

  @override
  String get settingsServer => 'Server address (debug)';

  @override
  String get save => 'Save';

  @override
  String get deleteData => 'Delete my data';

  @override
  String get deleteConfirm =>
      'This deletes your history from our server. Continue?';

  @override
  String get deleteDone => 'Your data was deleted.';

  @override
  String get privacyTitle => 'Privacy';

  @override
  String get privacyNote =>
      'I never store passwords, OTPs or CAPTCHA answers. Task details are deleted after 7 days.';

  @override
  String get demoBanner => 'Demo mode: using practice websites';

  @override
  String get chooseOne => 'Choose one';
}
