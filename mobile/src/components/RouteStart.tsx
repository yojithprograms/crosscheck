import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import type { School } from "@/api/types";
import { Card } from "@/components/Card";
import { ChipGroup } from "@/components/Chip";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { useAppStore, type LatLon, type TravelMode } from "@/state/store";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { insideCircle, pointToLatLng } from "@/utils/geo";
import { getCurrentPoint } from "@/utils/location";

type Props = {
  school: School;
  onPicked: (origin: LatLon, mode: TravelMode) => void; // a start point is ready: go to the results (S8)
  onDropPin: (notice?: string) => void; // go to the pin picker (S7), optionally with a message to show
};

const MODE_OPTIONS: { value: TravelMode; label: string; icon: "walk" | "bicycle" }[] = [
  { value: "walk", label: strings.start.modes.walk, icon: "walk" },
  { value: "bike", label: strings.start.modes.bike, icon: "bicycle" },
];

/** S6 · where does the student start? Their location, or a pin they drop. */
export function RouteStart({ school, onPicked, onDropPin }: Props) {
  const travelMode = useAppStore((state) => state.travelMode);
  const setTravelMode = useAppStore((state) => state.setTravelMode);
  const savedRoute = useAppStore((state) => state.savedRoute);
  const [locating, setLocating] = useState(false);

  const schoolCenter = { latitude: school.lat, longitude: school.lon };
  const isInside = (point: LatLon) => insideCircle(pointToLatLng(point), schoolCenter, school.radius_m);
  // A route saved for a different school can start outside this school's circle. Don't offer it then.
  const usual = savedRoute && isInside(savedRoute.origin) ? savedRoute : null;

  const useMyLocation = async () => {
    setLocating(true);
    const result = await getCurrentPoint();
    setLocating(false);
    if (result.status === "ok") {
      if (isInside(result.point)) onPicked(result.point, travelMode);
      else onDropPin(strings.start.outside(school.name));
    } else {
      onDropPin(result.status === "denied" ? strings.start.locationOff : strings.start.locationUnavailable);
    }
  };

  const useUsual = () => {
    if (!usual) return;
    setTravelMode(usual.mode);
    onPicked(usual.origin, usual.mode);
  };

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.title} accessibilityRole="header">
        {strings.start.title(school.name)}
      </Text>

      {usual ? (
        <Card>
          <Text style={styles.cardTitle}>{strings.start.usualTitle}</Text>
          <Text style={styles.body}>{strings.start.usualBody(strings.start.modes[usual.mode])}</Text>
          <View style={styles.cardButton}>
            <SecondaryButton title={strings.start.useIt} onPress={useUsual} />
          </View>
        </Card>
      ) : null}

      <Text style={styles.section}>{strings.start.whereTitle}</Text>
      <View style={styles.buttons}>
        <PrimaryButton
          title={locating ? strings.start.findingLocation : strings.start.useLocation}
          icon="locate"
          loading={locating}
          onPress={() => void useMyLocation()}
        />
        <SecondaryButton title={strings.start.dropPin} onPress={() => onDropPin()} disabled={locating} />
      </View>

      <ChipGroup options={MODE_OPTIONS} value={travelMode} onChange={setTravelMode} />

      <Text style={styles.tip}>{strings.start.tip}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: shape.screenPadding, gap: spacing.lg },
  title: { ...type.sectionTitle, color: colors.text },
  section: { ...type.headline, color: colors.text },
  cardTitle: { ...type.headline, color: colors.text },
  body: { ...type.body, color: colors.textMuted },
  cardButton: { marginTop: spacing.sm },
  buttons: { gap: spacing.sm },
  tip: { ...type.caption, color: colors.textMuted },
});
