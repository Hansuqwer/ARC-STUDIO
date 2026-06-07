/// ARC Mobile Runtime — Flutter Dart models (simulator preview).
///
/// Mirror the Python/JSON mobile protocol types. Pure data — no platform access.
library arc_mobile_runtime.models;

/// Data sensitivity level (mirrors MobileDataSensitivity).
enum ArcMobileDataSensitivity { none, low, medium, high, critical }

ArcMobileDataSensitivity sensitivityFromString(String value) =>
    ArcMobileDataSensitivity.values.firstWhere(
      (e) => e.name == value,
      orElse: () => ArcMobileDataSensitivity.none,
    );

/// A simulated capability descriptor.
class ArcMobileCapability {
  final String id;
  final ArcMobileDataSensitivity dataSensitivity;
  final bool simulated;

  const ArcMobileCapability({
    required this.id,
    this.dataSensitivity = ArcMobileDataSensitivity.none,
    this.simulated = true,
  });

  factory ArcMobileCapability.fromJson(Map<String, dynamic> json) => ArcMobileCapability(
        id: json['id'] as String,
        dataSensitivity: sensitivityFromString((json['data_sensitivity'] ?? 'none') as String),
        simulated: (json['simulated'] ?? true) as bool,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'data_sensitivity': dataSensitivity.name,
        'simulated': simulated,
      };
}

/// A single step in an action plan.
class ArcMobileActionStep {
  final String capabilityId;
  final Map<String, dynamic> inputs;

  const ArcMobileActionStep({required this.capabilityId, this.inputs = const {}});

  factory ArcMobileActionStep.fromJson(Map<String, dynamic> json) => ArcMobileActionStep(
        capabilityId: json['capability_id'] as String,
        inputs: Map<String, dynamic>.from((json['inputs'] ?? const {}) as Map),
      );

  Map<String, dynamic> toJson() => {'capability_id': capabilityId, 'inputs': inputs};
}

/// An action plan (network/background must be false in simulator preview).
class ArcMobileActionPlan {
  final String planId;
  final List<ArcMobileActionStep> steps;
  final bool requiresNetwork;
  final bool requiresBackground;

  const ArcMobileActionPlan({
    required this.planId,
    this.steps = const [],
    this.requiresNetwork = false,
    this.requiresBackground = false,
  });

  factory ArcMobileActionPlan.fromJson(Map<String, dynamic> json) => ArcMobileActionPlan(
        planId: json['plan_id'] as String,
        steps: ((json['steps'] ?? const []) as List)
            .map((e) => ArcMobileActionStep.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
        requiresNetwork: (json['requires_network'] ?? false) as bool,
        requiresBackground: (json['requires_background'] ?? false) as bool,
      );

  Map<String, dynamic> toJson() => {
        'plan_id': planId,
        'steps': steps.map((s) => s.toJson()).toList(),
        'requires_network': requiresNetwork,
        'requires_background': requiresBackground,
      };
}

/// The result of simulating one capability.
class ArcSimulateResult {
  final String capabilityId;
  final bool mock;
  final Map<String, dynamic> outputs;

  const ArcSimulateResult({required this.capabilityId, this.mock = true, this.outputs = const {}});

  factory ArcSimulateResult.fromJson(Map<String, dynamic> json) => ArcSimulateResult(
        capabilityId: json['capability_id'] as String,
        mock: (json['mock'] ?? true) as bool,
        outputs: Map<String, dynamic>.from((json['outputs'] ?? const {}) as Map),
      );

  Map<String, dynamic> toJson() => {'simulated': true, 'capability_id': capabilityId, 'mock': mock, 'outputs': outputs};
}
