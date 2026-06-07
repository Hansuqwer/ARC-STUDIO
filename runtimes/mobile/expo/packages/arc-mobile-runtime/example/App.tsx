/**
 * ARC Mobile Runtime — Expo example app (simulator preview).
 *
 * Demonstrates the SDK surface against fixtures only: list capabilities, run a simulated
 * action plan, and subscribe to simulation events. No real device access is performed.
 */
import { useEffect, useState } from "react";
import { Text, View, ScrollView, Button } from "react-native";
import {
  getCapabilities,
  simulate,
  addSimulationListener,
  ARC_MOBILE_SDK_VERSION,
  type ArcPlanResult,
  type ArcSimulationEvent,
} from "arc-mobile-runtime";

export default function App() {
  const [events, setEvents] = useState<ArcSimulationEvent[]>([]);
  const [result, setResult] = useState<ArcPlanResult | null>(null);

  useEffect(() => {
    const sub = addSimulationListener((e) => setEvents((prev) => [...prev, e]));
    return () => sub.remove();
  }, []);

  async function run() {
    const plan = {
      plan_id: "example-demo",
      steps: [
        { capability_id: "app.memory.write.mock", inputs: { key: "greeting", value: "hi" } },
        { capability_id: "device.camera.capture.mock" },
      ],
    };
    setResult(await simulate(plan));
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 24 }}>
      <Text style={{ fontSize: 18, fontWeight: "600" }}>ARC Mobile Runtime — Simulator Preview</Text>
      <Text>SDK v{ARC_MOBILE_SDK_VERSION} · fixtures only · no real device access</Text>
      <Text style={{ marginTop: 12 }}>Capabilities: {getCapabilities().length}</Text>
      <Button title="Run simulated plan" onPress={run} />
      {result && <Text style={{ marginTop: 12 }}>Plan steps simulated: {result.steps.length}</Text>}
      <View style={{ marginTop: 12 }}>
        {events.map((e, i) => (
          <Text key={i}>onSimulate: {e.capability_id}</Text>
        ))}
      </View>
    </ScrollView>
  );
}
