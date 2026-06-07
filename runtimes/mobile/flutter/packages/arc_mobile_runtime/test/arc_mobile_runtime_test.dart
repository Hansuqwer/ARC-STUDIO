import 'package:flutter_test/flutter_test.dart';
import 'package:arc_mobile_runtime/arc_mobile_runtime.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('capability catalog has the 13 simulated capabilities', () {
    expect(ArcMobileRuntime.listCapabilities().length, 13);
    expect(ArcMobileRuntime.listCapabilities(), contains('device.camera.capture.mock'));
  });

  test('ArcMobileCapability JSON round-trip', () {
    const cap = ArcMobileCapability(id: 'device.camera.capture.mock', dataSensitivity: ArcMobileDataSensitivity.high);
    final parsed = ArcMobileCapability.fromJson(cap.toJson());
    expect(parsed.id, cap.id);
    expect(parsed.dataSensitivity, ArcMobileDataSensitivity.high);
    expect(parsed.simulated, true);
  });

  test('action plan JSON round-trip', () {
    const plan = ArcMobileActionPlan(planId: 'p1', steps: [ArcMobileActionStep(capabilityId: 'app.memory.write.mock')]);
    final parsed = ArcMobileActionPlan.fromJson(plan.toJson());
    expect(parsed.planId, 'p1');
    expect(parsed.steps.single.capabilityId, 'app.memory.write.mock');
    expect(parsed.requiresNetwork, false);
  });

  test('simulateAction returns deterministic fixtures (no native plugin)', () async {
    final res = await ArcMobileRuntime.simulateAction('device.location.current.mock');
    expect(res.mock, true);
    expect(res.capabilityId, 'device.location.current.mock');
    expect(res.outputs['latitude'], 37.7749);
  });

  test('simulate runs an action plan step-by-step', () async {
    const plan = ArcMobileActionPlan(planId: 'demo', steps: [
      ArcMobileActionStep(capabilityId: 'app.memory.write.mock'),
      ArcMobileActionStep(capabilityId: 'device.camera.capture.mock'),
    ]);
    final results = await ArcMobileRuntime.simulate(plan);
    expect(results.length, 2);
    expect(results.every((r) => r.mock), true);
  });
}
