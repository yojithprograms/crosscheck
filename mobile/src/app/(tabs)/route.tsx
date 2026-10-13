import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, BackHandler, StyleSheet, View } from "react-native";

import { useSchools } from "@/api/hooks";
import { EmptyState } from "@/components/EmptyState";
import { PinPicker } from "@/components/PinPicker";
import { PrimaryButton } from "@/components/PrimaryButton";
import { RouteStart } from "@/components/RouteStart";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { useAppStore, type LatLon, type TravelMode } from "@/state/store";
import { colors } from "@/theme/colors";
import { distanceMeters, pointToLatLng } from "@/utils/geo";
import { miles } from "@/utils/format";

// Where the student is in the route flow (S6 to S8). This lives only in memory: a start point near
// someone's home is never saved or logged unless the student taps "Save as my route" (Step 4.2).
type Step =
  | { name: "start" }
  | { name: "pin"; notice?: string }
  | { name: "picked"; origin: LatLon; mode: TravelMode };

/** The Route tab: S6 start, S7 pin picker, then S8 results (coming in Step 4.2). */
export default function RouteTab() {
  const router = useRouter();
  const schoolId = useAppStore((state) => state.schoolId);
  const schools = useSchools();
  const school = schools.data?.find((s) => s.id === schoolId);
  const [step, setStep] = useState<Step>({ name: "start" });

  // A different school means a different circle, so begin again.
  useEffect(() => setStep({ name: "start" }), [schoolId]);

  // On Android, the back button steps back through the flow instead of leaving the tab.
  useFocusEffect(
    useCallback(() => {
      if (step.name === "start") return undefined;
      const subscription = BackHandler.addEventListener("hardwareBackPress", () => {
        setStep({ name: "start" });
        return true;
      });
      return () => subscription.remove();
    }, [step.name]),
  );

  if (schools.isPending) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }
  if (schools.isError) {
    return (
      <EmptyState
        icon="cloud-offline-outline"
        title={strings.schoolPicker.unreachableTitle}
        body={strings.schoolPicker.unreachableBody}
        action={<PrimaryButton title={strings.schoolPicker.tryAgain} onPress={() => void schools.refetch()} />}
      />
    );
  }
  if (!school) {
    return (
      <EmptyState
        icon="map-outline"
        title={strings.map.notReadyTitle}
        body={strings.map.notReadyBody}
        action={
          <PrimaryButton
            title={strings.map.changeSchool}
            onPress={() => router.push({ pathname: "/onboarding/school", params: { from: "settings" } })}
          />
        }
      />
    );
  }

  if (step.name === "pin") {
    return (
      <PinPicker
        school={school}
        notice={step.notice}
        onBack={() => setStep({ name: "start" })}
        onConfirm={(origin) => setStep({ name: "picked", origin, mode: useAppStore.getState().travelMode })}
      />
    );
  }

  if (step.name === "picked") {
    const away = distanceMeters(pointToLatLng(step.origin), { latitude: school.lat, longitude: school.lon });
    return (
      <EmptyState
        icon="checkmark-circle-outline"
        title={strings.pickedStart.title}
        body={strings.pickedStart.body(miles(away), school.name)}
        action={<SecondaryButton title={strings.pickedStart.changeStart} onPress={() => setStep({ name: "start" })} />}
      />
    );
  }

  return (
    <RouteStart
      school={school}
      onPicked={(origin, mode) => setStep({ name: "picked", origin, mode })}
      onDropPin={(notice) => setStep({ name: "pin", notice })}
    />
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
});
