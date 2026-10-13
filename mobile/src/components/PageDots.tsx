import { StyleSheet, View } from "react-native";

import { colors } from "@/theme/colors";

type Props = { count: number; index: number };

/** Page dots for the onboarding flow: ● ○ ○ */
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
  row: { flexDirection: "row", justifyContent: "center", gap: 8, paddingVertical: 8 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.border },
  active: { backgroundColor: colors.brand },
});
