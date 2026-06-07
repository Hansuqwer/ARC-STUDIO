/// ARC Mobile Runtime SDK — Flutter (simulator preview).
///
/// Public Dart API over a federated platform interface. The default implementation returns
/// fixtures only — no real camera, microphone, contacts, calendar, photos, location, files,
/// health, background execution, or OS permission requests. Nothing here grants device access.
library arc_mobile_runtime;

import 'src/models.dart';
import 'src/platform_interface.dart';

export 'src/models.dart';
export 'src/platform_interface.dart' show ArcMobileRuntimePlatform;

/// The simulated capability catalog (mirrors the Python builtin set; all fixture-backed).
const List<String> kArcMobileCapabilityIds = <String>[
  'device.camera.capture.mock',
  'device.microphone.transcribe.mock',
  'device.location.current.mock',
  'device.calendar.read.mock',
  'device.calendar.write.mock',
  'device.contacts.search.mock',
  'device.files.pick.mock',
  'device.photos.pick.mock',
  'device.notifications.schedule.mock',
  'app.memory.write.mock',
  'app.memory.retrieve.mock',
  'app.local_search.query.mock',
  'app.ui.action_plan.mock',
];

/// Facade for the ARC Mobile Runtime (simulator preview).
class ArcMobileRuntime {
  static const String sdkVersion = '0.1.0';
  static const bool isMockMode = true;

  static ArcMobileRuntimePlatform get _platform => ArcMobileRuntimePlatform.instance;

  /// List the simulated capability ids (fixtures only).
  static List<String> listCapabilities() => List<String>.from(kArcMobileCapabilityIds);

  /// Simulate a single capability.
  static Future<ArcSimulateResult> simulateAction(
    String capabilityId, [
    Map<String, dynamic> inputs = const {},
  ]) {
    return _platform.simulateAction(capabilityId, inputs);
  }

  /// Simulate a full action plan, step by step.
  static Future<List<ArcSimulateResult>> simulate(ArcMobileActionPlan plan) async {
    final results = <ArcSimulateResult>[];
    for (final step in plan.steps) {
      results.add(await simulateAction(step.capabilityId, step.inputs));
    }
    return results;
  }

  /// Runtime status (mock).
  static Future<Map<String, dynamic>> doctor() => _platform.doctor();
}
