import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_hi.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('hi'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Sahayak'**
  String get appTitle;

  /// No description provided for @languageTitle.
  ///
  /// In en, this message translates to:
  /// **'Choose your language'**
  String get languageTitle;

  /// No description provided for @languageHindi.
  ///
  /// In en, this message translates to:
  /// **'हिन्दी'**
  String get languageHindi;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @continueButton.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueButton;

  /// No description provided for @onboardingTitle.
  ///
  /// In en, this message translates to:
  /// **'I can use government websites for you'**
  String get onboardingTitle;

  /// No description provided for @onboardingBody.
  ///
  /// In en, this message translates to:
  /// **'Tell me what you need. I fill in the website and read the answer to you. I always ask you before anything important.'**
  String get onboardingBody;

  /// No description provided for @onboardingMicButton.
  ///
  /// In en, this message translates to:
  /// **'Allow microphone'**
  String get onboardingMicButton;

  /// No description provided for @onboardingMicNote.
  ///
  /// In en, this message translates to:
  /// **'I need the microphone to hear you.'**
  String get onboardingMicNote;

  /// No description provided for @notNow.
  ///
  /// In en, this message translates to:
  /// **'Not now'**
  String get notNow;

  /// No description provided for @greeting.
  ///
  /// In en, this message translates to:
  /// **'Namaste! How can I help?'**
  String get greeting;

  /// No description provided for @micTapToSpeak.
  ///
  /// In en, this message translates to:
  /// **'Tap and speak'**
  String get micTapToSpeak;

  /// No description provided for @micListening.
  ///
  /// In en, this message translates to:
  /// **'Listening…'**
  String get micListening;

  /// No description provided for @micSemantics.
  ///
  /// In en, this message translates to:
  /// **'Microphone. Tap and say what you need.'**
  String get micSemantics;

  /// No description provided for @supportedTasks.
  ///
  /// In en, this message translates to:
  /// **'I can help with'**
  String get supportedTasks;

  /// No description provided for @lastTask.
  ///
  /// In en, this message translates to:
  /// **'Last task'**
  String get lastTask;

  /// No description provided for @historyTitle.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get historyTitle;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @yes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get yes;

  /// No description provided for @no.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get no;

  /// No description provided for @change.
  ///
  /// In en, this message translates to:
  /// **'Change'**
  String get change;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @confirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Is this right?'**
  String get confirmTitle;

  /// No description provided for @thinking.
  ///
  /// In en, this message translates to:
  /// **'Understanding…'**
  String get thinking;

  /// No description provided for @noSpeech.
  ///
  /// In en, this message translates to:
  /// **'I did not hear anything. Please try again.'**
  String get noSpeech;

  /// No description provided for @typeInstead.
  ///
  /// In en, this message translates to:
  /// **'Type instead'**
  String get typeInstead;

  /// No description provided for @speakInstead.
  ///
  /// In en, this message translates to:
  /// **'Speak instead'**
  String get speakInstead;

  /// No description provided for @answerHint.
  ///
  /// In en, this message translates to:
  /// **'Your answer'**
  String get answerHint;

  /// No description provided for @send.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get send;

  /// No description provided for @micUnavailable.
  ///
  /// In en, this message translates to:
  /// **'The microphone is not available. You can type instead.'**
  String get micUnavailable;

  /// No description provided for @networkError.
  ///
  /// In en, this message translates to:
  /// **'I cannot reach the server. Please check your internet.'**
  String get networkError;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get tryAgain;

  /// No description provided for @taskWorking.
  ///
  /// In en, this message translates to:
  /// **'Working on it'**
  String get taskWorking;

  /// No description provided for @taskQueued.
  ///
  /// In en, this message translates to:
  /// **'Getting ready…'**
  String get taskQueued;

  /// No description provided for @taskNeedsYou.
  ///
  /// In en, this message translates to:
  /// **'I need your help'**
  String get taskNeedsYou;

  /// No description provided for @liveView.
  ///
  /// In en, this message translates to:
  /// **'Live view of the website. Tap to enlarge.'**
  String get liveView;

  /// No description provided for @stepDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get stepDone;

  /// No description provided for @stepCurrent.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get stepCurrent;

  /// No description provided for @captchaTitle.
  ///
  /// In en, this message translates to:
  /// **'Please read these letters'**
  String get captchaTitle;

  /// No description provided for @captchaImage.
  ///
  /// In en, this message translates to:
  /// **'Picture with letters to read'**
  String get captchaImage;

  /// No description provided for @captchaHint.
  ///
  /// In en, this message translates to:
  /// **'Letters in the picture'**
  String get captchaHint;

  /// No description provided for @otpTitle.
  ///
  /// In en, this message translates to:
  /// **'You will get an SMS. Tell me the 6-digit code.'**
  String get otpTitle;

  /// No description provided for @otpHint.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get otpHint;

  /// No description provided for @confirmSubmitTitle.
  ///
  /// In en, this message translates to:
  /// **'Shall I submit this?'**
  String get confirmSubmitTitle;

  /// No description provided for @speak.
  ///
  /// In en, this message translates to:
  /// **'Speak'**
  String get speak;

  /// No description provided for @answerInvalid.
  ///
  /// In en, this message translates to:
  /// **'That does not look right. Please check and try again.'**
  String get answerInvalid;

  /// No description provided for @handoffExpired.
  ///
  /// In en, this message translates to:
  /// **'This step took too long. Please start again.'**
  String get handoffExpired;

  /// No description provided for @resultTitle.
  ///
  /// In en, this message translates to:
  /// **'Here is your answer'**
  String get resultTitle;

  /// No description provided for @listenAgain.
  ///
  /// In en, this message translates to:
  /// **'Hear again'**
  String get listenAgain;

  /// No description provided for @share.
  ///
  /// In en, this message translates to:
  /// **'Share'**
  String get share;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @taskFailedTitle.
  ///
  /// In en, this message translates to:
  /// **'I could not finish this'**
  String get taskFailedTitle;

  /// No description provided for @taskCancelled.
  ///
  /// In en, this message translates to:
  /// **'Task cancelled'**
  String get taskCancelled;

  /// No description provided for @statusQueued.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get statusQueued;

  /// No description provided for @statusRunning.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get statusRunning;

  /// No description provided for @statusAwaitingUser.
  ///
  /// In en, this message translates to:
  /// **'Needs you'**
  String get statusAwaitingUser;

  /// No description provided for @statusSucceeded.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get statusSucceeded;

  /// No description provided for @statusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get statusFailed;

  /// No description provided for @statusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get statusCancelled;

  /// No description provided for @statusExpired.
  ///
  /// In en, this message translates to:
  /// **'Timed out'**
  String get statusExpired;

  /// No description provided for @historyEmpty.
  ///
  /// In en, this message translates to:
  /// **'No tasks yet.'**
  String get historyEmpty;

  /// No description provided for @settingsLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get settingsLanguage;

  /// No description provided for @settingsSpeechRate.
  ///
  /// In en, this message translates to:
  /// **'Speaking speed'**
  String get settingsSpeechRate;

  /// No description provided for @rateSlow.
  ///
  /// In en, this message translates to:
  /// **'Slow'**
  String get rateSlow;

  /// No description provided for @rateNormal.
  ///
  /// In en, this message translates to:
  /// **'Normal'**
  String get rateNormal;

  /// No description provided for @rateFast.
  ///
  /// In en, this message translates to:
  /// **'Fast'**
  String get rateFast;

  /// No description provided for @settingsTextSize.
  ///
  /// In en, this message translates to:
  /// **'Text size'**
  String get settingsTextSize;

  /// No description provided for @textSizePreview.
  ///
  /// In en, this message translates to:
  /// **'This is how text will look.'**
  String get textSizePreview;

  /// No description provided for @settingsReadAloud.
  ///
  /// In en, this message translates to:
  /// **'Read each step aloud'**
  String get settingsReadAloud;

  /// No description provided for @settingsServer.
  ///
  /// In en, this message translates to:
  /// **'Server address (debug)'**
  String get settingsServer;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @deleteData.
  ///
  /// In en, this message translates to:
  /// **'Delete my data'**
  String get deleteData;

  /// No description provided for @deleteConfirm.
  ///
  /// In en, this message translates to:
  /// **'This deletes your history from our server. Continue?'**
  String get deleteConfirm;

  /// No description provided for @deleteDone.
  ///
  /// In en, this message translates to:
  /// **'Your data was deleted.'**
  String get deleteDone;

  /// No description provided for @privacyTitle.
  ///
  /// In en, this message translates to:
  /// **'Privacy'**
  String get privacyTitle;

  /// No description provided for @privacyNote.
  ///
  /// In en, this message translates to:
  /// **'I never store passwords, OTPs or CAPTCHA answers. Task details are deleted after 7 days.'**
  String get privacyNote;

  /// No description provided for @demoBanner.
  ///
  /// In en, this message translates to:
  /// **'Demo mode: using practice websites'**
  String get demoBanner;

  /// No description provided for @chooseOne.
  ///
  /// In en, this message translates to:
  /// **'Choose one'**
  String get chooseOne;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'hi'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'hi':
      return AppLocalizationsHi();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
