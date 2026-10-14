import { StyleSheet, Text, View } from "react-native";

import type { HazardKind } from "@/api/types";
import { colors } from "@/theme/colors";

type Props = { n: number; kind: HazardKind; size?: number };

/**
 * The number in a circle that ties a spot on the map to its row in the list. High-risk spots are red and
 * spots only students reported are purple. The number is what identifies the spot, so color is never the only cue.
 */
export function NumberBadge({ n, kind, size = 28 }: Props) {
  const backgroundColor = kind === "reported" ? colors.report : colors.riskHigh;
  return (
    <View style={[styles.circle, { width: size, height: size, borderRadius: size / 2, backgroundColor }]}>
      <Text allowFontScaling={false} style={[styles.number, { fontSize: size * 0.5 }]}>
        {n}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  circle: { alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: "white" },
  number: { color: "white", fontWeight: "700" },
});
