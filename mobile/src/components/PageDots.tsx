import { StyleSheet, View } from "react-native";

import { colors } from "@/theme/colors";

type Props = { count: number; index: number };

/** Page dots for the onboarding flow: the current step is a longer blue pill, the others small pale dots. */
export function PageDots({ count, index }: Props) {
  return (
    <View
      style={styles.row}
      accessible
      accessibilityLabel={`Step ${index + 1} of ${count}`}
      importantForAccessibility="yes"
    >
      {Array.from({ length: count }, (_, i) => (
        <View key={i} style={[styles.dot, i === index && styles.active]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 6, paddingVertical: 4 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.brandSky },
  active: { width: 26, backgroundColor: colors.brand },
});
