/// ARC Mobile Runtime — Flutter method-channel implementation (simulator preview).
///
/// Default platform implementation. It attempts the `arc_mobile_runtime` MethodChannel and,
/// when no native plugin is registered (the simulator-preview default), produces identical
/// deterministic fixtures in Dart. No real device access is ever performed.
library arc_mobile_runtime.method_channel;

import 'package:flutter/services.dart';

import 'models.dart';
import 'platform_interface.dart';

class ArcMobileRuntimeMethodChannel extends ArcMobileRuntimePlatform {
  static const MethodChannel _channel = MethodChannel('arc_mobile_runtime');

  Map<String, dynamic> _fixtureOutputs(String capabilityId) {
    if (capabilityId.startsWith('device.location')) {
      return {'latitude': 37.7749, 'longitude': -122.4194, 'mock': true};
    }
    if (capabilityId.startsWith('device.camera')) {
      return {'uri': 'fixture://mock-image.jpg', 'mock': true};
    }
    if (capabilityId.startsWith('app.memory.retrieve')) {
      return {'found': false, 'value': null, 'mock': true};
    }
    return {'mock': true, 'capability_id': capabilityId};
  }

  @override
  Future<ArcSimulateResult> simulateAction(String capabilityId, Map<String, dynamic> inputs) async {
    try {
      final res = await _channel.invokeMapMethod<String, dynamic>(
        'simulateAction',
        {'capabilityId': capabilityId, 'inputs': inputs},
      );
      if (res != null) return ArcSimulateResult.fromJson(res);
    } on MissingPluginException {
      // Simulator preview: no native plugin registered — use Dart fixtures.
    }
    return ArcSimulateResult(capabilityId: capabilityId, outputs: _fixtureOutputs(capabilityId));
  }

  @override
  Future<Map<String, dynamic>> doctor() async {
    return {
      'ok': true,
      'runtime_mode': 'simulator',
      'mock_mode': true,
      'capability_count': 13,
      'note': 'Simulator preview — no real native bridges.',
    };
  }

  @override
  Future<Map<String, dynamic>> getPermissionState(String capabilityId) async {
    // Mock only — never requests real OS permissions.
    return {'status': 'not_requested', 'mock': true};
  }
}
