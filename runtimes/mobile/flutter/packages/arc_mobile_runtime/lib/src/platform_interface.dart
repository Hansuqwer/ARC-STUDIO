/// ARC Mobile Runtime — Flutter platform interface (simulator preview).
///
/// Federated-plugin platform interface. The default implementation
/// (ArcMobileRuntimeMethodChannel) returns fixtures only; a real native plugin would
/// register its own implementation here in a future, gated phase. No real device access.
library arc_mobile_runtime.platform_interface;

import 'method_channel.dart';
import 'models.dart';

abstract class ArcMobileRuntimePlatform {
  ArcMobileRuntimePlatform();

  static ArcMobileRuntimePlatform _instance = ArcMobileRuntimeMethodChannel();

  /// The active platform implementation (defaults to the fixtures-only method channel).
  static ArcMobileRuntimePlatform get instance => _instance;

  /// A platform plugin registers itself by setting this. Implementations must extend
  /// ArcMobileRuntimePlatform so the surface stays stable.
  static set instance(ArcMobileRuntimePlatform value) {
    _instance = value;
  }

  Future<ArcSimulateResult> simulateAction(String capabilityId, Map<String, dynamic> inputs) {
    throw UnimplementedError('simulateAction() not implemented');
  }

  Future<Map<String, dynamic>> doctor() {
    throw UnimplementedError('doctor() not implemented');
  }

  Future<Map<String, dynamic>> getPermissionState(String capabilityId) {
    throw UnimplementedError('getPermissionState() not implemented');
  }
}
